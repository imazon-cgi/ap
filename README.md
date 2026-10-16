# AP

Dashboard de Ameaça e Pressão em Áreas Protegidas, servido por um servidor Express.

Os rankings vêm do banco do ImazonGeo (projeto `imazongeo_upload`) quando ele está
configurado; sem banco — ou quando o ano pedido ainda não foi carregado nele — a
página lê os GeoJSON publicados no S3, como antes.

## Requisitos

- Node.js 18 ou superior
- npm 9 ou superior
- Acesso à internet para carregar bibliotecas front-end via CDN e camadas de mapa externas
- Opcional: PostgreSQL/PostGIS do ImazonGeo, com a visão `imazongeo.vw_ameaca_pressao`

## Instalação

Se ainda não existir a pasta `node_modules`, instale as dependências:

```powershell
npm install
```

## Banco de dados (opcional)

Copie `.env.example` para `.env` e aponte `DATABASE_URL` para o banco do ImazonGeo:

```powershell
DATABASE_URL=postgresql://usuario:senha@localhost:5432/imazongeo
```

Ao subir, o servidor informa a fonte no log:

```
Banco do AP: imazongeo.vw_ameaca_pressao
Banco do AP: DATABASE_URL não definida (só S3)
```

Rotas servidas a partir do banco (`banco.js`):

- `GET /api/ap/periodo` — anos, trimestres e legendas publicados
- `GET /api/ap/{recorte}/{classe}.geojson?ano=AAAA` — um ranking, com `recorte` em
  `geral`, `categ_ti`, `categ_uce` ou `categ_ucf` e `classe` em `ameaca` ou `pressao`

Cada rota responde `503` quando o banco não está configurado, está fora do ar ou
ainda não tem o que foi pedido; nesse caso a página busca o arquivo equivalente em
`https://imazongeo3-web.s3.amazonaws.com/dashboard/ap/geojson/`.

Variáveis aceitas (todas opcionais, ver `.env.example`):

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `AP_DB_VIEW` | `imazongeo.vw_ameaca_pressao` | Visão lida no banco |
| `AP_DB_CACHE_MS` | `600000` | Cache das respostas do banco (10 min) |
| `AP_DB_SIMPLIFICAR` | `0.001` | Simplificação das geometrias, em graus (≈100 m); `0` desliga |
| `AP_DB_DECIMAIS` | `5` | Casas decimais das coordenadas (≈1 m) |

A simplificação é o que faz o ranking de um ano sair em menos de 1 MB, contra
dezenas de MB do arquivo publicado no S3.

## Como executar localmente

Forma recomendada:

```powershell
npm start
```

Forma direta, sem usar script do `package.json`:

```powershell
node .\server.js
```

Após iniciar, a aplicação fica disponível em:

- `http://localhost:3001`

Health check:

- `http://localhost:3001/healthz`

Se tudo estiver certo, o endpoint acima deve responder `ok`.

## Alterar a porta

Por padrão, `server.js` usa a porta `3001`. Para subir em outra porta no PowerShell:

```powershell
$env:PORT=8080
npm start
```

Depois abra:

- `http://localhost:8080`

## Estrutura importante

Os arquivos e pastas abaixo precisam existir para a aplicação funcionar corretamente:

- `index.html`
- `server.js`
- `banco.js`
- `img/`
- `.env` (só se for usar o banco)

Os rankings e o contorno da Amazônia Legal vêm do banco ou do S3; não há mais
arquivos de dados no repositório.

## Executar com PM2

O repositório já inclui um `ecosystem.config.js`.

Instale o PM2, se necessário:

```powershell
npm install -g pm2
```

Subir em modo produção:

```powershell
pm2 start ecosystem.config.js --only ap
```

Nesse modo, a porta padrão é `3000`.

Subir em modo desenvolvimento com watch:

```powershell
pm2 start ecosystem.config.js --only ap-dev
```

Nesse modo, a porta padrão é `8050`.

Comandos úteis:

```powershell
pm2 logs ap
pm2 logs ap-dev
pm2 restart ap
pm2 restart ap-dev
pm2 delete ap
pm2 delete ap-dev
```

## Problemas comuns

### 1. Abrir o `index.html` direto no navegador

Não funciona corretamente via `file://`, porque a aplicação faz `fetch` em rotas como `/api/ap/...`.

Use sempre o servidor Node.

### 2. Porta já está em uso

Defina outra porta antes de iniciar:

```powershell
$env:PORT=8080
npm start
```

### 3. Mapa ou bibliotecas não carregam

O front-end depende de recursos externos, como:

- Bootstrap CDN
- Leaflet CDN
- Chart.js CDN
- DataTables CDN
- tiles do CARTO/OpenStreetMap

Se estiver sem internet ou atrás de bloqueios de rede, a interface pode carregar parcialmente.

### 4. Dados não aparecem

Confira o log do servidor: ele diz, para cada ano/recorte, se está lendo do banco ou
caindo no S3 (`AP 2025/geral/ameaca: lendo do banco (imazongeo.vw_ameaca_pressao)`).

Sem banco, a página depende do bucket `imazongeo3-web`; verifique o acesso à internet.
Com banco, verifique `DATABASE_URL` e se a visão `imazongeo.vw_ameaca_pressao` existe:

```powershell
psql $env:DATABASE_URL -c "SELECT ano, trimestre, count(*) FROM imazongeo.vw_ameaca_pressao GROUP BY 1,2 ORDER BY 1,2"
```

## Resumo rápido

```powershell
npm install
npm start
```

Abra:

- `http://localhost:3001`
