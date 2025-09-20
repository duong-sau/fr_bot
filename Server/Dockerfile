FROM python:3.11-slim

# Cài docker-cli để gọi docker qua /var/run/docker.sock
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/code
COPY .. /app/code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/logs /app/data
RUN pip install --no-cache-dir -r /app/code/requirements.txt

EXPOSE 8000
CMD ["python", "Server/App.py"]

