FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    PORT=5000 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=60

WORKDIR ${APP_HOME}

COPY requirements.txt ./

RUN pip install -r requirements.txt

RUN groupadd --system app && \
    useradd --system --gid app --home-dir ${APP_HOME} --shell /usr/sbin/nologin app

COPY . .

RUN chown -R app:app ${APP_HOME}

USER app

EXPOSE 5000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --worker-class gthread --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} --access-logfile - --error-logfile - app:app"]
