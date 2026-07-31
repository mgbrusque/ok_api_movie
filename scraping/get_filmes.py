import time
import datetime
import psycopg2
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from psycopg2.extras import execute_batch
from psycopg2 import DataError

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = Path(os.environ.get("OKRU_ARTIFACTS_DIR", str(BASE_DIR / "artifacts")))


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name, default=0):
    val = os.environ.get(name)
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# CONFIG #
EMAIL = os.environ.get("OKRU_EMAIL")
PASSWORD = os.environ.get("OKRU_PASSWORD")
HEADLESS = env_bool("OKRU_HEADLESS", True)
DEBUG_LOGIN = env_bool("OKRU_DEBUG_LOGIN", False)
MANUAL_LOGIN = env_bool("OKRU_MANUAL_LOGIN", False)
MANUAL_LOGIN_WAIT_SEC = env_int("OKRU_MANUAL_LOGIN_WAIT_SEC", 180)
LOGIN_PAGE = "https://ok.ru/dk?st.cmd=anonymMain"
COOKIES_FILE = os.environ.get("OKRU_COOKIES_FILE", str(BASE_DIR / "okru_cookies.json"))


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_DATABASE"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT"),
    )


MAX_TXT = 200
SQL_INSERT = """
    INSERT INTO filmes (id, nome, tempo, imagem, idserver, ordernum, created_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (id) DO UPDATE SET
        nome       = EXCLUDED.nome,
        tempo      = EXCLUDED.tempo,
        imagem     = EXCLUDED.imagem,
        idserver   = EXCLUDED.idserver,
        ordernum   = EXCLUDED.ordernum,
        created_at = EXCLUDED.created_at
"""


conn = None
cursor = None


def ensure_connection():
    global conn, cursor
    if conn is None or conn.closed or cursor.closed:
        print("[info] Recriando conexao com o banco...")
        conn = get_conn()
        cursor = conn.cursor()


def start_driver():
    os.environ.setdefault("WDM_LOCAL", "1")

    opt = Options()
    if HEADLESS:
        opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-blink-features=AutomationControlled")
    opt.add_argument("--disable-software-rasterizer")
    opt.add_argument("--disable-features=VizDisplayCompositor")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("useAutomationExtension", False)
    opt.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        },
    )

    chrome_binary = (os.environ.get("OKRU_CHROME_BINARY") or "").strip()
    if chrome_binary:
        opt.binary_location = chrome_binary

    chrome_user_data_dir = (os.environ.get("OKRU_CHROME_USER_DATA_DIR") or "").strip()
    chrome_profile = (os.environ.get("OKRU_CHROME_PROFILE") or "").strip()
    if chrome_user_data_dir:
        opt.add_argument(f"--user-data-dir={chrome_user_data_dir}")
    if chrome_profile:
        opt.add_argument(f"--profile-directory={chrome_profile}")

    # Don't wait for full load; the login form appears earlier.
    opt.page_load_strategy = "eager"

    chromedriver_binary = (os.environ.get("OKRU_CHROMEDRIVER") or "").strip()
    if chromedriver_binary:
        driver = webdriver.Chrome(service=Service(chromedriver_binary), options=opt)
    else:
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
        except Exception as e:
            # Fallback when webdriver-manager cache has permissions/issues.
            print(f"[warn] ChromeDriverManager falhou ({e}); tentando chromedriver do PATH.")
            driver = webdriver.Chrome(options=opt)

    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
    except Exception:
        pass

    driver.set_page_load_timeout(120)
    return driver


def _debug_dump(driver, base_name):
    if not DEBUG_LOGIN:
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    png = ARTIFACTS_DIR / f"{base_name}_{stamp}.png"
    html = ARTIFACTS_DIR / f"{base_name}_{stamp}.html"
    try:
        driver.save_screenshot(str(png))
        with open(html, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"[warn] Dump de debug salvo em {png} / {html}")
    except Exception:
        pass


def _find_first_visible(driver, selectors, timeout_total=12):
    if not selectors:
        return None
    end = time.time() + timeout_total
    while time.time() < end:
        for how, sel in selectors:
            try:
                for elem in driver.find_elements(how, sel):
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
            except Exception:
                continue
        time.sleep(0.25)
    return None


def _safe_click(driver, elem):
    if not elem:
        return False
    try:
        elem.click()
        return True
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].click();", elem)
        return True
    except Exception:
        return False


