# Contribuindo

Obrigado por querer ajudar.

## Issues

- Informe o sistema operacional, a versão do Python e passos reproduzíveis.
- Remova senhas, cookies, tokens, URLs temporárias e dados pessoais de logs e capturas.
- Para vulnerabilidades, siga o canal privado descrito em `SECURITY.md`.

## Pull requests

1. Faça um fork e crie uma branch a partir de `main`.
2. Explique o problema, a solução e qualquer impacto de compatibilidade.
3. Atualize documentação e exemplos quando a configuração ou o comportamento mudar.
4. Execute os testes antes de enviar:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py services scraping tests
```

Se a mudança afetar o container e o Docker estiver disponível, valide também:

```bash
docker compose config
docker build -t ok-api-movie:test .
```

O código Python deve ser legível e seguir PEP 8. Prefira mudanças focadas e não inclua arquivos gerados, ambientes virtuais, drivers, cookies ou credenciais.

## Ambiente local

```bash
python -m venv .venv
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e use apenas credenciais próprias de desenvolvimento. O `.env` nunca deve ser commitado.
