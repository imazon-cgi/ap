// ecosystem.config.js
const path = require('path');
const fs   = require('fs');

function resolveAppDir(appName) {
  const candidates = [
    process.env.APP_DIR,                                        // caminho explícito (abs/rel)
    process.env.DASH_ROOT && path.join(process.env.DASH_ROOT, appName), // base + app
    path.join(__dirname, appName),                              // pasta irmã
    __dirname,                                                  // mesma pasta do ecosystem
    process.cwd()                                               // de onde pm2 foi executado
  ]
    .filter(Boolean)
    .map(p => path.resolve(p));

  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, 'server.js'))) {
      return dir;
    }
  }
  // fallback: primeiro candidato válido ou __dirname
  return candidates[0] || __dirname;
}

const APP_NAME   = process.env.APP_NAME || 'ap';
const APP_DIR    = resolveAppDir(APP_NAME);
const PORT_PROD  = Number(process.env.PORT_PROD || process.env.PORT || 3000);
const PORT_DEV   = Number(process.env.PORT_DEV  || 3001);

module.exports = {
  apps: [
    // Produção (sem watch)
    {
      name: APP_NAME,
      script: 'server.js',
      cwd: APP_DIR,
      exec_mode: 'fork',
      instances: 1,
      watch: false,
      max_memory_restart: '300M',
      autorestart: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'production',
        PORT: PORT_PROD
      }
    },

    // Desenvolvimento (com watch)
    {
      name: `${APP_NAME}-dev`,
      script: 'server.js',
      cwd: APP_DIR,
      exec_mode: 'fork',
      instances: 1,
      watch: [
        'server.js',
        'index.html',
        'img'
        // normalmente NÃO é necessário observar 'dataset'
      ],
      ignore_watch: [
        'node_modules',
        'logs',
        '.git',
        '.pm2',
        'dataset' // remova se quiser reiniciar ao mudar dados
      ],
      watch_options: {
        usePolling: true, // mais confiável no Windows
        interval: 1000
      },
      max_memory_restart: '300M',
      autorestart: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'development',
        PORT: PORT_DEV
      }
    }
  ]
};