def _read_page_flags(driver):
    script = """
        const body = document.body || {};
        return {
            bodyClass: body.className || '',
            hasLoginField: !!document.querySelector(
                '#field_email, input[name="st.email"], #field_password, input[name="st.password"]'
            ),
            hasAnonLogin: !!document.querySelector(
                '.feed-anonym-login, auth-login-banner, a[data-module="AuthLoginPopup"], .auth_login_banner_button'
            ),
            hasToolbarUser: !!document.querySelector(
                '#hook_Block_ToolbarUserBlock, .toolbar_ucard, .toolbar_user'
            ),
            hasLogout: !!document.querySelector(
                'a[href*="st.cmd=logoff"], a[data-l*="logout"], a[data-l*="logoff"]'
            ),
        };
    """
    try:
        return driver.execute_script(script) or {}
    except Exception:
        return {}


def is_logged_in(driver) -> bool:
    try:
        flags = _read_page_flags(driver)
        page = (driver.page_source or "").lower()
        if '"isloginin":true' in page or '"isloggedin":true' in page:
            return True
        if flags.get("hasToolbarUser") or flags.get("hasLogout"):
            return True
        if '"isloginin":false' in page and "auth-login-popup" in page:
            return False
        if flags.get("hasLoginField") or flags.get("hasAnonLogin"):
            return False
        if "anonym" in (flags.get("bodyClass") or "").lower():
            return False
        return True
    except Exception:
        return False


def detect_login_block_reason(driver):
    page = (driver.page_source or "").lower()
    if any(x in page for x in ["captcha", "field_code", "i'm not a robot", "i am not a robot"]):
        return "captcha"
    if any(x in page for x in ["profile verification", "enter code", "verification code", "two-factor", "2fa", "sms"]):
        return "verification"
    if any(x in page for x in ["wrong password", "incorrect password", "invalid password", "invalid login"]):
        return "credentials"
    if any(x in page for x in ["too many attempts", "temporarily blocked", "try again later"]):
        return "rate_limit"
    return ""


