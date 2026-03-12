# AP

Aplicação web estática servida por um servidor Express. O projeto entrega o arquivo `index.html`, a pasta `img/` e os arquivos de dados em `dataset/`.

## Requisitos

- Node.js 18 ou superior
- npm 9 ou superior
- Acesso à internet para carregar bibliotecas front-end via CDN e camadas de mapa externas

## Instalação

Se ainda não existir a pasta `node_modules`, instale as dependências:

```powershell
npm install
```

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
- `img/`
- `dataset/AMZ_legal_amz_legal.geojson`
- `dataset/ap/geojson/`

Sem esses dados, o mapa e os painéis não carregam corretamente.

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

Não funciona corretamente via `file://`, porque a aplicação faz `fetch` em rotas como `/dataset/...`.

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

Verifique se os arquivos `.geojson`, `.json`, `.csv` e `.parquet` continuam dentro da pasta `dataset/` na mesma estrutura do repositório.

## Resumo rápido

```powershell
npm install
npm start
```

Abra:

- `http://localhost:3001`
