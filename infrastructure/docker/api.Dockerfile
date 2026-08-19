FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY apps/api/src ./src
COPY data/demo ./data/demo
COPY database/migrations ./database/migrations

EXPOSE 8000
CMD ["sh", "-c", "uv run python -m geodashboard_api.migrate && uv run uvicorn geodashboard_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
