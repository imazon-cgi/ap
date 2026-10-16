// server.js
// Servidor Express para hospedar o index.html desta pasta e os datasets em /dataset
// Evita padrões de rota que quebram path-to-regexp (nada de "*" nem URL completa em app.get/app.use)

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env'), quiet: true });
const fs = require('fs');
const os = require('os');
const { execFile } = require('child_process');
const { promisify } = require('util');
const express = require('express');
const compression = require('compression');
const helmet = require('helmet');
const {
  geojsonAp, periodoAp, linhasDownloadAp, CAMPOS_DOWNLOAD, bancoConfigurado, AP_VIEW
} = require('./banco');

const execFileAsync = promisify(execFile);

const app = express();
const PORT = process.env.PORT || 3001; // use 3001 se já tiver outro app na 3000

// Diretórios
const ROOT_DIR = __dirname;                         // onde está seu index.html (o HTML que você enviou)
const DATASET_DIR = path.join(ROOT_DIR, 'dataset'); // coloque seus arquivos em ./dataset

// ---- Segurança (CSP liberando CDNs usados + unsafe-eval para D3/pdfmake) ----
app.use(
  helmet({
    contentSecurityPolicy: {
      useDefaults: true,
      directives: {
        "default-src": ["'self'"],

        "script-src": [
          "'self'",
          "'unsafe-inline'",
          "'unsafe-eval'",
          "https://code.jquery.com",
          "https://cdn.jsdelivr.net",
          "https://unpkg.com",
          "https://cdnjs.cloudflare.com",
          "https://cdn.datatables.net"
        ],

        "style-src": [
          "'self'",
          "'unsafe-inline'",
          "https://fonts.googleapis.com",
          "https://cdn.jsdelivr.net",
          "https://cdnjs.cloudflare.com",
          "https://cdn.datatables.net",
          "https://unpkg.com"
        ],

        "font-src": [
          "'self'",
          "https://fonts.gstatic.com",
          "https://cdn.jsdelivr.net",
          "https://cdnjs.cloudflare.com"
        ],

        // Libera imagens necessárias: data:/blob: + tiles OSM e CARTO + ícones/arquivos que você usa
        "img-src": [
          "'self'",
          "data:",
          "blob:",
          "https://*.tile.openstreetmap.org",          // OSM
          "https://*.basemaps.cartocdn.com",           // Carto (a|b|c|d)
          "https://unpkg.com",                          // ícones do Leaflet se servidos de lá
          "https://imazongeo3-web.s3.sa-east-1.amazonaws.com" // seu S3 (ajuste se usar outro bucket)
        ],

        // Necessário para baixar sourcemap do Leaflet via unpkg e quaisquer fetch/XHR que você faça
        "connect-src": [
          "'self'",
          "https://*.tile.openstreetmap.org",
          "https://cdn.datatables.net",
          "https://cdnjs.cloudflare.com",
          "https://cdn.jsdelivr.net",
          "https://unpkg.com",
          "https://imazongeo3-web.s3.amazonaws.com",
          "https://imazongeo3-web.s3.sa-east-1.amazonaws.com"
        ],

        // Para libs que usam Web Workers (ex.: html2canvas, leaflet-image, etc.)
        "worker-src": ["'self'", "blob:"],

        "object-src": ["'none'"],
        "frame-ancestors": ["'self'"]
      }
    },
    crossOriginEmbedderPolicy: false,
    crossOriginOpenerPolicy: { policy: "same-origin-allow-popups" },
    crossOriginResourcePolicy: { policy: "cross-origin" },
    referrerPolicy: { policy: "no-referrer-when-downgrade" }
  })
);

// ---- Compressão ----
app.use(compression({ threshold: 1024 }));

