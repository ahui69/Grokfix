
# Production-ready minimal image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKSPACE=/app \
    MEM_DB=/app/data/mem.db \
    CORS_ORIGINS=http://localhost:8080 \
    RL_DISABLE=0 \
    RL_RPM_LIMIT=60

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# dev reqs optional
COPY requirements-dev.txt /app/requirements-dev.txt
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt || true; fi

COPY . .

EXPOSE 8080
CMD ["python", "main.py"]
