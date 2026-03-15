FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[all]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy alembic psycopg2-binary \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    aiofiles httpx celery redis

COPY . .

EXPOSE 8000