// ---- Headers de cache/MIME para arquivos estáticos ----
function setStaticHeaders(res, filePath) {
  const fp = filePath.toLowerCase();

  if (fp.endsWith('.geojson')) {
    res.type('application/geo+json; charset=utf-8');
  } else if (fp.endsWith('.csv')) {
    res.type('text/csv; charset=utf-8');
  } else if (fp.endsWith('.json')) {
    res.type('application/json; charset=utf-8');
  }

  if (fp.includes('/dataset/') || fp.endsWith('.csv') || fp.endsWith('.geojson') || fp.endsWith('.json')) {
    res.setHeader('Cache-Control', 'public, max-age=600, stale-while-revalidate=120'); // 10 min
  } else if (/\.(js|css|png|jpg|jpeg|webp|svg|ico|woff2?|ttf)$/.test(fp)) {
    res.setHeader('Cache-Control', 'public, max-age=604800, immutable'); // 7 dias
  } else {
    res.setHeader('Cache-Control', 'no-cache');
  }
}

console.log('Banco do AP:', bancoConfigurado ? AP_VIEW : 'DATABASE_URL não definida (só S3)');

// ---- Rankings de Ameaça e Pressão no banco ----
// 503 quando o banco não está configurado/ativo ou ainda não tem o ano pedido:
// o navegador então lê o GeoJSON correspondente do S3.
function semBanco(res) {
  res.setHeader('Cache-Control', 'no-store');
  res.status(503).type('text/plain').send('Ameaça e Pressão indisponível no banco');
}

function comCacheDe10Min(res, tipoMime) {
  res.type(tipoMime);
  res.setHeader('Cache-Control', 'public, max-age=600, stale-while-revalidate=120');
}

// Anos, trimestres e legendas do banco: a página monta com eles os filtros de
// ano/trimestre e os rótulos da lista de downloads
app.get('/api/ap/periodo', async (_req, res) => {
  const periodo = await periodoAp();
  if (periodo === null) return semBanco(res);
  comCacheDe10Min(res, 'application/json; charset=utf-8');
  res.send(periodo);
});

// Um ranking por requisição, no mesmo recorte dos arquivos do S3:
// /api/ap/geral/ameaca.geojson?ano=2025 ↔ ameaca_e_pressao_2025_geral_ameaca.geojson
app.get('/api/ap/:recorte/:classe.geojson', async (req, res) => {
  const geojson = await geojsonAp(req.params.recorte, req.params.classe, parseInt(req.query.ano, 10));
  if (geojson === null) return semBanco(res);
  comCacheDe10Min(res, 'application/geo+json; charset=utf-8');
  res.send(geojson);
});

