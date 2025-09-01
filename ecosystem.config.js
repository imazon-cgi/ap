// ecosystem.config.js
module.exports = {
  apps: [
    // Produção (sem watch)
    {
      name: 'ap',
      script: 'server.js',
      cwd: 'C:\\dashboards\\ap', // <-- ajuste se necessário
      exec_mode: 'fork',
      instances: 1,               // em Windows, 'fork' é o mais estável
      watch: false,
      max_memory_restart: '300M',
      autorestart: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      }
    },

    // Desenvolvimento (com watch)
    {
      name: 'ap-dev',
      script: 'server.js',
      cwd: 'C:\\dashboards\\ap', // <-- ajuste se necessário
      exec_mode: 'fork',
      instances: 1,
      watch: [
        'server.js',
        'index.html',
        'img'
        // normalmente NÃO é necessário observar 'dataset' (muito grande);
        // os arquivos estáticos são servidos sem reiniciar o servidor
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
        PORT: 3001
      }
    }
  ]
};
