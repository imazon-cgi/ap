// banco.js — rankings de Ameaça & Pressão lidos do banco do imazongeo_upload
// (PostgreSQL/PostGIS).
//
// O banco é opcional. Sem DATABASE_URL, com o banco fora do ar, sem a visão do
// AP ou sem dados do ano/recorte pedido, geojsonAp() retorna null e o dashboard
// continua lendo os GeoJSON do S3.
//
// Visão esperada (imazongeo.vw_ameaca_pressao), uma linha por área protegida
// em cada ranking trimestral:
//   ano, trimestre  inteiros
//   legenda         meses cobertos, ex.: julho a setembro
//   recorte         'geral' | 'categ_ti' | 'categ_uce' | 'categ_ucf'
//   classe          'ameaca' | 'pressao'
//   posicao         posição no ranking (1 a 10)
//   celulas         células com desmatamento
//   nome            nome da área protegida
//   modalidade      'ti' | 'ucf' | 'uce'
//   categoria       categoria da área, ex.: Floresta Nacional
//   uso             Uso Sustentável | Proteção Integral | Terra Indígena
//   jurisdicao      Federal | Estadual
//   estado          UF(s), ex.: AM/PA
//   geom            MultiPolygon em EPSG:4326
const { Pool } = require('pg');

const DATABASE_URL = (process.env.DATABASE_URL || '').trim();
const AP_VIEW = (process.env.AP_DB_VIEW || 'imazongeo.vw_ameaca_pressao').trim();
const CACHE_MS = parseInt(process.env.AP_DB_CACHE_MS || '600000', 10); // 10 min, igual ao /dataset
const RETRY_MS = 60 * 1000; // banco fora do ar ou sem dados: tenta de novo após 1 min

// As áreas protegidas são grandes: o contorno original de um ano passa dos 15 MB.
// A simplificação (tolerância em graus, ~0,001° = 100 m) derruba isso para menos
// de 1 MB sem mudar o mapa na escala da Amazônia. AP_DB_SIMPLIFICAR=0 desliga.
const TOLERANCIA = Number(process.env.AP_DB_SIMPLIFICAR ?? '0.001');
const DECIMAIS = parseInt(process.env.AP_DB_DECIMAIS || '5', 10); // ~1 m

if (!/^[A-Za-z_]\w*(\.[A-Za-z_]\w*)?$/.test(AP_VIEW)) {
  throw new Error(`AP_DB_VIEW inválida: ${AP_VIEW}`);
}
if (!Number.isFinite(TOLERANCIA) || TOLERANCIA < 0 || TOLERANCIA > 1) {
  throw new Error(`AP_DB_SIMPLIFICAR inválida: ${process.env.AP_DB_SIMPLIFICAR}`);
}
if (!Number.isInteger(DECIMAIS) || DECIMAIS < 1 || DECIMAIS > 15) {
  throw new Error(`AP_DB_DECIMAIS inválida: ${process.env.AP_DB_DECIMAIS}`);
}

const RECORTES = ['geral', 'categ_ti', 'categ_uce', 'categ_ucf'];
const CLASSES = ['ameaca', 'pressao'];
const ANO_MIN = 2000;
const ANO_MAX = 2100;

// Geometria do jeito que o mapa recebe: simplificada (quando configurado) e com
// as casas decimais de AP_DB_DECIMAIS.
// ST_Multi porque a simplificação devolve Polygon quando a área tem uma parte só,
// e os arquivos do S3 trazem sempre MultiPolygon.
const geomSql = TOLERANCIA > 0
  ? `ST_AsGeoJSON(ST_Multi(ST_SimplifyPreserveTopology(geom, ${TOLERANCIA})), ${DECIMAIS})`
  : `ST_AsGeoJSON(geom, ${DECIMAIS})`;

// Propriedades com os mesmos nomes dos GeoJSON do S3 (dashboard/ap/geojson),
// para o index.html não precisar saber de onde veio o arquivo. 'count' repete
// 'celulas' como nos arquivos publicados.
const sqlGeojson = `
  SELECT count(*) AS total,
         json_build_object(
           'type', 'FeatureCollection',
           'features', coalesce(json_agg(json_build_object(
             'type', 'Feature',
             'properties', json_build_object(
               'dado', recorte, 'class', classe, 'nome', nome, 'estado', estado,
               'jurisdicao', jurisdicao, 'modalidade', modalidade,
               'categoria', categoria, 'uso', uso, 'rank', posicao,
               'celulas', celulas, 'count', celulas,
               'ano', ano, 'trimestre', trimestre, 'legend', legenda),
             'geometry', ${geomSql}::json)
             ORDER BY trimestre, posicao), '[]'::json))::text AS geojson
    FROM ${AP_VIEW}
   WHERE ano = $1 AND recorte = $2 AND classe = $3`;

// Anos e trimestres publicados, com a legenda de cada trimestre: a página monta
// os filtros de ano/trimestre e os rótulos de download com isso.
const sqlPeriodo = `
  SELECT ano, trimestre, min(legenda) AS legenda
    FROM ${AP_VIEW}
   GROUP BY ano, trimestre
   ORDER BY ano, trimestre`;

// Um trimestre inteiro (os 8 rankings) para os downloads, nos campos do padrão
// do imazongeo_upload e com a geometria completa: sem a simplificação do mapa.
const CAMPOS_DOWNLOAD = ['ano', 'trimestre', 'legenda', 'recorte', 'classe', 'posicao',
  'celulas', 'nome', 'modalidade', 'categoria', 'uso', 'jurisdicao', 'estado'];
