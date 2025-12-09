# Contribuindo

Obrigado por querer ajudar! Este guia resume como colaborar de forma organizada.

## Como abrir issues
- Descreva o problema/ideia, versao do Python/OS e passos para reproduzir.
- Para bugs, inclua logs/stack traces e, se possivel, prints.

## Como criar pull requests
1. Faca um fork e crie um branch a partir de `main` (ex: `feature/nome-curto` ou `fix/bug-curto`).
2. Inclua descricao clara do que muda e por que.
3. Sempre que possivel, teste localmente (`python app.py`, `python get_filmes.py` ou scripts especificos).
4. Mantenha o escopo enxuto; preferimos PRs pequenos e focados.

## Padroes de codigo
- Python: siga PEP8; evite linters agressivos, mas mantenha legibilidade.
- Comentarios so quando o codigo nao for obvio.
- Nao commit secrets (.env, cookies, etc.).

## Branches
- `main`: linha estavel.
- Crie branches de feature/fix a partir de `main`; depois, PR.

## Requisitos para aceitar PR
- CI verde (se configurado) ou testes locais informados na descricao.
- Sem quebra de compatibilidade intencional sem documentacao.
- Atualize a documentacao relevante (README, comentarios, exemplos).

## Ambiente rapido
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Dados sensiveis
- Scraper precisa de conta OK.ru: configure via `.env` local.
- Nao compartilhe cookies/senhas em issues ou PRs.
