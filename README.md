# OK API Movie

Busca vídeos do OK.ru (via API oficial ou banco próprio), toca no navegador e exibe metadados localizados usando TMDB com fallback IMDb.

## Funcionalidades
- Busca direta na API do OK.ru (não precisa login/banco) ou no Postgres raspado pelo scraper.
- Player embutido com seleção de qualidade e botão de download (yt-dlp).
- Metadados: título/sinopse/gêneros/nota em `pt-BR | es-ES | en-US` via TMDB; fallback IMDb em inglês quando TMDB não encontrar.
- Limpeza de títulos de release (guessit + heurísticas PT-BR) para acertar a busca por ano/título.
- Cache em Postgres (`infofilmes`) para não refazer consultas.
- Front responsivo (tema claro/escuro, idiomas, filtros, fallback de imagem para thumbs quebradas).

## Requisitos
- Python 3.11+
- PostgreSQL
- (Opcional) Google Chrome/Chromium + chromedriver (apenas para o scraper `get_filmes.py`)

## Variáveis de ambiente (.env)
```
DB_HOST=...
DB_DATABASE=...
DB_USER=...
DB_PASSWORD=...
DB_PORT=...

OKRU_EMAIL=...          # só para scraper
OKRU_PASSWORD=...       # só para scraper
OKRU_HEADLESS=True      # só para scraper

KEY_API_TMDB=...        # API key TMDB
TOKEN_API_TMDB=...      # Bearer TMDB (opcional se já tiver KEY)
```

## Instalação rápida
```bash
git clone <repo>
cd ok_api_movie
python -m venv .venv
.venv/Scripts/activate    # Windows (ou source .venv/bin/activate no Linux/mac)
pip install -r requirements.txt
```

## Rodar o app Flask
```bash
python app.py
# abre em http://127.0.0.1:5000
```

### Filtros do frontend
- Fonte: `API` (OK.ru web) ou `Banco` (tabela `filmes`).
- Duração (API), HD on/off.
- Duração/ordenação (Banco).
- Idioma: PT / EN / ES (passa `lang` para TMDB e título do modal).

### Metadados
1. Limpa o título (guessit + heurística PT-BR) e tenta TMDB (multi search, com/sem ano, fallback en-US).
2. Se TMDB não achar, tenta API IMDb não oficial (en-US).
3. Atualiza título do modal se vier vazio na abertura.
4. Persistência em `infofilmes` só ocorre quando há resultado de API.

## Scraper (opcional)
`get_filmes.py` usa Selenium para autenticar no OK.ru e popular `filmes`. Preencha `OKRU_EMAIL/OKRU_PASSWORD` e configure tabela `server`/`filmes` (veja `CONTRIBUTING.md` ou código).

## Estrutura
- `app.py` — Flask, rotas de busca/download/info.
- `services/tmdb_client.py` — TMDB search/detail com pontuação de candidatos.
- `services/imdb_fallback.py` — fallback IMDb.
- `utils/title_cleaner.py` — limpeza de títulos e geração de candidatos.
- `templates/index.html` + `static/` — frontend (tema, filtros, modal, fallback de imagem).
- `get_filmes.py` — scraper OK.ru -> Postgres.

## Deploy (Vercel/WSGI)
- Apenas Python puro; garanta que `requirements.txt` inclua `rapidfuzz` e `guessit`.
- Configure as variáveis de ambiente no provedor.
- Entry-point continua sendo `app.py` (Flask).
