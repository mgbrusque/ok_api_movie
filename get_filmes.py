import time, datetime
import psycopg2
from psycopg2.extras import execute_batch
from psycopg2 import DataError
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ───── CONFIG ───── #
EMAIL   = "moitaum@gmail.com"
PASSWORD = "speaker1A"
HEADLESS = True

DB_CONFIG = {
    "host"    : "bq2dwmholieihd7cnpxx-postgresql.services.clever-cloud.com",
    "database": "bq2dwmholieihd7cnpxx",
    "user"    : "upi6tqi6dxccuuerpwjg",
    "password": "rz7SsSKNHuN43DmC14Wq",
    "port"    : "50013"
}
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
# ────────────────── #

conn = None
cursor = None

def ensure_connection():
    global conn, cursor
    if conn is None or conn.closed or cursor.closed:
        print("🔄 Recriando conexão com o banco...")
        conn = psycopg2.connect(**DB_CONFIG)
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

def login(driver):
    print("➡️ Login…")
    try:
        driver.get("https://ok.ru/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "field_email")))
        driver.find_element(By.ID, "field_email").send_keys(EMAIL)
        driver.find_element(By.ID, "field_password").send_keys(PASSWORD)
        btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='submit' and contains(@class,'button-pro')]")))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)
        if "anonymLogin" in driver.current_url:
            raise RuntimeError("❌ Login falhou.")
        print("✅ Login OK")
    except Exception as e:
        raise RuntimeError(f"❌ Falha no login: {e}")

def is_404(driver) -> bool:
    return bool(driver.find_elements(By.CSS_SELECTOR, "h1.p404_t"))

def page_has_videos(driver) -> bool:
    return driver.execute_script("return document.querySelectorAll('.video-card').length") > 0

def mark_server_inactive(cursor, conn, server_id):
    try:
        if cursor and not cursor.closed:
            cursor.execute("UPDATE server SET active = 0 WHERE id = %s;", (server_id,))
            conn.commit()
            print(f"🚫 idserver={server_id} marcado como inactive=0 (404).")
        else:
            print(f"⚠️ Cursor fechado — não foi possível marcar o idserver={server_id} como inativo.")
    except Exception as e:
        print(f"❌ Erro ao tentar marcar server inativo: {e}")

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
    print(f"\n➡️ Perfil {perfil_url}  (idserver {idserver})")
    driver.get(perfil_url)
    time.sleep(3)

    if is_404(driver):
        ensure_connection()
        mark_server_inactive(cursor, conn, idserver)
        return 0

    for attempt in range(3):
        if page_has_videos(driver):
            break
        print("🔄 Reload porque não encontrou vídeos…")
        driver.refresh(); time.sleep(3)
    if not page_has_videos(driver):
        print("⚠️  Nenhum vídeo — pulando perfil.")
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
            except:
                pass

        novos = process_visible_videos(driver, idserver, seen_ids)
        if not novos:
            print("🛑 Sem novos vídeos – stop.")
            break

        try:
            ensure_connection()
            execute_batch(cursor, SQL_INSERT, novos, page_size=500)
            conn.commit()
        except DataError as e:
            if not conn.closed:
                conn.rollback()
            print(f"⚠️  DataError bloco {page}: {e}")
            continue
        except psycopg2.OperationalError as e:
            print(f"⚠️  Conexão perdida com o banco: {e}")
            return total

        total += len(novos)
        print(f"📺 Bloco {page}: +{len(novos)}  (total {total})")
        page += 1
    return total

def main():
    global conn, cursor
    conn = psycopg2.connect(**DB_CONFIG)
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
              AND (f.ultima_data < NOW() - INTERVAL '1 month' OR f.ultima_data IS NULL)
            ORDER BY s.id;
        """)
        perfis = cursor.fetchall()

        driver = start_driver()
        try:
            login(driver)
        except Exception as e:
            print(e)
            driver.quit()
            driver = start_driver()
            login(driver)

        total_global = 0
        for perfil_url, idserver in perfis:
            for tentativa in range(2):
                try:
                    ensure_connection()
                    if tentativa == 1:
                        print("🔁 Tentando novamente após erro...")
                        driver.get(perfil_url)
                        time.sleep(3)

                    qtd = scroll_and_scrape(driver, perfil_url, idserver, cursor, conn)
                    print(f"✅ {qtd} vídeos processados para {perfil_url}")
                    total_global += qtd
                    break
                except Exception as e:
                    if conn and not conn.closed:
                        try: conn.rollback()
                        except: pass
                    print(f"❌ Erro na tentativa {tentativa + 1} para perfil {perfil_url}: {e}")
                    if tentativa == 1:
                        print("🔁 Reiniciando driver...")
                        driver.quit()
                        driver = start_driver()
                        try:
                            login(driver)
                        except Exception as e:
                            print(f"❌ Falha ao relogar após erro: {e}")
                            continue
        driver.quit()
        print(f"\n🎉 Terminado! Total geral: {total_global} vídeos.")
    finally:
        if cursor: cursor.close()
        if conn and not conn.closed: conn.close()

if __name__ == "__main__":
    main()
