import datetime
import html
import importlib.util
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from psycopg2 import InterfaceError, OperationalError

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"


MAX_TXT = 200
HTTP_TIMEOUT = 45
COOKIES_FILE = os.environ.get("OKRU_COOKIES_FILE", str(BASE_DIR / "okru_cookies.json"))
USER_AGENT = os.environ.get(
    "OKRU_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
)
ENABLE_EXPERIMENTAL_PAGINATION = os.environ.get("OKRU_REQUESTS_PAGINATION", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_EXTRA_PAGES = int(os.environ.get("OKRU_REQUESTS_MAX_EXTRA_PAGES", "500"))
MAX_SERVERS = int(os.environ.get("OKRU_REQUESTS_MAX_SERVERS", "0"))
DRY_RUN = os.environ.get("OKRU_REQUESTS_DRY_RUN", "0").strip().lower() in {"1", "true", "yes", "on"}
SERVER_IDS_ENV = (os.environ.get("OKRU_SERVER_IDS") or "").strip()
LOADER_CMD = "FriendVideoMoviesRedesignRBlock"
DEFAULT_LOADER_ID = "FriendVideoMoviesRedesignRBlockLoader"
DB_WRITE_CHUNK = int(os.environ.get("OKRU_DB_WRITE_CHUNK", "500"))
DB_WRITE_RETRIES = int(os.environ.get("OKRU_DB_WRITE_RETRIES", "3"))
DB_CONNECT_RETRIES = int(os.environ.get("OKRU_DB_CONNECT_RETRIES", "8"))
DB_FLUSH_EVERY = int(os.environ.get("OKRU_DB_FLUSH_EVERY", "1000"))
HTTP_RETRIES = int(os.environ.get("OKRU_HTTP_RETRIES", "4"))
IGNORE_DAYS = int(os.environ.get("OKRU_IGNORE_DAYS", "0"))
RESUME_FROM_IDSERVER = int(os.environ.get("OKRU_RESUME_FROM_IDSERVER", "0"))
MAX_WORKERS = int(os.environ.get("OKRU_MAX_WORKERS", "1"))
LOG_ENABLED = os.environ.get("OKRU_LOG", "1").strip().lower() in {"1", "true", "yes", "on"}
RUN_LOG_FILE = ARTIFACTS_DIR / "requests_run.log"
BOOL_TRUE = {"1", "true", "yes", "on"}
AUTO_COOKIE_LOGIN = os.environ.get("OKRU_REQUESTS_AUTO_COOKIE_LOGIN", "1").strip().lower() in BOOL_TRUE
AUTO_COOKIE_LOGIN_FORCE_HEADLESS = (
    os.environ.get("OKRU_REQUESTS_AUTO_COOKIE_LOGIN_FORCE_HEADLESS", "1").strip().lower() in BOOL_TRUE
)
AUTO_COOKIE_LOGIN_ALLOW_MANUAL = (
    os.environ.get("OKRU_REQUESTS_AUTO_COOKIE_LOGIN_ALLOW_MANUAL", "0").strip().lower() in BOOL_TRUE
)

SQL_INSERT = """
    INSERT INTO filmes (id, nome, tempo, imagem, idserver, ordernum, created_at)
    VALUES %s
    ON CONFLICT (id) DO UPDATE SET
        nome       = EXCLUDED.nome,
        tempo      = EXCLUDED.tempo,
        imagem     = EXCLUDED.imagem,
        idserver   = EXCLUDED.idserver,
        ordernum   = EXCLUDED.ordernum,
        created_at = EXCLUDED.created_at
"""


_OKRU_LOGIN_MODULE = None


def _load_okru_login_module():
    global _OKRU_LOGIN_MODULE
    if _OKRU_LOGIN_MODULE is not None:
        return _OKRU_LOGIN_MODULE

    module_path = BASE_DIR / "get_filmes.py"
    spec = importlib.util.spec_from_file_location("okru_cookie_login_helper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar modulo de login em {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    if not hasattr(module, "start_driver") or not hasattr(module, "login"):
        raise RuntimeError("Modulo de login nao expoe start_driver/login.")

    _OKRU_LOGIN_MODULE = module
    return module


def _check_session_authenticated(session: requests.Session, probe_profile_url: str) -> bool:
    try:
        resp = _fetch_profile_page(session, probe_profile_url)
    except requests.RequestException as exc:
        print(f"[warn] Nao foi possivel validar sessao por HTTP ({exc}); seguindo com cookies atuais.")
        return True

    page_html = resp.text or ""
    if _is_auth_required(page_html):
        return False
    return True


def _refresh_cookies_automatically(profile_url: str) -> bool:
    if not AUTO_COOKIE_LOGIN:
        return False

    old_headless = os.environ.get("OKRU_HEADLESS")
    old_manual_login = os.environ.get("OKRU_MANUAL_LOGIN")
    old_cookies_file = os.environ.get("OKRU_COOKIES_FILE")

    if AUTO_COOKIE_LOGIN_FORCE_HEADLESS:
        os.environ["OKRU_HEADLESS"] = "1"
    if not AUTO_COOKIE_LOGIN_ALLOW_MANUAL:
        os.environ["OKRU_MANUAL_LOGIN"] = "0"
    os.environ["OKRU_COOKIES_FILE"] = COOKIES_FILE

    driver = None
    try:
        login_mod = _load_okru_login_module()
        print("[info] Sessao anonima detectada; tentando renovar cookies automaticamente...")
        driver = login_mod.start_driver()
        login_mod.login(driver, profile_url)
        print("[info] Cookies renovados com sucesso.")
        return True
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[warn] Falha ao renovar cookies automaticamente: {exc}")
        return False
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # pylint: disable=broad-except
                pass

        if old_headless is None:
            os.environ.pop("OKRU_HEADLESS", None)
        else:
            os.environ["OKRU_HEADLESS"] = old_headless

        if old_manual_login is None:
            os.environ.pop("OKRU_MANUAL_LOGIN", None)
        else:
            os.environ["OKRU_MANUAL_LOGIN"] = old_manual_login

        if old_cookies_file is None:
            os.environ.pop("OKRU_COOKIES_FILE", None)
        else:
            os.environ["OKRU_COOKIES_FILE"] = old_cookies_file


def _ensure_authenticated_session(session: requests.Session, probe_profile_url: str) -> bool:
    if _check_session_authenticated(session, probe_profile_url):
        return True

    if not AUTO_COOKIE_LOGIN:
        return False

    if not _refresh_cookies_automatically(probe_profile_url):
        return False

    session.cookies.clear()
    _load_cookies(session, COOKIES_FILE, verbose=True)
    return _check_session_authenticated(session, probe_profile_url)


def get_conn():
    retries = max(1, DB_CONNECT_RETRIES)
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return psycopg2.connect(
                host=os.environ.get("DB_HOST"),
                database=os.environ.get("DB_DATABASE"),
                user=os.environ.get("DB_USER"),
                password=os.environ.get("DB_PASSWORD"),
                port=os.environ.get("DB_PORT"),
                connect_timeout=20,
                application_name="okru_requests_scraper",
            )
        except OperationalError as exc:
            last_exc = exc
            if attempt >= retries:
                break
            wait_sec = min(10, attempt * 2)
            print(f"[warn] Falha conectando ao banco (tentativa {attempt}/{retries}): {exc}")
            print(f"[info] Aguardando {wait_sec}s para tentar reconectar...")
            time.sleep(wait_sec)
    raise last_exc  # type: ignore[misc]


def _close_db(conn, cursor):
    try:
        if cursor and not cursor.closed:
            cursor.close()
    except Exception:  # pylint: disable=broad-except
        pass
    try:
        if conn and not conn.closed:
            conn.close()
    except Exception:  # pylint: disable=broad-except
        pass


def _ensure_db(conn, cursor):
    if conn is None or cursor is None:
        conn = get_conn()
        cursor = conn.cursor()
        return conn, cursor

    if conn.closed or cursor.closed:
        _close_db(conn, cursor)
        conn = get_conn()
        cursor = conn.cursor()
        return conn, cursor

    try:
        cursor.execute("SELECT 1")
    except Exception:  # pylint: disable=broad-except
        _close_db(conn, cursor)
        conn = get_conn()
        cursor = conn.cursor()
    return conn, cursor


def _clean_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_attr(tag: str, attr: str) -> str:
    if not tag:
        return ""
    m = re.search(rf'\b{re.escape(attr)}="([^"]*)"', tag, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def _normalize_thumb_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    return url


def _normalize_profile_video_url(raw_url: str) -> str:
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return raw_url

    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    elif not raw_url.lower().startswith(("http://", "https://")):
        raw_url = "https://ok.ru/" + raw_url.lstrip("/")

    parsed = urlparse(raw_url)
    path = (parsed.path or "").rstrip("/")
    if "/video/" in path:
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    m = re.search(r"/profile/\d+", path)
    if m:
        return f"{parsed.scheme}://{parsed.netloc}{m.group(0)}/video/uploaded"

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _parse_friend_id(url: str) -> Optional[str]:
    m = re.search(r"/profile/(\d+)", url or "")
    return m.group(1) if m else None


def _load_cookies(session: requests.Session, cookies_file: str, verbose: bool = True) -> bool:
    path = Path(cookies_file)
    if not path.exists():
        if verbose:
            print(f"[warn] Arquivo de cookies nao encontrado: {path}")
        return False

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        if verbose:
            print(f"[warn] Falha lendo cookies em {path}: {exc}")
        return False

    if not isinstance(raw, list):
        if verbose:
            print(f"[warn] Formato invalido de cookies em {path}")
        return False

    loaded = 0
    for entry in raw:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name")
        value = entry.get("value")
        domain = entry.get("domain")
        if not (name and value and domain):
            continue

        cookie = requests.cookies.create_cookie(
            name=name,
            value=value,
            domain=domain,
            path=entry.get("path") or "/",
            secure=bool(entry.get("secure", False)),
            expires=entry.get("expiry"),
        )
        session.cookies.set_cookie(cookie)
        loaded += 1

    if verbose:
        print(f"[info] {loaded} cookies carregados de {path}.")
    return loaded > 0


def _extract_page_ctx(html_text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    m = re.search(r"var\s+pageCtx=\{.*?\};", html_text, re.S)
    if not m:
        return out
    chunk = m.group(0)

    gwt = re.search(r'gwtHash:"([^"]+)"', chunk)
    if gwt:
        out["gwtHash"] = gwt.group(1)

    state = re.search(r'state:"([^"]+)"', chunk)
    if state:
        out["state"] = html.unescape(state.group(1))

    return out


def _extract_loader_attrs(html_text: str) -> Dict[str, str]:
    m = re.search(
        r'<[^>]*id="hook_Loader_FriendVideoMoviesRedesignRBlockLoader"[^>]*>',
        html_text,
        re.S,
    )
    if not m:
        return {}

    tag = m.group(0)
    attrs: Dict[str, str] = {}
    for key, value in re.findall(r'([a-zA-Z0-9_\-:]+)="([^"]*)"', tag):
        attrs[key] = html.unescape(value)
    return attrs


def _extract_body_attr(html_text: str, attr_name: str) -> str:
    m = re.search(r"<html[^>]*>|<body[^>]*>", html_text, re.I)
    if not m:
        return ""
    tag = m.group(0)
    p = re.search(rf'{re.escape(attr_name)}="([^"]*)"', tag, re.I)
    return html.unescape(p.group(1)) if p else ""


def _extract_tkn(html_text: str) -> str:
    m = re.search(r"OK\.tkn\.set\('([^']+)'\)", html_text)
    return m.group(1) if m else ""


def _parse_has_more(last_elem: str) -> Optional[bool]:
    if not last_elem:
        return None
    try:
        data = json.loads(last_elem)
    except Exception:  # pylint: disable=broad-except
        return None
    marker = data.get("uploadedMovieMarker") or {}
    has_more = marker.get("hasMore")
    if isinstance(has_more, bool):
        return has_more
    return None


def _build_loader_url(profile_url: str, gwt_hash: str, state_params: Dict[str, str]) -> str:
    query = {"cmd": LOADER_CMD, "gwt.requested": gwt_hash, **state_params}
    return f"{profile_url}?{urlencode(query)}&"


def _is_auth_required(html_text: str) -> bool:
    page = html_text.lower()
    checks = [
        "feed-anonym-login",
        "auth_login_banner_button",
        "data-module=\"authloginpopup\"",
        "id=\"field_email\"",
        "id=\"field_password\"",
        "data-initial-state-id=\"anonym",
    ]
    return any(key in page for key in checks)


def _is_404(html_text: str) -> bool:
    page = html_text.lower()
    return "class=\"p404_t\"" in page or "error-404" in page


def _extract_videos_from_html(html_text: str) -> List[Dict[str, str]]:
    cards = list(
        re.finditer(
            r'<div[^>]+class="[^"]*\bvideo-card\b[^"]*"[^>]*data-id="([^"]+)"[^>]*>',
            html_text,
            re.I,
        )
    )
    if not cards:
        return []

    items: List[Dict[str, str]] = []
    seen = set()
    for idx, match in enumerate(cards):
        video_id = (match.group(1) or "").strip()
        if not video_id or video_id in seen:
            continue

        start = match.start()
        end = cards[idx + 1].start() if idx + 1 < len(cards) else min(len(html_text), start + 9000)
        chunk = html_text[start:end]

        title = ""
        m_title = re.search(r'class="video-card_n[^"]*"[^>]*title="([^"]*)"', chunk, re.I)
        if m_title:
            title = _clean_text(m_title.group(1))
        if not title:
            m_title = re.search(r'class="video-card_n[^"]*"[^>]*>(.*?)</a>', chunk, re.I | re.S)
            if m_title:
                title = _clean_text(m_title.group(1))
        if not title:
            m_title = re.search(r'class="video-card_img"[^>]*alt="([^"]*)"', chunk, re.I)
            if m_title:
                title = _clean_text(m_title.group(1))

        duration = ""
        m_duration = re.search(r'class="video-card_duration">([^<]*)<', chunk, re.I)
        if m_duration:
            duration = _clean_text(m_duration.group(1))

        thumb = ""
        img_tag = ""
        m_img = re.search(r"<img[^>]*class=\"[^\"]*\bvideo-card_img\b[^\"]*\"[^>]*>", chunk, re.I)
        if m_img:
            img_tag = m_img.group(0)
        else:
            m_img = re.search(r"<img[^>]*>", chunk, re.I)
            if m_img:
                img_tag = m_img.group(0)

        if img_tag:
            thumb = _extract_attr(img_tag, "src")
            if not thumb:
                thumb = _extract_attr(img_tag, "data-src")
            if not thumb:
                thumb = _extract_attr(img_tag, "data-lazy-src")
            if not thumb:
                srcset = _extract_attr(img_tag, "srcset")
                if srcset:
                    thumb = srcset.split(",")[0].strip().split(" ")[0].strip()
            thumb = _normalize_thumb_url(thumb)

        items.append(
            {
                "id": video_id,
                "title": title,
                "duration": duration,
                "thumb": thumb,
            }
        )
        seen.add(video_id)

    return items


def _build_state_params(state_str: str, profile_url: str) -> Dict[str, str]:
    params = dict(parse_qsl(state_str or "", keep_blank_values=True))
    friend_id = params.get("st.friendId") or _parse_friend_id(profile_url)
    if "st.cmd" not in params:
        params["st.cmd"] = "userFriendVideoNew"
    if "st.fetchType" not in params:
        params["st.fetchType"] = "UPLOADED"
    if friend_id:
        params["st.friendId"] = friend_id
    return params


def _post_loader(
    session: requests.Session,
    loader_url: str,
    referer_url: str,
    payload: Dict[str, str],
    token_headers: Dict[str, str],
) -> requests.Response:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://ok.ru",
        "Referer": referer_url,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    headers.update(token_headers)

    retries = max(1, HTTP_RETRIES)
    last_exc = None
    resp = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.post(loader_url, data=payload, headers=headers, timeout=HTTP_TIMEOUT)
            if resp.status_code >= 500:
                if attempt < retries:
                    wait_sec = min(5, attempt)
                    print(
                        f"[warn] HTTP {resp.status_code} no load-more; "
                        f"retry {attempt}/{retries} em {wait_sec}s"
                    )
                    time.sleep(wait_sec)
                    continue
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            wait_sec = min(5, attempt)
            print(f"[warn] Erro de rede no load-more; retry {attempt}/{retries} em {wait_sec}s: {exc}")
            time.sleep(wait_sec)

    if resp is None:
        raise last_exc if last_exc else RuntimeError("Falha inesperada no load-more")

    # Keep tokens rolling as the site rotates anti-csrf headers.
    if resp.headers.get("TKN"):
        token_headers["TKN"] = resp.headers.get("TKN", "")
    if resp.headers.get("tkn"):
        token_headers["TKN"] = resp.headers.get("tkn", "")
    if resp.headers.get("X-Client-Flags"):
        token_headers["X-Client-Flags"] = resp.headers.get("X-Client-Flags", "")
    return resp


def _try_collect_extra_pages(
    session: requests.Session,
    profile_url: str,
    first_html: str,
    first_resp_headers: Dict[str, str],
    on_delta=None,
    allow_refresh_retry: bool = True,
) -> List[Dict[str, str]]:
    if not ENABLE_EXPERIMENTAL_PAGINATION or MAX_EXTRA_PAGES <= 0:
        return []

    page_ctx = _extract_page_ctx(first_html)
    loader = _extract_loader_attrs(first_html)
    gwt_hash = page_ctx.get("gwtHash", "")
    state_params = _build_state_params(page_ctx.get("state", ""), profile_url)
    last_elem = loader.get("data-last-element", "")
    loader_id = loader.get("id", DEFAULT_LOADER_ID) or DEFAULT_LOADER_ID
    initial_has_more = _parse_has_more(last_elem)

    if not gwt_hash or not last_elem:
        return []

    loader_url = _build_loader_url(profile_url, gwt_hash, state_params)

    token_headers: Dict[str, str] = {}
    token_headers["STRD"] = "true"
    token_headers["STRV"] = "V3"

    tkn = _extract_tkn(first_html)
    if tkn:
        token_headers["TKN"] = tkn
    elif first_resp_headers.get("TKN"):
        token_headers["TKN"] = first_resp_headers.get("TKN", "")

    client_flags = _extract_body_attr(first_html, "data-client-state")
    if client_flags:
        token_headers["X-Client-Flags"] = client_flags
    elif first_resp_headers.get("X-Client-Flags"):
        token_headers["X-Client-Flags"] = first_resp_headers.get("X-Client-Flags", "")

    stat_id = _extract_body_attr(first_html, "data-stat-id")
    if stat_id:
        token_headers["X-Stat-Id"] = stat_id

    collected: List[Dict[str, str]] = []
    seen_ids = set()
    for video in _extract_videos_from_html(first_html):
        seen_ids.add(video["id"])

    empty_rounds = 0
    stopped_by_limit = True
    for page_idx in range(1, MAX_EXTRA_PAGES + 1):
        payload = {
            "fetch": "false",
            "st.lastelem": last_elem,
            "st.loaderid": loader_id,
        }
        try:
            resp = _post_loader(session, loader_url, profile_url, payload, token_headers)
        except requests.RequestException as exc:
            print(f"[warn] Erro no load-more ({profile_url}): {exc}")
            break

        body = resp.text or ""
        maybe_new = _extract_videos_from_html(body)
        delta = [v for v in maybe_new if v["id"] not in seen_ids]

        if delta:
            for v in delta:
                seen_ids.add(v["id"])
            collected.extend(delta)
            if on_delta:
                on_delta(delta, page_idx)
            empty_rounds = 0
        else:
            empty_rounds += 1

        # marker for next page comes in header 'lastelem'
        if resp.headers.get("lastelem"):
            last_elem = resp.headers.get("lastelem", last_elem)
        elif resp.headers.get("Lastelem"):
            last_elem = resp.headers.get("Lastelem", last_elem)

        has_more = _parse_has_more(last_elem)
        if page_idx % 10 == 0 or len(delta) != 20:
            print(
                f"[info] Paginacao: page={page_idx} +{len(delta)} "
                f"(total_extra={len(collected)}, has_more={has_more})"
            )

        # Defensive retry: sometimes OK returns an empty first delta even when
        # the first page marker advertises more content.
        if (
            allow_refresh_retry
            and page_idx == 1
            and not delta
            and initial_has_more is True
            and has_more is False
        ):
            print("[warn] Paginacao inconsistente na primeira pagina; renovando contexto e tentando novamente.")
            try:
                fresh_resp = _fetch_profile_page(session, profile_url)
            except requests.RequestException as exc:
                print(f"[warn] Falha ao renovar contexto de paginacao ({profile_url}): {exc}")
            else:
                fresh_html = fresh_resp.text or ""
                if not _is_auth_required(fresh_html) and fresh_resp.status_code != 404 and not _is_404(fresh_html):
                    return _try_collect_extra_pages(
                        session,
                        profile_url,
                        fresh_html,
                        dict(fresh_resp.headers),
                        on_delta=on_delta,
                        allow_refresh_retry=False,
                    )

        if has_more is False:
            stopped_by_limit = False
            break
        if empty_rounds >= 2:
            stopped_by_limit = False
            if has_more is True:
                print(
                    "[warn] Paginacao interrompida por respostas vazias consecutivas "
                    f"(page={page_idx}, total_extra={len(collected)})."
                )
            break

    if stopped_by_limit and MAX_EXTRA_PAGES > 0:
        print(
            "[warn] Limite de paginacao atingido: "
            f"MAX_EXTRA_PAGES={MAX_EXTRA_PAGES}, total_extra={len(collected)}. "
            "Aumente OKRU_REQUESTS_MAX_EXTRA_PAGES para coletar mais."
        )

    return collected


def _mark_server_inactive(cursor, conn, server_id: int):
    cursor.execute("UPDATE server SET active = 0 WHERE id = %s;", (server_id,))
    conn.commit()
    print(f"[warn] idserver={server_id} marcado como active=0 (404).")


def _write_rows_with_retry(rows, conn, cursor):
    if not rows:
        return conn, cursor, 0

    chunk_size = max(1, DB_WRITE_CHUNK)
    retries = max(1, DB_WRITE_RETRIES)
    total_written = 0

    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        done = False

        for attempt in range(1, retries + 1):
            try:
                conn, cursor = _ensure_db(conn, cursor)
                execute_values(cursor, SQL_INSERT, chunk, page_size=len(chunk))
                conn.commit()
                total_written += len(chunk)
                done = True
                break
            except (OperationalError, InterfaceError) as exc:
                print(
                    f"[warn] Conexao com banco caiu ao gravar lote "
                    f"({start + 1}-{start + len(chunk)}): {exc}"
                )
                _close_db(conn, cursor)
                conn, cursor = None, None
                time.sleep(min(5, attempt))
            except Exception:
                if conn and not conn.closed:
                    try:
                        conn.rollback()
                    except Exception:  # pylint: disable=broad-except
                        pass
                raise

        if not done:
            raise RuntimeError(
                f"Falha persistente ao gravar lote ({start + 1}-{start + len(chunk)}) "
                f"apos {retries} tentativas."
            )

    return conn, cursor, total_written


def _backup_rows(rows, idserver: int) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ARTIFACTS_DIR / f"pending_filmes_idserver_{idserver}_{stamp}.json"
    data = [
        {
            "id": row[0],
            "nome": row[1],
            "tempo": row[2],
            "imagem": row[3],
            "idserver": row[4],
            "ordernum": row[5],
            "created_at": str(row[6]),
        }
        for row in rows
    ]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _write_run_log(
    total_profiles: int,
    total_found: int,
    total_saved: int,
    total_errors: int,
    elapsed_sec: float,
) -> None:
    if not LOG_ENABLED:
        return

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    status = "ERRO" if total_errors > 0 else "OK"
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{stamp} | status={status} | tempo={elapsed_sec:.1f}s | "
        f"servers={total_profiles} | filmes={total_found} | "
        f"gravados={total_saved} | erros={total_errors}\n"
    )
    try:
        with RUN_LOG_FILE.open("a", encoding="utf-8") as fp:
            fp.write(line)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[warn] Falha ao gravar log em {RUN_LOG_FILE}: {exc}")


def _load_servers(cursor) -> List[Tuple[str, int]]:
    ids: List[int] = []
    if SERVER_IDS_ENV:
        for part in SERVER_IDS_ENV.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))

    if ids:
        cursor.execute(
            """
            SELECT s.server, s.id
            FROM server s
            LEFT JOIN (
                SELECT idserver, MAX(created_at) AS ultima_data
                FROM filmes
                GROUP BY idserver
            ) f ON f.idserver = s.id
            WHERE s.active = 1
              AND s.type = 'UPLOAD'
              AND s.id = ANY(%s)
              AND s.id >= %s
              AND (
                    %s <= 0
                    OR f.ultima_data IS NULL
                    OR f.ultima_data < CURRENT_DATE - (%s * INTERVAL '1 day')
              )
            ORDER BY s.id;
            """,
            (ids, RESUME_FROM_IDSERVER, IGNORE_DAYS, IGNORE_DAYS),
        )
    else:
        cursor.execute(
            """
            SELECT s.server, s.id
            FROM server s
            LEFT JOIN (
                SELECT idserver, MAX(created_at) AS ultima_data
                FROM filmes
                GROUP BY idserver
            ) f ON f.idserver = s.id
            WHERE s.active = 1
              AND s.type = 'UPLOAD'
              AND s.id >= %s
              AND (
                    %s <= 0
                    OR f.ultima_data IS NULL
                    OR f.ultima_data < CURRENT_DATE - (%s * INTERVAL '1 day')
              )
            ORDER BY s.id;
            """,
            (RESUME_FROM_IDSERVER, IGNORE_DAYS, IGNORE_DAYS),
        )

    rows = cursor.fetchall()
    if MAX_SERVERS > 0:
        rows = rows[:MAX_SERVERS]
    return rows


def _to_rows(videos: List[Dict[str, str]], idserver: int, offset: int = 0):
    today = datetime.date.today()
    rows = []
    for idx, item in enumerate(videos, start=1 + offset):
        rows.append(
            (
                item["id"],
                (item.get("title") or "")[:MAX_TXT].strip().title(),
                (item.get("duration") or "")[:20].strip(),
                (item.get("thumb") or "")[:MAX_TXT],
                idserver,
                idx,
                today,
            )
        )
    return rows


def _fetch_profile_page(session: requests.Session, profile_url: str) -> requests.Response:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    retries = max(1, HTTP_RETRIES)
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(profile_url, headers=headers, timeout=HTTP_TIMEOUT)
            if resp.status_code >= 500 and attempt < retries:
                wait_sec = min(5, attempt)
                print(
                    f"[warn] HTTP {resp.status_code} ao abrir perfil; "
                    f"retry {attempt}/{retries} em {wait_sec}s"
                )
                time.sleep(wait_sec)
                continue
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            wait_sec = min(5, attempt)
            print(f"[warn] Erro HTTP ao abrir perfil; retry {attempt}/{retries} em {wait_sec}s: {exc}")
            time.sleep(wait_sec)
    raise last_exc  # type: ignore[misc]


def _process_profile_network(profile_url: str, idserver: int) -> Dict[str, object]:
    session = requests.Session()
    _load_cookies(session, COOKIES_FILE, verbose=False)
    result: Dict[str, object] = {
        "idserver": idserver,
        "profile_url": profile_url,
        "status": "error",
    }
    try:
        try:
            resp = _fetch_profile_page(session, profile_url)
        except requests.RequestException as exc:
            result["status"] = "http_error"
            result["error"] = str(exc)
            return result

        page_html = resp.text or ""
        if resp.status_code == 404 or _is_404(page_html):
            result["status"] = "not_found"
            return result

        if _is_auth_required(page_html):
            result["status"] = "auth_required"
            return result

        base_videos = _extract_videos_from_html(page_html)
        if not base_videos:
            result["status"] = "empty"
            return result

        extra_videos = _try_collect_extra_pages(session, profile_url, page_html, dict(resp.headers))
        base_ids = {x["id"] for x in base_videos}
        all_videos = base_videos + [v for v in extra_videos if v["id"] not in base_ids]

        result["status"] = "ok"
        result["base_count"] = len(base_videos)
        result["extra_count"] = len(extra_videos)
        result["videos"] = all_videos
        return result
    except Exception as exc:  # pylint: disable=broad-except
        result["status"] = "error"
        result["error"] = str(exc)
        return result
    finally:
        session.close()


def main():
    started = time.time()
    conn = None
    cursor = None
    session = requests.Session()
    _load_cookies(session, COOKIES_FILE)

    total_saved = 0
    total_found = 0
    total_profiles = 0
    total_errors = 0

    def register_error():
        nonlocal total_errors
        total_errors += 1

    try:
        try:
            conn, cursor = _ensure_db(conn, cursor)
            perfis = _load_servers(cursor)
        except OperationalError as exc:
            register_error()
            print(f"[erro] Banco indisponivel para iniciar processamento: {exc}")
            print(
                "[info] Verifique limite de conexoes no Postgres e rode novamente. "
                f"Retries configurados: {DB_CONNECT_RETRIES}."
            )
            return
        finally:
            _close_db(conn, cursor)
            conn, cursor = None, None

        if not perfis:
            print("[info] Nenhum perfil encontrado em server para processar.")
            return

        auth_probe_url = _normalize_profile_video_url(perfis[0][0])
        if not _ensure_authenticated_session(session, auth_probe_url):
            print(
                "[warn] Sessao ainda aparenta anonima apos tentativa automatica. "
                "Se necessario, renove manualmente os cookies com get_filmes.py."
            )

        workers = max(1, min(MAX_WORKERS, len(perfis)))
        auth_refresh_attempted = False
        print(
            f"[info] Iniciando requests scraper: perfis={len(perfis)} "
            f"dry_run={DRY_RUN} paginacao={ENABLE_EXPERIMENTAL_PAGINATION} "
            f"ignore_days={IGNORE_DAYS} resume_from_id={RESUME_FROM_IDSERVER} "
            f"workers={workers}"
        )

        if workers == 1:
            for perfil_url, idserver in perfis:
                total_profiles += 1
                profile_url = _normalize_profile_video_url(perfil_url)
                print(f"\n[info] Perfil {profile_url} (idserver {idserver})")
                pending_rows = []
                try:
                    try:
                        resp = _fetch_profile_page(session, profile_url)
                    except requests.RequestException as exc:
                        register_error()
                        print(f"[erro] Falha HTTP no perfil {profile_url}: {exc}")
                        continue

                    page_html = resp.text or ""
                    if resp.status_code == 404 or _is_404(page_html):
                        try:
                            conn, cursor = _ensure_db(conn, cursor)
                            _mark_server_inactive(cursor, conn, idserver)
                        except Exception as exc:  # pylint: disable=broad-except
                            register_error()
                            print(f"[erro] Nao foi possivel marcar server {idserver} como inativo: {exc}")
                        continue

                    base_videos = []
                    if _is_auth_required(page_html):
                        if not auth_refresh_attempted and AUTO_COOKIE_LOGIN:
                            auth_refresh_attempted = True
                            if _ensure_authenticated_session(session, profile_url):
                                try:
                                    resp = _fetch_profile_page(session, profile_url)
                                    page_html = resp.text or ""
                                except requests.RequestException as exc:
                                    register_error()
                                    print(f"[erro] Falha HTTP no perfil {profile_url} apos renovar cookies: {exc}")
                                    continue

                        if not _is_auth_required(page_html):
                            base_videos = _extract_videos_from_html(page_html)
                            if not base_videos:
                                print("[warn] Nenhum video encontrado na pagina visivel.")
                                continue
                        else:
                            print(
                                "[warn] Sessao anonima/challenge detectado para este perfil. "
                                "Atualize o okru_cookies.json com uma sessao valida."
                            )
                            continue

                    if not base_videos:
                        base_videos = _extract_videos_from_html(page_html)

                    if not base_videos:
                        print(
                            "[warn] Nenhum video encontrado na pagina visivel."
                        )
                        continue

                    if DRY_RUN:
                        extra_videos = _try_collect_extra_pages(session, profile_url, page_html, dict(resp.headers))
                        base_ids = {x["id"] for x in base_videos}
                        all_videos = base_videos + [v for v in extra_videos if v["id"] not in base_ids]
                        total_found += len(all_videos)
                        print(
                            f"[info] Videos encontrados: pagina_inicial={len(base_videos)} "
                            f"extras={len(extra_videos)} total={len(all_videos)}"
                        )
                        for item in all_videos[:5]:
                            print(f"  - {item['id']} | {item.get('duration','')} | {item.get('title','')[:80]}")
                        continue

                    order_offset = 0
                    saved_for_profile = 0
                    extra_counter = 0
                    flush_threshold = max(1, DB_FLUSH_EVERY)

                    def flush_pending():
                        nonlocal conn, cursor, pending_rows, saved_for_profile, total_saved
                        if not pending_rows:
                            return
                        conn, cursor, saved = _write_rows_with_retry(pending_rows, conn, cursor)
                        saved_for_profile += saved
                        total_saved += saved
                        pending_rows = []

                    def enqueue_videos(videos):
                        nonlocal order_offset, pending_rows
                        if not videos:
                            return
                        rows_part = _to_rows(videos, idserver, offset=order_offset)
                        order_offset += len(rows_part)
                        pending_rows.extend(rows_part)
                        if len(pending_rows) >= flush_threshold:
                            flush_pending()

                    enqueue_videos(base_videos)

                    def on_delta(delta, _page_idx):
                        nonlocal extra_counter
                        extra_counter += len(delta)
                        enqueue_videos(delta)

                    _try_collect_extra_pages(
                        session,
                        profile_url,
                        page_html,
                        dict(resp.headers),
                        on_delta=on_delta,
                    )
                    flush_pending()

                    found_for_profile = len(base_videos) + extra_counter
                    total_found += found_for_profile
                    print(
                        f"[info] Videos encontrados: pagina_inicial={len(base_videos)} "
                        f"extras={extra_counter} total={found_for_profile}"
                    )
                    print(f"[info] Gravados/atualizados {saved_for_profile} videos no banco.")
                except Exception as exc:  # pylint: disable=broad-except
                    register_error()
                    print(f"[erro] Falha ao processar/gravar videos do idserver={idserver}: {exc}")
                    if pending_rows:
                        backup = _backup_rows(pending_rows, idserver)
                        print(f"[warn] Backup salvo em: {backup}")
                    continue
                finally:
                    # Release DB slot between profiles to reduce chance of hitting max connections.
                    _close_db(conn, cursor)
                    conn, cursor = None, None
        else:
            normalized_perfis = [(_normalize_profile_video_url(url), sid) for url, sid in perfis]
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(_process_profile_network, profile_url, idserver): (profile_url, idserver)
                    for profile_url, idserver in normalized_perfis
                }
                for future in as_completed(future_map):
                    profile_url, idserver = future_map[future]
                    total_profiles += 1
                    pending_rows = []
                    print(f"\n[info] Perfil {profile_url} (idserver {idserver})")
                    try:
                        try:
                            result = future.result()
                        except Exception as exc:  # pylint: disable=broad-except
                            register_error()
                            print(f"[erro] Falha no worker do perfil {profile_url}: {exc}")
                            continue

                        status = result.get("status")
                        if status == "not_found":
                            try:
                                conn, cursor = _ensure_db(conn, cursor)
                                _mark_server_inactive(cursor, conn, idserver)
                            except Exception as exc:  # pylint: disable=broad-except
                                register_error()
                                print(f"[erro] Nao foi possivel marcar server {idserver} como inativo: {exc}")
                            continue
                        if status == "auth_required":
                            if not auth_refresh_attempted and AUTO_COOKIE_LOGIN:
                                auth_refresh_attempted = True
                                if _ensure_authenticated_session(session, profile_url):
                                    result = _process_profile_network(profile_url, idserver)
                                    status = result.get("status")
                            if status == "auth_required":
                                print(
                                    "[warn] Sessao anonima/challenge detectado para este perfil. "
                                    "Atualize o okru_cookies.json com uma sessao valida."
                                )
                                continue
                        if status == "empty":
                            print("[warn] Nenhum video encontrado na pagina visivel.")
                            continue
                        if status == "http_error":
                            register_error()
                            print(f"[erro] Falha HTTP no perfil {profile_url}: {result.get('error', '')}")
                            continue
                        if status != "ok":
                            register_error()
                            print(f"[erro] Falha no perfil {profile_url}: {result.get('error', 'erro desconhecido')}")
                            continue

                        all_videos = result.get("videos") or []
                        base_count = int(result.get("base_count") or 0)
                        extra_count = int(result.get("extra_count") or 0)
                        total_found += len(all_videos)
                        print(
                            f"[info] Videos encontrados: pagina_inicial={base_count} "
                            f"extras={extra_count} total={len(all_videos)}"
                        )

                        if DRY_RUN:
                            for item in all_videos[:5]:
                                print(
                                    f"  - {item.get('id','')} | "
                                    f"{item.get('duration','')} | {str(item.get('title',''))[:80]}"
                                )
                            continue

                        pending_rows = _to_rows(all_videos, idserver)
                        conn, cursor, saved = _write_rows_with_retry(pending_rows, conn, cursor)
                        total_saved += saved
                        pending_rows = []
                        print(f"[info] Gravados/atualizados {saved} videos no banco.")
                    except Exception as exc:  # pylint: disable=broad-except
                        register_error()
                        print(f"[erro] Falha ao processar/gravar videos do idserver={idserver}: {exc}")
                        if pending_rows:
                            backup = _backup_rows(pending_rows, idserver)
                            print(f"[warn] Backup salvo em: {backup}")
                        continue
                    finally:
                        _close_db(conn, cursor)
                        conn, cursor = None, None
    finally:
        elapsed = time.time() - started
        print(
            f"\n[info] Finalizado: perfis_processados={total_profiles}, "
            f"videos_encontrados={total_found}, videos_gravados={total_saved}, "
            f"erros={total_errors}, tempo_total={elapsed:.1f}s"
        )
        _write_run_log(total_profiles, total_found, total_saved, total_errors, elapsed)
        _close_db(conn, cursor)
        session.close()


if __name__ == "__main__":
    main()