def load_cookies(driver, cookies_file):
    path = Path(cookies_file)
    if not path.exists():
        return False

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return False
    except Exception as e:
        print(f"[warn] Nao foi possivel ler cookies ({path}): {e}")
        return False

    try:
        driver.get("https://ok.ru/")
    except TimeoutException:
        print("[warn] Timeout ao abrir OK.ru para carregar cookies; seguindo.")

    loaded = 0
    allowed = {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        cookie = {k: v for k, v in entry.items() if k in allowed and v is not None}
        if "expiry" in cookie:
            try:
                cookie["expiry"] = int(cookie["expiry"])
            except Exception:
                cookie.pop("expiry", None)

        try:
            driver.add_cookie(cookie)
            loaded += 1
            continue
        except Exception:
            cookie.pop("sameSite", None)
        try:
            driver.add_cookie(cookie)
            loaded += 1
        except Exception:
            continue

    if loaded == 0:
        return False

    print(f"[info] {loaded} cookies carregados de {path}.")
    try:
        driver.get("https://ok.ru/")
    except TimeoutException:
        print("[warn] Timeout ao recarregar OK.ru apos cookies; seguindo.")
    time.sleep(2)
    return True


def save_cookies(driver, cookies_file):
    path = Path(cookies_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(driver.get_cookies(), indent=2), encoding="utf-8")
        print(f"[info] Cookies salvos em {path}.")
    except Exception as e:
        print(f"[warn] Nao foi possivel salvar cookies em {path}: {e}")


def wait_until_login_resolved(driver, timeout_total=35):
    end = time.time() + timeout_total
    while time.time() < end:
        if is_logged_in(driver):
            return "ok"
        reason = detect_login_block_reason(driver)
        if reason:
            return reason
        time.sleep(1)
    return "timeout"


def wait_manual_login(driver, timeout_total=180):
    end = time.time() + max(30, timeout_total)
    while time.time() < end:
        if is_logged_in(driver):
            return True
        time.sleep(2)
    return False


def login(driver, login_url=None):
    print("[info] Login")
    target_url = login_url or "https://ok.ru/"
    try:
        try:
            driver.get(target_url)
        except TimeoutException:
            print("[warn] Timeout no carregamento da pagina alvo; seguindo.")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        if is_logged_in(driver):
            print("[info] Sessao ja autenticada.")
            save_cookies(driver, COOKIES_FILE)
            return

        if load_cookies(driver, COOKIES_FILE):
            try:
                driver.get(target_url)
            except TimeoutException:
                print("[warn] Timeout ao recarregar alvo apos cookies; seguindo.")
            time.sleep(2)
            if is_logged_in(driver):
                print("[info] Sessao restaurada por cookies.")
                return
            print("[warn] Cookies expirados/invalidos; tentando login com credenciais.")

        if not EMAIL or not PASSWORD:
            raise RuntimeError("Defina OKRU_EMAIL e OKRU_PASSWORD no .env para autenticar.")

        try:
            driver.get(LOGIN_PAGE)
        except TimeoutException:
            print("[warn] Timeout ao abrir login page; seguindo.")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        email_selectors = [
            (By.ID, "field_email"),
            (By.CSS_SELECTOR, "input[name='st.email']"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='tel']"),
        ]
        pwd_selectors = [
            (By.ID, "field_password"),
            (By.CSS_SELECTOR, "input[name='st.password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
        ]
        submit_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "button.button-pro"),
            (By.CSS_SELECTOR, ".auth_login_banner_button"),
        ]

        email_input = _find_first_visible(driver, email_selectors, timeout_total=20)
        if not email_input:
            _debug_dump(driver, "okru_login_email_not_found")
            raise RuntimeError("Campo de email nao encontrado.")
        email_input.clear()
        email_input.send_keys(EMAIL)

        pwd_input = _find_first_visible(driver, pwd_selectors, timeout_total=8)
        if not pwd_input:
            email_input.send_keys(Keys.ENTER)
            pwd_input = _find_first_visible(driver, pwd_selectors, timeout_total=12)
        if not pwd_input:
            _debug_dump(driver, "okru_login_password_not_found")
            raise RuntimeError("Campo de senha nao encontrado.")
        pwd_input.clear()
        pwd_input.send_keys(PASSWORD)

        submit_btn = _find_first_visible(driver, submit_selectors, timeout_total=8)
        if not _safe_click(driver, submit_btn):
            pwd_input.send_keys(Keys.ENTER)

        status = wait_until_login_resolved(driver, timeout_total=35)
        if status == "ok":
            print("[info] Login OK")
            save_cookies(driver, COOKIES_FILE)
        elif status in {"captcha", "verification"}:
            _debug_dump(driver, "okru_login_challenge")
            if HEADLESS and not MANUAL_LOGIN:
                raise RuntimeError(
                    "OK.ru exigiu verificacao adicional. Rode com OKRU_HEADLESS=False "
                    "e OKRU_MANUAL_LOGIN=1 para concluir manualmente e salvar cookies."
                )
            print("[warn] Verificacao adicional detectada. Complete o login manualmente no navegador.")
            if not wait_manual_login(driver, timeout_total=MANUAL_LOGIN_WAIT_SEC):
                raise RuntimeError("Tempo esgotado aguardando login manual.")
            print("[info] Login manual concluido.")
            save_cookies(driver, COOKIES_FILE)
        elif status == "credentials":
            _debug_dump(driver, "okru_login_credentials")
            raise RuntimeError("Credenciais rejeitadas pelo OK.ru.")
        elif status == "rate_limit":
            _debug_dump(driver, "okru_login_ratelimit")
            raise RuntimeError("OK.ru bloqueou temporariamente novas tentativas de login.")
        else:
            _debug_dump(driver, "okru_login_timeout")
            raise RuntimeError("Nao foi possivel confirmar login; sessao continua anonima.")

        if login_url:
            try:
                driver.get(login_url)
            except TimeoutException:
                print("[warn] Timeout ao voltar para perfil alvo; seguindo.")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception as e:
        raise RuntimeError(f"[erro] Falha no login: {e}")


def is_404(driver) -> bool:
    return bool(driver.find_elements(By.CSS_SELECTOR, "h1.p404_t"))


def page_has_videos(driver) -> bool:
    return driver.execute_script("return document.querySelectorAll('.video-card').length") > 0


def page_requires_auth(driver) -> bool:
    selectors = ".feed-anonym-login, auth-login-banner, a[data-module='AuthLoginPopup'], .auth_login_banner_button"
    try:
        return bool(driver.find_elements(By.CSS_SELECTOR, selectors))
    except Exception:
        return False


def mark_server_inactive(cursor, conn, server_id):
    try:
        if cursor and not cursor.closed:
            cursor.execute("UPDATE server SET active = 0 WHERE id = %s;", (server_id,))
            conn.commit()
            print(f"[warn] idserver={server_id} marcado como inactive=0 (404).")
        else:
            print(f"[warn] Cursor fechado; nao foi possivel marcar o idserver={server_id} como inativo.")
    except Exception as e:
        print(f"[erro] Erro ao tentar marcar server inativo: {e}")


