<div align="center">

<img src="assets/Whereabouts_banner.png" alt="Whereabouts: Enterprise Visual Geolocation Scanner" width="100%"/>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-005571?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostGIS](https://img.shields.io/badge/PostGIS-Spatial%20DB-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-red?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-Async%20Worker-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-VLM%20Engine-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

# Whereabouts: Enterprise Visual Geolocation Scanner

Whereabouts is a high-throughput, multi-modal visual intelligence and geolocation platform. It profiles and estimates physical locations from image and video payloads by fusing deep vector feature extraction, zero-shot botanical/architectural classification, physical signage OCR text reading, and hardware EXIF telemetry.

The system utilizes a dynamic, four-stage inference pipeline:
1. **Coarse Structural Vector Matching:** DINOv2 (`dinov2_vitl14`) 1024-dimensional dense vector embeddings queried against Qdrant.
2. **Zero-Shot Visual Classification:** Open-world botanical (flora) and architectural classification using OpenAI's CLIP (`clip-vit-base-patch32`).
3. **Physical Signage OCR Reader:** Deep text extraction using EasyOCR to read road signs, street markers, and building plaques.
4. **Multi-Factor Scoring & Sensor Fusion Fallback:** Combines raw vector cosine similarity with OCR detection bonuses ($+0.15$). If composite confidence drops below operational threshold limits ($<0.35$), the platform automatically triggers **Sensor Fusion Fallback**, routing exact spatial coordinates to embedded hardware EXIF metadata while retaining extracted flora and structural contexts.

---

## 🏗️ Directory Architecture

```plaintext
Whereabouts/
├── .env.development            # Local environment configurations
├── .dockerignore               # Prevents local cache layers from leaking into Docker
├── docker-compose.yml          # Containerized database, broker, and cache infrastructure
├── requirements.txt            # Main python dependency manifest
├── alembic.ini                 # Database migration configuration metadata
├── seed_vector.py              # Qdrant reference vector seeding utility (Real Image & Synthetic)
│
├── migrations/                 # Active database schema migration tracking repository
│   ├── env.py                  # Alembic migrations orchestrator script
│   ├── README                  # Migration directory documentation
│   ├── script.py.mako          # Migration script generation template
│   └── versions/               # Saved historical database version states (PostGIS schemas)
│
├── qdrant_storage/             # Persistent local disk volume for the Qdrant vector database
│
├── app/                        # Main application package boundary
│   ├── __init__.py
│   ├── main.py                 # FastAPI initialization & routing assembly
│   │
│   ├── api/                    # API Version control routing matrix
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── scanner.py  # Ingestion endpoints & async PostGIS GeoJSON queries
│   │
│   ├── core/                   # Application runtime settings
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic BaseSettings environment parser
│   │   └── security.py         # Sandboxing parameters & cryptographic helpers
│   │
│   ├── db/                     # Persistence layer infrastructure
│   │   ├── __init__.py
│   │   └── session.py          # Asynchronous database engine pool generators
│   │
│   ├── ml/                     # Vision Machine Learning Subsystem
│   │   ├── __init__.py
│   │   ├── engine.py           # Standalone multi-modal VLM engine (Video keyframe & OCR)
│   │   ├── geo_scanner.py      # WhereaboutsAIEngine with DINOv2, CLIP, EasyOCR & Sensor Fusion
│   │   └── weights/
│   │       └── .gitkeep        # High-density model feature weight mounts
│   │
│   ├── models/                 # Relational Schema Definitions
│   │   ├── __init__.py
│   │   └── spatial.py          # GeoAlchemy2 PostGIS database mapping configurations
│   │
│   ├── services/               # Processing utility frameworks
│   │   ├── __init__.py
│   │   └── metadata_extractor.py # Hardened ExifTool parser wrappers
│   │
│   ├── templates/              # Frontend User Interface Assets
│   │   └── map.html            # Leaflet.js real-time telemetry dashboard layout
│   │
│   └── workers/                # Asynchronous Task Distribution Tier
│       ├── __init__.py
│       └── tasks.py            # Long-running ML processing & spatial persistence jobs
│
└── docker/                     # Deployment Dockerfile targets
    ├── api.Dockerfile
    └── worker.Dockerfile
```

🛠️ Infrastructure Topologies & PrerequisitesHybrid Local/Native Mode (Recommended for Development / Linux)Persistent datastores (PostGIS, Qdrant) and message brokers (RabbitMQ) execute via Docker containers, while FastAPI endpoints, Celery workers, and migration tools run directly inside your host environment's Python Virtual Environment (venv). This preserves native GPU acceleration (PyTorch/CUDA) and avoids container layering overhead during development. Host System Baseline Dependencies Ensure your host machine has the following baseline system packages installed natively before proceeding:

Bash

sudo apt update && sudo apt install -y build-essential libgl1-mesa-glx libglib2.0-0 exiftool libpq-dev netcat-openbsd

🚦 Orchestration & Service Startup Matrix 

To eliminate socket race conditions and structural errors (such as Duplicate Table Error or memory exhaustion events), system initialization must strictly follow the operational checklist below.

Summary Quick-Reference TablePhaseTerminal ScopeVirtual Env (venv)Core Command / Action0. PreparationTerminal 1OUTSIDE venvdocker-compose up -dI. Health CheckTerminal 1INSIDE venvNetwork socket readiness verification loopII. DatabaseTerminal 1INSIDE venvalembic upgrade head (Do not run init_db.py)III. Vector SeedTerminal 1INSIDE venvpython3 seed_vector.pyIV. BackgroundTerminal 2INSIDE venvcelery -A app.workers.tasks.celery_app worker -c 2V. Web CoreTerminal 3INSIDE venvuvicorn app.main:app --reload

🏃‍♂️ Step-by-Step Execution Playbook

📦 Phase 0: Launch Core Datastores 
Open your first terminal window at the host level.

Venv Context: OUTSIDE venv (Host Shell)

Bash
# Force-flush conflicting historical networks and orphan data volumes
docker-compose down --volumes --remove-orphans
docker network prune -f

# Spin backing infrastructure services up into background daemons
docker-compose up -d

This provisions whereabouts_postgres_1 (PostGIS), whereabouts_rabbitmq_1 (AMQP Broker), and whereabouts_qdrant_1 (Vector DB).

🚦 Phase I: Infrastructure Readiness CheckIn the same terminal window, activate your virtual environment and poll network interfaces to confirm container daemons are ready.

Venv Context: INSIDE venv

Bash

source venv/bin/activate

# Poll background ports until PostGIS, RabbitMQ, and Qdrant accept connections
echo "Checking daemon socket availability..."
until nc -z 127.0.0.1 5432 && nc -z 127.0.0.1 5672 && nc -z 127.0.0.1 6333; do
  echo "⏳ Waiting for PostGIS (5432), RabbitMQ (5672), and Qdrant (6333) to initialize..."
  sleep 2
done
echo "✅ All backing databases and message brokers are live."

🗄️ Phase II: PostGIS Relational Schema Initialization Venv Context: INSIDE venv (Terminal 1 continued)

Bash

# Execute structural schema migration tracking
alembic upgrade head

⚠️ CRITICAL ARCHITECTURAL WARNING: Do NOT run python3 init_db.py. Manual setup utilities alongside Alembic trigger a DuplicateTableError: relation "geospatial_scans" already exists crash because Alembic maintains sole state ownership over the PostGIS schema.

🌱 Phase III: Qdrant Vector Space SeedingVenv Context: INSIDE venv (Terminal 1 continued)
Populate the urban_global_geoms collection space with model reference dimensions and baseline image feature embeddings:

Bash

python3 seed_vector.py

(Terminal 1 has fulfilled its initialization loop and can now remain open for database inspection.)

🧠 Phase IV: Celery Worker Processing CoreOpen a second terminal window (Terminal 2).

Venv Context: INSIDE venv

Bash

source venv/bin/activate

# Start the worker cluster with explicit hardware concurrency limits
celery -A app.workers.tasks.celery_app worker --loglevel=info -P prefork --concurrency=2

⚠️ CRITICAL MEMORY NOTE: You must provide an explicit concurrency cap via --concurrency=2 or -c 2 alongside -P prefork. Because each individual prefork child process caches its own independent instance of the heavy deep learning models (DINOv2, CLIP, EasyOCR) in RAM/VRAM, unconstrained concurrency will trigger the Linux Kernel OOM Killer to terminate worker processes (SIGKILL).

🌐 Phase V: FastAPI Async Web Core

Open a third terminal window (Terminal 3).

Venv Context: INSIDE venv

Bash

source venv/bin/activate

# Launch the non-blocking HTTP microservice gateway
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

🚀 Verification, Testing & API Ingestion

1. Dispatch an Ingress Media Payload

Open an independent ingestion shell session (Terminal 4), navigate to your root project directory, and fire a target image or video payload into the ingress endpoint:

Bash

curl -X POST "[http://127.0.0.1:8000/api/v1/scanner/process-media](http://127.0.0.1:8000/api/v1/scanner/process-media)" \
     -F "file=@/home/alien/Videos/DSC04375.JPG;type=image/jpeg"

The gateway stores the uploaded asset, posts an async task ID to RabbitMQ, and returns a tracking ticket:

JSON{
  "tracking_id": "db431f16-e33d-4a4f-b052-853c665561ec",
  "task_id": "c39cd5d4-e95d-4eb5-8718-aa00e653f987",
  "status": "QUEUED",
  "map_configuration": {
    "tile_provider": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "attribution": "© OpenStreetMap contributors",
    "layer_format": "EPSG:4326"
  }
}

2. Verify Leaflet-Ready GeoJSON OutputQuery your committed spatial results layer using the issued tracking_id:

Bash

curl -X GET "[http://127.0.0.1:8000/api/v1/scanner/scans/11c74158-1fed-4d47-8e9d-de08d05dcd11/geojson](http://127.0.0.1:8000/api/v1/scanner/scans/11c74158-1fed-4d47-8e9d-de08d05dcd11/geojson)"

Example Response Payload:

JSON{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-121.77858, 47.436018]
  },
  "properties": {
    "tracking_id": "11c74158-1fed-4d47-8e9d-de08d05dcd11",
    "confidence": 0.0192,
    "accuracy_radius": 15.0,
    "evidence_logs": {
      "signage_text_found": "NONE",
      "detected_foliage": "Subalpine Evergreen Meadows",
      "architectural_era": "Pacific Northwest Timber Frame",
      "logical_deduction_chain": "Visual vector confidence (0.02) below threshold (<0.35). Defaulting pipeline logic. [SENSOR FUSION FALLBACK: Rerouted to high-accuracy hardware EXIF metadata]."
    },
    "created_at": "2026-07-21T05:48:13.148000+00:00"
  }
}

