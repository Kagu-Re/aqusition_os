# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

# System deps kept minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml README.md ./
COPY src ./src
COPY ops ./ops

# Install (no dev deps). We assume pyproject uses Poetry-style metadata but install via pip.
# If you switch to Poetry runtime, adjust this section.
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir .

EXPOSE 8000 8001

# Optional container-level healthcheck (compose overrides per-service)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://localhost:8000/health >/dev/null || exit 1

# Default to console. Override with CMD for public.
CMD ["ae", "serve-console", "--host", "0.0.0.0", "--port", "8000"]
