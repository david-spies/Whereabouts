# docker/worker.Dockerfile
FROM python:3.11-slim

WORKDIR /whereabouts

# Force standard public DNS inside the container workspace
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    exiftool \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