def process_visible_videos(driver, idserver, seen_ids):
    raw = driver.execute_script("""
        return Array.from(document.querySelectorAll('.video-card'))
        .map(c => ({
            id       : c.getAttribute('data-id'),
            title    : c.querySelector('.video-card_n')?.innerText || '',
            duration : c.querySelector('.video-card_duration')?.innerText || '',
            thumb    : c.querySelector('img')?.src || ''
        }));
    """)
    novos, order_init = [], len(seen_ids) + 1
    for idx, vid in enumerate(raw, start=order_init):
        if vid["id"] and vid["id"] not in seen_ids:
            seen_ids.add(vid["id"])
            novos.append((
                vid["id"],
                vid["title"][:MAX_TXT].strip().title(),
                vid["duration"][:20].strip(),
                vid["thumb"][:MAX_TXT],
                idserver,
                idx,
                datetime.date.today()
            ))
    driver.execute_script("""
        let cards = document.querySelectorAll('.video-card');
        for (let i = 0; i < cards.length - 200; i++) cards[i].remove();
    """)
    return novos


def scroll_and_scrape(driver, perfil_url, idserver, cursor, conn):
    print(f"\n[info] Perfil {perfil_url} (idserver {idserver})")
    driver.get(perfil_url)
    time.sleep(3)

    if not is_logged_in(driver) and page_requires_auth(driver):
        raise RuntimeError("Sessao anonima detectada; perfil requer login.")

    if is_404(driver):
        ensure_connection()
        mark_server_inactive(cursor, conn, idserver)
        return 0

    for attempt in range(3):
        if page_has_videos(driver):
            break
        print("[warn] Reload porque nao encontrou videos")
        driver.refresh()
        time.sleep(3)
    if not page_has_videos(driver):
        print("[warn] Nenhum video; pulando perfil.")
        return 0

    seen_ids, total, page = set(), 0, 1
    for _ in range(150):
        for _ in range(10):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            try:
                btn = driver.find_element(By.CLASS_NAME, "js-show-more")
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
            except Exception:
                pass

        novos = process_visible_videos(driver, idserver, seen_ids)
        if not novos:
            print("[info] Sem novos videos; stop.")
            break

        try:
            ensure_connection()
            execute_batch(cursor, SQL_INSERT, novos, page_size=500)
            conn.commit()
        except DataError as e:
            if not conn.closed:
                conn.rollback()
            print(f"[warn] DataError bloco {page}: {e}")
            continue
        except psycopg2.OperationalError as e:
            print(f"[warn] Conexao perdida com o banco: {e}")
            return total

        total += len(novos)
        print(f"[info] Bloco {page}: +{len(novos)} (total {total})")
        page += 1
    return total


def main():
    global conn, cursor
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                s.server, s.id
            FROM server s
            LEFT JOIN (
                SELECT idserver, MAX(created_at) AS ultima_data 
                FROM filmes GROUP BY idserver
            ) f ON s.id = f.idserver
            WHERE s.active = 1 
              AND s.type = 'UPLOAD' 
              --AND (f.ultima_data < NOW() - INTERVAL '1 month' OR f.ultima_data IS NULL)
              AND s.id in (398,399,400,401,402,403)
            ORDER BY s.id;
        """)
        perfis = cursor.fetchall()

        if not perfis:
            print("[info] Nenhum perfil encontrado para processar.")
            return

        driver = start_driver()
        try:
            login(driver, perfis[0][0])
        except Exception as e:
            print(e)
            driver.quit()
            driver = start_driver()
            login(driver, perfis[0][0])

        total_global = 0
        for perfil_url, idserver in perfis:
            for tentativa in range(2):
                try:
                    ensure_connection()
                    if tentativa == 1:
                        print("[warn] Tentando novamente apos erro...")
                        driver.get(perfil_url)
                        time.sleep(3)

                    qtd = scroll_and_scrape(driver, perfil_url, idserver, cursor, conn)
                    print(f"[info] {qtd} videos processados para {perfil_url}")
                    total_global += qtd
                    break
                except Exception as e:
                    if conn and not conn.closed:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    print(f"[erro] Erro na tentativa {tentativa + 1} para perfil {perfil_url}: {e}")
                    if tentativa == 1:
                        print("[warn] Reiniciando driver...")
                        driver.quit()
                        driver = start_driver()
                        try:
                            login(driver, perfil_url)
                        except Exception as e:
                            print(f"[erro] Falha ao relogar apos erro: {e}")
                            continue
        driver.quit()
        print(f"\n[info] Terminado! Total geral: {total_global} videos.")
    finally:
        if cursor:
            cursor.close()
        if conn and not conn.closed:
            conn.close()


if __name__ == "__main__":
    main()
