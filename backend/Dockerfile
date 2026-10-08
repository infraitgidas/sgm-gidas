FROM python:3.11.16-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --only-binary=:all: --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11.16-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py

WORKDIR /app

# Fuentes Debian por https: el mirror http devuelve 403 en el build de la VM.
RUN (sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null) \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY app.py config.py extension.py entrypoint.sh seed_roles.py ./
COPY modules ./modules
COPY migrations ./migrations
COPY tools ./tools
COPY assets ./assets

RUN chmod +x /app/entrypoint.sh \
    && chown -R app:app /app

EXPOSE 5000

USER app

CMD ["/app/entrypoint.sh"]

FROM runtime AS development

USER root
RUN (sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null) \
    && apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
USER app

FROM runtime AS production
