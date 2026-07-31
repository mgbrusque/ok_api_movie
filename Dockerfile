FROM python:3.11-slim-bookworm

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000 \
    OKRU_CHROME_BINARY=/usr/bin/chromium \
    OKRU_CHROMEDRIVER=/usr/bin/chromedriver \
    OKRU_COOKIES_FILE=/data/okru_cookies.json \
    OKRU_ARTIFACTS_DIR=/data/artifacts

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=app:app . .
RUN mkdir -p /data/artifacts \
    && chown -R app:app /data /app

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '5000') + '/healthz', timeout=3)" || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
