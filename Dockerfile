# Build:
#   docker build -t crime-intelligence-api .
#
# Run against a PostgreSQL instance on the host machine:
#   docker run --rm -p 8000:8000 ^
#     -e DB_HOST=host.docker.internal ^
#     -e DB_PORT=5432 ^
#     -e DB_NAME=crimedb ^
#     -e DB_USER=postgres ^
#     -e DB_PASSWORD=<password> ^
#     crime-intelligence-api
#
# Or provide a single DATABASE_URL instead:
#   docker run --rm -p 8000:8000 ^
#     -e DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/crimedb ^
#     crime-intelligence-api
#
# In production, credentials (DATABASE_URL, JWT_SECRET) are injected at runtime
# by the ECS task definition — they are NOT baked into the image.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY App ./App
COPY Database ./Database

EXPOSE 8000

# Liveness check — the slim image ships no curl, so use Python's urllib.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else sys.exit(1)" || exit 1

CMD ["uvicorn", "App.main:app", "--host", "0.0.0.0", "--port", "8000"]
