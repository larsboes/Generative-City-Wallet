FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY apps/api/src/spark apps/api/src/spark
COPY .env .env

ENV PYTHONPATH=/app/apps/api/src

# Create data directory for SQLite
RUN mkdir -p data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "spark.main:app", "--host", "0.0.0.0", "--port", "8000"]
