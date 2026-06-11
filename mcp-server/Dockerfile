# -------------------------------------------------------------------------
# STAGE 1: Builder
# -------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app/services/mcp-server

RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

# Copia somente manifests para cache de deps
COPY services/mcp-server/pyproject.toml \
     services/mcp-server/poetry.lock ./


RUN poetry install --no-root

# Copia o código
COPY services/mcp-server .

# -------------------------------------------------------------------------
# STAGE 2: Runtime
# -------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/services/mcp-server

COPY --from=builder /app/services/mcp-server .

ENV PATH="/app/services/mcp-server/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/mcp-server/src"

EXPOSE 8080

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "1", "--threads", "8", \
     "-b", "0.0.0.0:8080", \
     "mcp_server.main:app"]
