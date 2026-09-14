# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY data/mock ./data/mock

RUN python -m pip install .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/runtime \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "scripts/docker_start.py"]

