# OK API Movie

Aplicação Flask para pesquisar vídeos do OK.ru, reproduzi-los no navegador e enriquecer os resultados com metadados do TMDB ou IMDb. A página pública continua disponível sem conta; um login administrativo opcional libera a consulta de resoluções reais e o envio ao JDownloader.

## Funcionalidades

- Busca pela interface web do OK.ru ou por um catálogo PostgreSQL local.
- Player incorporado, seleção de qualidade e download com `yt-dlp`.
- Login administrativo de usuário único com sessão, proteção CSRF e limite de tentativas.
- Detecção das resoluções realmente disponíveis, incluindo 1440p e 2160p/4K quando a origem oferecer esses formatos.
- Envio autenticado ao MyJDownloader e início automático do download.
- Metadados localizados em `pt-BR`, `es-ES` e `en-US` via TMDB, com fallback IMDb.
- Interface responsiva, tema claro/escuro, filtros e fallback para miniaturas quebradas.

## Requisitos

- Python 3.11 ou mais recente.
- Docker com o plugin Compose para a instalação recomendada no CasaOS.
- PostgreSQL somente para a fonte `Banco`, o cache de metadados e os scrapers.
- Uma conta MyJDownloader somente para o botão de envio ao servidor.
- Chrome/Chromium somente para os scrapers que precisarem criar ou renovar cookies.

## Instalação

```bash
git clone https://github.com/mgbrusque/ok_api_movie.git
cd ok_api_movie
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source .venv/bin/activate
```

Instale as dependências e crie o arquivo local de configuração:

```bash
pip install -r requirements.txt
cp .env.example .env
```

No Windows, o último comando pode ser substituído por `Copy-Item .env.example .env`.

## Configuração

O arquivo `.env` é ignorado pelo Git. Preencha apenas os grupos de recursos que pretende usar; consulte [`.env.example`](.env.example) para a lista completa.

### Página pública e metadados

As buscas pela fonte `API` funcionam sem PostgreSQL. Para metadados do TMDB, configure ao menos uma das opções:

```dotenv
KEY_API_TMDB=
TOKEN_API_TMDB=
```

Para usar a fonte `Banco`, o cache e os scrapers, configure PostgreSQL e aplique [`schema.sql`](schema.sql):

```dotenv
DB_HOST=localhost
DB_DATABASE=ok_api_movie
DB_USER=ok_api_movie
DB_PASSWORD=
DB_PORT=5432
```

```bash
psql -d ok_api_movie -f schema.sql
```

### Login administrativo

Gere o hash sem exibir a senha no terminal e crie uma chave de sessão persistente:

```bash
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Senha: ')))"
python -c "import secrets; print(secrets.token_hex(32))"
```

Coloque os resultados no `.env`:

```dotenv
APP_ADMIN_USERNAME=admin
APP_ADMIN_PASSWORD_HASH=
FLASK_SECRET_KEY=
ADMIN_SESSION_HOURS=12
ADMIN_LOGIN_MAX_ATTEMPTS=5
ADMIN_LOGIN_WINDOW_MINUTES=15
SESSION_COOKIE_SECURE=false
```

Use `SESSION_COOKIE_SECURE=false` apenas em HTTP local. Em produção atrás de HTTPS, use `true`. Depois de alterar o hash ou a chave, reinicie a aplicação; sessões antigas deixam de ser válidas.

O bloqueio de login é mantido em memória por processo. Para várias réplicas ou proteção persistente, complemente-o no proxy reverso ou use um limitador com armazenamento compartilhado.

### MyJDownloader

Conecte primeiro o JDownloader à sua conta em **Configurações > My.JDownloader** e use exatamente o mesmo nome do dispositivo no `.env`:

```dotenv
MYJD_EMAIL=
MYJD_PASSWORD=
MYJD_DEVICE=nome-do-dispositivo
MYJD_DOWNLOAD_FOLDER=/output
JDOWNLOADER_WEB_URL=https://jdownloader.example.com/
```

`MYJD_DOWNLOAD_FOLDER` é o caminho visto de dentro do container. Em CasaOS/Docker, mapeie uma pasta do host para esse destino. `JDOWNLOADER_WEB_URL` é opcional e apenas controla o link **Abrir JDownloader**; autenticação HTTP Basic ou outra proteção do Nginx continua sendo responsabilidade do proxy.

No primeiro envio, a aplicação cria ou atualiza uma regra `DIRECTHTTP` chamada `Cooframe OK CDN`, restrita a subdomínios `okcdn.ru`, para repassar o `User-Agent` exigido pelo CDN. As demais regras do JDownloader são preservadas.

## Instalar no CasaOS

O CasaOS é a hospedagem recomendada para o painel administrativo e o JDownloader. Diferentemente da Vercel, o container permanece ativo e o Gunicorn pode aguardar a extração e o LinkGrabber.

### Opção 1: construir no próprio servidor

Abra o terminal do servidor CasaOS e execute:

```bash
cd /DATA/AppData
git clone https://github.com/mgbrusque/ok_api_movie.git
cd ok_api_movie
cp .env.example .env
mkdir -p data
```

Edite `.env`, configure as credenciais e, em produção HTTPS, ajuste pelo menos:

