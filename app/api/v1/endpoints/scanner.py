# app/api/v1/endpoints/scanner.py
import json
import logging
import shutil
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# IMPORT ALIGNMENT: Pointing explicitly to your updated spatial execution worker task
from app.db.session import get_async_db
from app.models.spatial import GeospatialScan
from app.workers.tasks import execute_full_analysis

logger = logging.getLogger(__name__)

router = APIRouter()
TMP_UPLOAD_DIR = Path("/tmp/whereabouts_ingress")
TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --- ENDPOINTS ---


@router.post("/process-media", status_code=202, tags=["Ingress Pipelines"])
async def process_media_payload(file: UploadFile = File(...)):
    """
    Ingests payload streams (images/videos) securely, caches them to a hardened
    ingress volume, and dispatches processing contracts immediately to the Celery pool.
    """
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in [".jpg", ".jpeg", ".png", ".webp", ".mp4"]:
        raise HTTPException(
            status_code=400, detail="Unsupported media architecture stream."
        )

    session_id = uuid.uuid4()
    target_disk_path = TMP_UPLOAD_DIR / f"{session_id}{file_extension}"

    try:
        with target_disk_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as io_err:
        logger.error(
            f"Failed to cache incoming media stream to disk: {str(io_err)}"
        )
        raise HTTPException(
            status_code=500, detail="Local ingress write failure."
        )

    try:
        # ALIGNMENT CORRECTED: Dispatches tracking_id to coordinate perfectly with the PostGIS row binding
        task = execute_full_analysis.delay(
            str(session_id), str(target_disk_path)
        )

        return {
            "tracking_id": str(session_id),
            "task_id": task.id,
            "status": "QUEUED",
            "map_configuration": {
                "tile_provider": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors",
                "layer_format": "EPSG:4326",
            },
        }
    except Exception as err:
        # Guarantee physical file destruction if the message broker handshake fails
        target_disk_path.unlink(missing_ok=True)
        logger.error(f"Celery task dispatch crash encountered: {str(err)}")
        raise HTTPException(
            status_code=500, detail=f"Broker dispatch error: {str(err)}"
        )


@router.get("/scans/{tracking_id}/geojson", tags=["Spatial Queries"])
async def get_scan_geojson(
    tracking_id: UUID, db: AsyncSession = Depends(get_async_db)
):
    """
    Enterprise Spatial Query Edge.
    Retrieves precise geolocation match records formatted natively as a GeoJSON Feature
    using database-level serialization for sub-millisecond response loops.
    """
    # Offload the GeoJSON conversion to PostGIS at query execution time
    query = select(
        GeospatialScan,
        ST_AsGeoJSON(GeospatialScan.inferred_location).label("geojson_geom"),
    ).where(GeospatialScan.tracking_id == tracking_id)

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Requested spatial telemetry signature not found.",
        )

    scan_record, raw_geojson_geometry = row

    # Construct the final compliant RFC 7946 GeoJSON Feature Object
    return {
        "type": "Feature",
        "geometry": json.loads(raw_geojson_geometry),
        "properties": {
            "tracking_id": str(scan_record.tracking_id),
            "confidence": float(scan_record.confidence_score),
            "accuracy_radius": scan_record.accuracy_radius_meters,
            "evidence_logs": scan_record.visual_evidence_json,
            "created_at": scan_record.created_at.isoformat(),
        },
    }
