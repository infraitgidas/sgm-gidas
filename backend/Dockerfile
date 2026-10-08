FROM python:3.11-slim AS builder

WORKDIR /app

RUN (sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null) \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py

WORKDIR /app

RUN (sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null) \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY . .

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