// ---- Downloads (como no SAD) ----
// Um trimestre inteiro (os 8 rankings) gerado na hora a partir da visão PostGIS,
// para CSV, GeoJSON e Shapefile trazerem exatamente o mesmo recorte:
//   /api/ap/download/2025/4.csv                 CSV (UTF-8 com BOM, sem geometria)
//   /api/ap/download/2025/4.zip?formato=geojson GeoJSON em ZIP
//   /api/ap/download/2025/4.zip                 Shapefile em ZIP
// O CSV fica sem geometria, como no padrão do imazongeo_upload: os contornos das
// áreas protegidas passam do limite de caracteres por célula do Excel.
function csvDownload(linhas) {
  const esc = v => {
    const s = String(v ?? '');
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const corpo = linhas.map(l => CAMPOS_DOWNLOAD.map(c => esc(l[c])).join(','));
  return '﻿' + [CAMPOS_DOWNLOAD.join(','), ...corpo].join('\n') + '\n';
}

app.get('/api/ap/download/:ano/:trimestre.:formato', async (req, res) => {
  const ano = Number(req.params.ano);
  const trimestre = Number(req.params.trimestre);
  const formato = String(req.params.formato).toLowerCase();
  if (!Number.isInteger(ano) || !Number.isInteger(trimestre) || trimestre < 1 || trimestre > 4 ||
      !['csv', 'geojson', 'zip'].includes(formato)) {
    return res.status(400).type('text/plain').send('Parâmetros inválidos');
  }

  const linhas = await linhasDownloadAp(ano, trimestre);
  if (linhas === null) return semBanco(res);
  if (!linhas.length) return res.status(404).type('text/plain').send('Sem dados para o período');

  const nome = `ameaca_e_pressao_${ano}_t${trimestre}`;
  if (formato === 'csv') {
    res.type('text/csv; charset=utf-8');
    return res.attachment(`${nome}.csv`).send(csvDownload(linhas));
  }

  const fc = {
    type: 'FeatureCollection',
    features: linhas.map(l => ({
      type: 'Feature',
      properties: Object.fromEntries(CAMPOS_DOWNLOAD.map(c => [c, l[c]])),
      geometry: l.geometry
    }))
  };
  if (formato === 'geojson') {
    res.type('application/geo+json; charset=utf-8');
    return res.attachment(`${nome}.geojson`).send(JSON.stringify(fc));
  }

  // ZIP: o GeoJSON (?formato=geojson) ou o Shapefile convertido pelo ogr2ogr
  const tmp = await fs.promises.mkdtemp(path.join(os.tmpdir(), `ap-${ano}-t${trimestre}-`));
  const limpar = () => fs.promises.rm(tmp, { recursive: true, force: true });
  try {
    const geo = path.join(tmp, `${nome}.geojson`);
    const zip = path.join(tmp, `${nome}.zip`);
    await fs.promises.writeFile(geo, JSON.stringify(fc));
    if (req.query.formato === 'geojson') {
      await execFileAsync('zip', ['-j', '-q', zip, geo]);
    } else {
      const shp = path.join(tmp, 'shapefile');
      await fs.promises.mkdir(shp);
      await execFileAsync('ogr2ogr', ['-f', 'ESRI Shapefile', '-lco', 'ENCODING=UTF-8', shp, geo]);
      const partes = (await fs.promises.readdir(shp)).map(a => path.join(shp, a));
      await execFileAsync('zip', ['-j', '-q', zip, ...partes]);
    }
    res.download(zip, `${nome}.zip`, limpar);
  } catch (e) {
    await limpar();
    res.status(500).type('text/plain').send(`Falha ao gerar arquivo: ${e.message}`);
  }
});

// ---- Estáticos ----

// Arquivos do servidor ficam fora: o .env tem a senha do banco, e a configuração
// não interessa ao navegador.
const ARQUIVOS_PRIVADOS = /^\/(\.env|server\.js|banco\.js|package(-lock)?\.json|ecosystem\.config\.js|logs(\/|$))/;
app.use((req, res, next) => {
  if (ARQUIVOS_PRIVADOS.test(req.path)) return res.status(404).type('text/plain').send('Not found');
  next();
});

// /dataset → serve a pasta ./dataset (GeoJSON/CSV)
app.use('/dataset', express.static(DATASET_DIR, { setHeaders: setStaticHeaders }));

// Opcional: manter alias /dataset/sad → ./dataset (não use URLs completas aqui)
app.use('/dataset/sad', express.static(DATASET_DIR, { setHeaders: setStaticHeaders }));

// Raiz: serve tudo que estiver na pasta do projeto (onde está seu index.html)
app.use(express.static(ROOT_DIR, {
  setHeaders: setStaticHeaders,
  dotfiles: 'ignore' // .env e outros arquivos ocultos
}));

// Healthcheck simples
app.get('/healthz', (_req, res) => res.status(200).send('ok'));

app.use((req, res, next) => {
  try {
    if (req.method !== 'GET') return next();
    // Se o caminho tem extensão (.js, .css, .png etc.), deixa os estáticos cuidarem
    if (path.extname(req.path)) return next();
    // Envia o index.html da raiz
    return res.sendFile(path.join(ROOT_DIR, 'index.html'));
  } catch (e) {
    return next(e);
  }
});

// 404 para qualquer outra coisa que tenha passado pelos middlewares
app.use((req, res) => res.status(404).send('Not found'));

// ---- Start ----
app.listen(PORT, () => {
  console.log(`✅ Server em http://localhost:${PORT}`);
  console.log(`📁 Raiz:        ${ROOT_DIR}`);
  console.log(`📂 /dataset ->  ${DATASET_DIR}`);
});