const sqlDownload = `
  SELECT ${CAMPOS_DOWNLOAD.join(', ')}, ST_AsGeoJSON(geom)::json AS geometry
    FROM ${AP_VIEW}
   WHERE ano = $1 AND trimestre = $2
   ORDER BY recorte, classe, posicao`;

let pool = null;
function obterPool() {
  if (!pool) {
    pool = new Pool({
      connectionString: DATABASE_URL,
      max: 4,
      connectionTimeoutMillis: 3000,
      idleTimeoutMillis: 30000,
      statement_timeout: 120000
    });
    // Erro numa conexão ociosa (ex.: banco reiniciado) não pode derrubar o servidor
    pool.on('error', err => console.warn('Banco: conexão ociosa perdida:', err.message));
  }
  return pool;
}

// Loga só quando a fonte de um ano/recorte muda, para não repetir a cada consulta
const ultimaMensagem = new Map();
function registrar(chave, mensagem) {
  if (ultimaMensagem.get(chave) === mensagem) return;
  ultimaMensagem.set(chave, mensagem);
  console.log(`AP ${chave}: ${mensagem}`);
}

let indisponivelAte = 0;
function aoFalhar(chave, err) {
  indisponivelAte = Date.now() + RETRY_MS;
  const motivo = err.code === '42P01' ? `${AP_VIEW} não existe` : (err.message || err.code);
  registrar(chave, `banco indisponível (${motivo}); lendo do S3`);
  return null;
}

async function consultarGeojson(recorte, classe, ano) {
  const chave = `${ano}/${recorte}/${classe}`;
  try {
    const { rows } = await obterPool().query(sqlGeojson, [ano, recorte, classe]);
    // Ano ainda não carregado no banco: o navegador busca o arquivo do S3
    if (!Number(rows[0].total)) {
      registrar(chave, `sem dados em ${AP_VIEW}; lendo do S3`);
      return null;
    }
    registrar(chave, `lendo do banco (${AP_VIEW})`);
    return rows[0].geojson;
  } catch (err) {
    return aoFalhar(chave, err);
  }
}

async function consultarPeriodo() {
  try {
    const { rows } = await obterPool().query(sqlPeriodo);
    if (!rows.length) {
      registrar('periodo', `sem dados em ${AP_VIEW}; lendo do S3`);
      return null;
    }
    // [{ano, trimestres:[1,2], legendas:{'1':'janeiro a março'}}], do mais novo ao mais antigo
    const porAno = new Map();
    for (const r of rows) {
      if (!porAno.has(r.ano)) porAno.set(r.ano, { ano: r.ano, trimestres: [], legendas: {} });
      const item = porAno.get(r.ano);
      item.trimestres.push(r.trimestre);
      item.legendas[r.trimestre] = r.legenda;
    }
    const anos = [...porAno.values()].sort((a, b) => b.ano - a.ano);
    const ultimo = anos[0];
    registrar('periodo', `${anos[anos.length - 1].ano} a ${ultimo.ano}-T${Math.max(...ultimo.trimestres)}`);
    return JSON.stringify({
      ano_min: anos[anos.length - 1].ano,
      ano_max: ultimo.ano,
      trimestre_max: Math.max(...ultimo.trimestres),
      anos
    });
  } catch (err) {
    return aoFalhar('periodo', err);
  }
}

// chave -> { expira, valor: Promise<string|null> }; a Promise evita consultas
// repetidas quando vários navegadores pedem o mesmo arquivo ao mesmo tempo.
const cache = new Map();

function comCache(chave, consultar) {
  const item = cache.get(chave);
  if (item && item.expira > Date.now()) return item.valor;
  if (Date.now() < indisponivelAte) return Promise.resolve(null);

  const novo = { expira: Date.now() + CACHE_MS, valor: consultar() };
  novo.valor.then(v => { if (v === null) novo.expira = Date.now() + RETRY_MS; });
  if (cache.size > 60) cache.delete(cache.keys().next().value); // 6 anos x 4 recortes x 2 classes
  cache.set(chave, novo);
  return novo.valor;
}

// GeoJSON de um ranking (ano + recorte + classe) no layout dos arquivos do S3,
// ou null quando o banco não puder ser usado.
function geojsonAp(recorte, classe, ano) {
  const anoOk = Number.isInteger(ano) && ano >= ANO_MIN && ano <= ANO_MAX;
  if (!DATABASE_URL || !anoOk || !RECORTES.includes(recorte) || !CLASSES.includes(classe)) {
    return Promise.resolve(null);
  }
  return comCache(`${ano}/${recorte}/${classe}`, () => consultarGeojson(recorte, classe, ano));
}

// {ano_min, ano_max, trimestre_max, anos:[{ano, trimestres, legendas}]} do banco,
// ou null (a página então usa os anos/trimestres padrão dela)
function periodoAp() {
  if (!DATABASE_URL) return Promise.resolve(null);
  return comCache('periodo', consultarPeriodo);
}

// Linhas de um trimestre para os downloads (sem cache: cada formato é gerado
// na hora), ou null quando o banco não está configurado ou não respondeu.
async function linhasDownloadAp(ano, trimestre) {
  if (!DATABASE_URL) return null;
  try {
    const { rows } = await obterPool().query(sqlDownload, [ano, trimestre]);
    return rows;
  } catch (err) {
    console.warn(`AP download ${ano}-T${trimestre}: banco indisponível (${err.message || err.code})`);
    return null;
  }
}

module.exports = {
  geojsonAp, periodoAp, linhasDownloadAp, CAMPOS_DOWNLOAD,
  bancoConfigurado: !!DATABASE_URL, AP_VIEW
};