```dotenv
APP_PORT=5000
APP_DATA_DIR=/DATA/AppData/ok_api_movie/data
PUID=1000
PGID=1000
SESSION_COOKIE_SECURE=true
GUNICORN_WORKERS=1
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=300
```

Garanta que o usuário do container possa gravar os cookies e artefatos persistentes e suba a aplicação:

```bash
sudo chown -R 1000:1000 /DATA/AppData/ok_api_movie/data
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

A interface ficará em `http://IP_DO_CASAOS:5000`. No CasaOS, você pode criar um ícone em **Instalação personalizada** apontando a Web UI para essa porta; o container já estará sendo gerenciado pelo Docker Compose.

### Opção 2: imagem pronta do GitHub

O workflow `Container` publica imagens `amd64` e `arm64` no GitHub Container Registry. Depois da primeira publicação, defina a visibilidade do pacote como pública e use:

```bash
docker compose -f compose.casaos.yml pull
docker compose -f compose.casaos.yml up -d
```

O arquivo `compose.casaos.yml` também pode ser usado como base na instalação personalizada do CasaOS. Ele usa a imagem `ghcr.io/mgbrusque/ok_api_movie:latest` e o diretório `/DATA/AppData/ok_api_movie/data` quando `APP_DATA_DIR` não for informado.

### Proxy reverso e JDownloader

No Nginx, encaminhe o domínio da aplicação para `http://IP_DO_CASAOS:5000` e mantenha HTTPS ativo. O JDownloader pode continuar em seu próprio container e domínio protegido.

O OK API Movie usa a API em nuvem do MyJDownloader, portanto não exponha a porta `3129` e não é necessário colocar os dois containers na mesma rede. `MYJD_DOWNLOAD_FOLDER=/output` continua representando o caminho dentro do container do JDownloader; o container desta aplicação não precisa montar a pasta dos filmes.

O volume `/data` preserva `okru_cookies.json` e artefatos dos scrapers. Chromium e Chromedriver já estão incluídos na imagem e são configurados automaticamente pelo Compose.

### Atualizar no CasaOS

Para uma instalação construída no servidor:

```bash
cd /DATA/AppData/ok_api_movie
git pull --ff-only
docker compose up -d --build
```

Para a imagem pronta:

```bash
docker compose -f compose.casaos.yml pull
docker compose -f compose.casaos.yml up -d
```

## Executar

Desenvolvimento local:

```bash
python app.py
# http://127.0.0.1:5000
```

Produção Linux com Gunicorn:

```bash
gunicorn --config gunicorn.conf.py app:app
```

Produção Windows com Waitress:

```powershell
waitress-serve --listen=0.0.0.0:5000 app:app
```

Use HTTPS no proxy reverso, mantenha `.env` fora da imagem pública e não exponha diretamente as portas internas do JDownloader.

## Como usar

1. Pesquise e abra um filme normalmente; isso não exige login.
2. Clique em **Login** para liberar o painel administrativo.
3. Clique em **Verificar resoluções**. A lista mostra somente formatos detectados na origem; 4K aparece como `2160p` quando existir.
4. Escolha o formato e clique em **Enviar ao JDownloader**.

As rotas `/admin/formats/<id>` e `/admin/jdownloader` exigem sessão administrativa. O envio também exige o token CSRF da sessão.

## Scrapers opcionais

- `python get_filmes.py`: Selenium, útil quando é necessário um navegador completo.
- `python get_filmes_requests.py`: fluxo principal por HTTP; pode abrir Chrome automaticamente para obter cookies quando eles não existem ou expiraram.

Configure `OKRU_EMAIL`, `OKRU_PASSWORD` e as opções `OKRU_*` no `.env`. Nunca versione cookies, credenciais, `.wdm` ou artefatos de execução.

## Testes

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py services scraping tests
```

## Estrutura principal

- `app.py`: aplicação Flask e rotas HTTP.
- `services/auth.py`: sessão administrativa, CSRF e limite de tentativas.
- `services/jdownloader_client.py`: integração MyJDownloader.
- `services/ok_client.py`: busca, extração e formatos do OK.ru.
- `services/tmdb_client.py` e `services/imdb_fallback.py`: metadados.
- `services/video_repository.py`: consultas ao catálogo PostgreSQL.
- `scraping/`: coletores Selenium e HTTP.
- `templates/` e `static/`: interface web.
- `tests/`: testes automatizados.
- `Dockerfile`, `compose.yml` e `compose.casaos.yml`: implantação persistente no CasaOS.
- `gunicorn.conf.py`: workers, threads, porta e timeout da aplicação em produção.

## Vercel e ambientes serverless

O arquivo `vercel.json` mantém compatibilidade básica com a página pública. Sessões, limite de login em memória, extração com `yt-dlp` e espera pelo LinkGrabber podem ser reiniciados ou atingir limites de execução em plataformas serverless. Para o painel administrativo e o JDownloader, prefira um processo WSGI persistente em CasaOS, Docker ou VM.

## Segurança

Não publique `.env`, cookies, dumps de banco, links de mídia temporários ou tokens em commits, issues e logs. Se uma credencial já tiver entrado no histórico, removê-la do arquivo atual não basta: revogue-a, gere outra e limpe o histórico Git. Consulte [`SECURITY.md`](SECURITY.md) para relatar vulnerabilidades.

## Licença

Distribuído sob a licença MIT. Consulte [`LICENSE`](LICENSE).
