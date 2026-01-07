import time
import datetime
import psycopg2
import os
import sys
import types
from dotenv import load_dotenv
from psycopg2.extras import execute_batch
from psycopg2 import DataError

# Compat: selenium-wire vendor mitmproxy still imports blinker._saferef, removed in blinker>=1.9.
try:
    import blinker._saferef  # type: ignore
except ModuleNotFoundError:
    sys.modules["blinker._saferef"] = types.ModuleType("blinker._saferef")

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


# CONFIG #
EMAIL = os.environ.get("OKRU_EMAIL")
PASSWORD = os.environ.get("OKRU_PASSWORD")
HEADLESS = env_bool("OKRU_HEADLESS", True)


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
    opt = Options()
    if HEADLESS:
        opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    driver.set_page_load_timeout(60)
    return driver


def login(driver, login_url=None):
    print("[info] Login")
    try:
        target_url = login_url or "https://ok.ru/"
        driver.get(target_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        if login_url:
            # Abre o modal de login a partir da pagina de videos do perfil.
            openers = [
                (By.CSS_SELECTOR, "#hook_Block_FriendAllVideoRBlock a"),
                (By.XPATH, "//*[@id='hook_Block_FriendAllVideoRBlock']//a[1]"),
            ]
            for how, sel in openers:
                try:
                    opener = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((how, sel)))
                    driver.execute_script("arguments[0].click();", opener)
                    break
                except Exception:
                    continue

        def first_visible(selectors, wait_time=12):
            for how, sel in selectors:
                try:
                    elem = WebDriverWait(driver, wait_time).until(EC.visibility_of_element_located((how, sel)))
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
                except Exception:
                    continue
            return None

        email_input = first_visible([
            (By.CSS_SELECTOR, "#hook_Block_AuthLoginAutoOpen input#field_email"),
            (By.XPATH, "//*[@id='hook_Block_AuthLoginAutoOpen']//input[contains(@id,'field_email')]"),
            (By.XPATH, "//auth-login-popup//input[contains(@id,'field_email')]"),
            (By.ID, "field_email"),
        ], wait_time=15)
        pwd_input = first_visible([
            (By.CSS_SELECTOR, "#hook_Block_AuthLoginAutoOpen input#field_password"),
            (By.XPATH, "//*[@id='hook_Block_AuthLoginAutoOpen']//input[contains(@id,'field_password')]"),
            (By.XPATH, "//auth-login-popup//input[contains(@id,'field_password')]"),
            (By.ID, "field_password"),
        ], wait_time=15)

        if not email_input or not pwd_input:
            raise RuntimeError("Campos de login nao encontrados (email/senha).")

        email_input.clear(); email_input.send_keys(EMAIL)
        pwd_input.clear(); pwd_input.send_keys(PASSWORD)

        selectors = [
            (By.XPATH, "//*[@id='hook_Block_AuthLoginAutoOpen']/auth-login-popup/div/div[2]/div/div[1]/div[2]/div/div[1]/div[1]/form/button"),
            (By.XPATH, "//*[@id='hook_Block_AuthLoginAutoOpen']//form//button[@type='submit']"),
            (By.XPATH, "//auth-login-popup//form//button[@type='submit']"),
            (By.CSS_SELECTOR, "auth-login-popup button[type='submit']"),
            (By.CSS_SELECTOR, "#hook_Block_AuthLoginAutoOpen button[type='submit']"),
            (By.CSS_SELECTOR, "vkid-form-adapter form button[type='submit']"),
            (By.XPATH, "//vkid-form-adapter//form//button[@type='submit']"),
            (By.XPATH, "//div[contains(@id,'tabpanel-login-')]//form//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit'].vkuButton_host"),
            (By.CSS_SELECTOR, "input.button-pro[type='submit']"),
            (By.CSS_SELECTOR, "button.button-pro[type='submit']"),
            (By.XPATH, "//input[@type='submit' and contains(@class,'button-pro')]"),
            (By.XPATH, "//button[@type='submit' and contains(@class,'button-pro')]"),
        ]
        btn = first_visible(selectors, wait_time=12)

        if not btn:
            # Fallback: primeiro submit visivel.
            for candidate in driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"):
                if candidate.is_displayed() and candidate.is_enabled():
                    btn = candidate
                    break

        if btn:
            driver.execute_script("arguments[0].click();", btn)
        else:
            pwd_input.send_keys(Keys.ENTER)

        # Nao bloquear no fechamento do popup; login segue em frente.
        time.sleep(3)
        print("[info] Login OK")
    except Exception as e:
        raise RuntimeError(f"[erro] Falha no login: {e}")


def is_404(driver) -> bool:
    return bool(driver.find_elements(By.CSS_SELECTOR, "h1.p404_t"))


def page_has_videos(driver) -> bool:
    return driver.execute_script("return document.querySelectorAll('.video-card').length") > 0


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
              AND s.id in (397)
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
