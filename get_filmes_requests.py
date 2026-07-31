from pathlib import Path
import os
import runpy

LOG = 1  # 1 = ativa log resumido, 0 = desativa

if __name__ == "__main__":
    # Dica: descomente apenas as variaveis que quiser forcar nesta execucao.
    # Se preferir, mantenha no .env e deixe tudo comentado aqui.
    #
    SERVER_IDS = []  # exemplo: [114, 395, 7]; deixe [] para nao filtrar por id
    if SERVER_IDS:
        os.environ["OKRU_SERVER_IDS"] = ",".join(str(x) for x in SERVER_IDS)
    # os.environ["OKRU_IGNORE_DAYS"] = "30"            # ignora idserver atualizado nos ultimos X dias
    # os.environ["OKRU_RESUME_FROM_IDSERVER"] = "200"  # retoma a partir deste idserver
    # os.environ["OKRU_REQUESTS_DRY_RUN"] = "1"        # 1 = nao grava no banco
    os.environ["OKRU_REQUESTS_MAX_EXTRA_PAGES"] = "2500"  # suporta perfis muito grandes (50k+)
    os.environ["OKRU_MAX_WORKERS"] = "3"             # perfis em paralelo (recomendado iniciar com 2)
    #
    # Robustez/performance de banco e rede
    os.environ.setdefault("OKRU_DB_FLUSH_EVERY", "1000")
    os.environ.setdefault("OKRU_DB_WRITE_CHUNK", "500")
    os.environ.setdefault("OKRU_DB_WRITE_RETRIES", "5")
    os.environ.setdefault("OKRU_DB_CONNECT_RETRIES", "10")
    os.environ.setdefault("OKRU_REQUESTS_AUTO_COOKIE_LOGIN", "1")
    os.environ.setdefault("OKRU_REQUESTS_AUTO_COOKIE_LOGIN_FORCE_HEADLESS", "1")
    # os.environ["OKRU_REQUESTS_AUTO_COOKIE_LOGIN_ALLOW_MANUAL"] = "1"  # abre browser para completar desafio
    # os.environ["OKRU_HTTP_RETRIES"] = "4"
    os.environ["OKRU_LOG"] = str(LOG)

    root = Path(__file__).resolve().parent
    target = root / "scraping" / "get_filmes_requests.py"
    os.chdir(root / "scraping")
    runpy.run_path(str(target), run_name="__main__")
