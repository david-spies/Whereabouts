Here is a highly scannable, minimal QUICKSTART.md designed to get developers up and running with the hybrid stack in under 60 seconds.

Whereabouts: 3-Terminal Quickstart

Follow this exact sequence to spin up the containerized datastores, activate the async web endpoints, and bring the AI worker cluster online.
Terminal 1: Infrastructure Datastores

Launch the containerized PostGIS database and the RabbitMQ message broker.
Bash

# Clean up legacy networks and launch backplanes
docker-compose down --volumes --remove-orphans
docker network prune -f
docker-compose up -d

# Verify containers are healthy
docker-compose ps

Terminal 2: FastAPI Web Core

Boots the asynchronous web gateway to ingest media payloads and serve Leaflet-ready GeoJSON.
Bash

# Activate virtual environment
source venv/bin/activate

# Inject async storage runtime coordinates
export ASYNC_DATABASE_URL="postgresql+asyncpg://admin:secure_dev_password@127.0.0.1:5432/whereabouts_dev"

# Launch the hot-reloading web engine
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Terminal 3: Celery AI Worker Pool

Boots the background processing cluster to handle live visual inference and spatial translation.
Bash

# Activate virtual environment
source venv/bin/activate

# Inject worker storage and broker coordinates
export DATABASE_URL="postgresql://admin:secure_dev_password@127.0.0.1:5432/whereabouts_dev"
export CELERY_BROKER_URL="amqp://guest:guest@127.0.0.1:5672//"

# Run database migrations, then start the worker cluster
alembic upgrade head
celery -A app.workers.tasks.celery_app worker --loglevel=info

🚀 Smoke Test Execution

Open a temporary terminal window and run this end-to-end integration test:
Bash

# 1. Create a quick mock asset file
echo "mock_camera_bytes" > urban_test_image.jpg

# 2. Ingest the payload via the FastAPI pipeline
curl -X POST "http://127.0.0.1:8000/api/v1/scanner/process-media" \
     -F "file=@urban_test_image.jpg;type=image/jpeg"

(Copy the returned tracking_id from the response to fetch the Leaflet-ready GeoJSON feature payload at http://127.0.0.1:8000/api/v1/scanner/scans/<TRACKING_ID>/geojson).
