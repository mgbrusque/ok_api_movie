import hashlib
import math
import os
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable

from flask import jsonify, request, session
from werkzeug.security import check_password_hash


LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def admin_username() -> str:
    return (os.environ.get("APP_ADMIN_USERNAME") or "admin").strip()


def auth_is_configured() -> bool:
    return bool((os.environ.get("APP_ADMIN_PASSWORD_HASH") or "").strip())


def _auth_fingerprint() -> str:
    password_hash = (os.environ.get("APP_ADMIN_PASSWORD_HASH") or "").strip()
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def verify_admin_credentials(username: str, password: str) -> bool:
    password_hash = (os.environ.get("APP_ADMIN_PASSWORD_HASH") or "").strip()
    if not password_hash or not password:
        return False
    username_matches = secrets.compare_digest(username, admin_username())
    try:
        password_matches = check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        password_matches = False
    return username_matches and password_matches


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def rotate_authenticated_session() -> str:
    session.clear()
    session["admin_authenticated"] = True
    session["admin_username"] = admin_username()
    session["admin_auth_fingerprint"] = _auth_fingerprint()
    session.permanent = True
    return csrf_token()


def logout_session() -> str:
    session.clear()
    return csrf_token()


def is_admin_authenticated() -> bool:
    return bool(
        auth_is_configured()
        and session.get("admin_authenticated")
        and secrets.compare_digest(
            session.get("admin_auth_fingerprint") or "",
            _auth_fingerprint(),
        )
    )


def csrf_is_valid() -> bool:
    expected = session.get("csrf_token") or ""
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
    return bool(expected and supplied and secrets.compare_digest(expected, supplied))


def require_admin(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin_authenticated():
            return jsonify({"error": "Login necessário.", "code": "authentication_required"}), 401
        return view(*args, **kwargs)

    return wrapped


def require_csrf(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not csrf_is_valid():
            return jsonify({"error": "Sessão inválida. Atualize a página e tente novamente.", "code": "csrf_invalid"}), 403
        return view(*args, **kwargs)

    return wrapped


def _attempt_key() -> str:
    return request.remote_addr or "unknown"


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int((os.environ.get(name) or str(default)).strip()))
    except ValueError:
        return default


def login_max_attempts() -> int:
    return _positive_int_env("ADMIN_LOGIN_MAX_ATTEMPTS", LOGIN_MAX_ATTEMPTS)


def login_window_seconds() -> int:
    minutes = _positive_int_env("ADMIN_LOGIN_WINDOW_MINUTES", LOGIN_WINDOW_SECONDS // 60)
    return minutes * 60


def login_retry_after() -> int:
    now = time.monotonic()
    attempts = _login_attempts[_attempt_key()]
    window = login_window_seconds()
    while attempts and now - attempts[0] > window:
        attempts.popleft()
    if len(attempts) < login_max_attempts():
        return 0
    return max(1, math.ceil(window - (now - attempts[0])))


def login_is_rate_limited() -> bool:
    return login_retry_after() > 0


def record_failed_login() -> None:
    _login_attempts[_attempt_key()].append(time.monotonic())


def clear_failed_logins() -> None:
    _login_attempts.pop(_attempt_key(), None)