🗺️ Live Telemetry Frontend Dashboard

The platform features an embedded, live telemetry tracking interface integrated directly into the FastAPI application layer. This design bypasses cross-origin environment blocks (CORS) and browser filesystem sandboxing constraints.To view your processed coordinates on the interactive dark-mode dashboard map, open your browser and pass your target entry tracking_id as a query parameter:

Plaintext[http://127.0.0.1:8000/map?id=11c74158-1fed-4d47-8e9d-de08d05dcd11](http://127.0.0.1:8000/map?id=11c74158-1fed-4d47-8e9d-de08d05dcd11)

# Key UI Features:

Interactive Tracking Controller: An upper-left panel allowing instant lookup and hot-swapping of active tracking tickets.
Live Telemetry Polling: Runs non-blocking polling loops every 4 seconds to retrieve background worker updates until coordinate lock is achieved.
Full Evidence Log Visualization: Displays confidence percentages, accuracy radiuses ($\pm 15\text{m}$), detected flora context, architectural classifications, signage text, and complete deduction chains.

🗺️ Troubleshooting: CARTO Basemap Tile "API Key Required" Issue

Problem Description

When accessing the Leaflet web dashboard, map tiles may appear tiled with a black-and-white world map overlay containing repeating text blocks stating "API KEY REQUIRED". This occurs because CARTO updated its raster tile endpoints to enforce API token authorization. If a key is missing or omitted from the Leaflet tile layer configuration, the basemap service restricts tile delivery and falls back to a watermarked error placeholder.

Resolution Options

You can resolve this mapping artifact using one of two approaches:

Option A: Switch to Standard OpenStreetMap Tiles (Recommended / Quickest)

If you do not require specific CARTO stylized map layers during local development, update the map template to use native OpenStreetMap tiles, which require no registration or API keys.

    Open your map template file:

    Bash

    nano app/templates/map.html

    Locate the L.tileLayer initialization script block.

    Replace the CARTO URL string with the official open OpenStreetMap tile definition:
    JavaScript

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    Save the file and refresh your browser tab.

Option B: Obtain and Configure a Free CARTO Basemap Key

If your deployment mandates specific CARTO map themes and styling:

    Register for a free development token via the CARTO Basemaps API Key Portal (free for personal and development usage up to high monthly limits).

    Open your map template file:
    Bash

    nano app/templates/map.html

    Append your live API token key parameter to the raster endpoint URL string:
    JavaScript

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=YOUR_ACTUAL_CARTO_KEY', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        maxZoom: 20
    }).addTo(map);

    Save the file and reload the dashboard interface.

📜 License

This project is open-source software licensed under the MIT License.

