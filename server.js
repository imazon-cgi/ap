// server.js
// Servidor Express para hospedar o index.html desta pasta e os datasets em /dataset
// Evita padrões de rota que quebram path-to-regexp (nada de "*" nem URL completa em app.get/app.use)

const path = require('path');
const express = require('express');
const compression = require('compression');
const helmet = require('helmet');

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
          "https://unpkg.com"
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

// ---- Estáticos ----

// /dataset → serve a pasta ./dataset (GeoJSON/CSV)
app.use('/dataset', express.static(DATASET_DIR, { setHeaders: setStaticHeaders }));

// Opcional: manter alias /dataset/sad → ./dataset (não use URLs completas aqui)
app.use('/dataset/sad', express.static(DATASET_DIR, { setHeaders: setStaticHeaders }));

// Raiz: serve tudo que estiver na pasta do projeto (onde está seu index.html)
app.use(express.static(ROOT_DIR, {
  setHeaders: setStaticHeaders
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
