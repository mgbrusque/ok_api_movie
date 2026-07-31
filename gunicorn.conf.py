import os


def positive_int(name: str, default: int) -> int:
    try:
        return max(1, int((os.environ.get(name) or str(default)).strip()))
    except ValueError:
        return default


bind = f"0.0.0.0:{positive_int('PORT', 5000)}"
workers = positive_int("GUNICORN_WORKERS", 1)
threads = positive_int("GUNICORN_THREADS", 4)
timeout = positive_int("GUNICORN_TIMEOUT", 300)
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True
