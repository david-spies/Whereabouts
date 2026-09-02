# app/workers/tasks.py
import asyncio
import logging
import uuid
from pathlib import Path
from celery import Celery
from celery.signals import worker_process_init
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.ml.geo_scanner import WhereaboutsAIEngine
from app.models.spatial import GeospatialScan
from app.services.metadata_extractor import MetadataExtractorService

logger = logging.getLogger(__name__)

celery_app = Celery("whereabouts_tasks", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(result_backend=settings.CELERY_RESULT_BACKEND)

sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(sync_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata_extractor = None
ai_engine = None


@worker_process_init.connect
def init_worker_processes(*args, **kwargs):
    """
    Initializes heavy models once per worker process to optimize memory usage.
    """
    global metadata_extractor, ai_engine
    logger.info("Initializing process-isolated worker resources.")
    metadata_extractor = MetadataExtractorService()
    qdrant_url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
    ai_engine = WhereaboutsAIEngine(
        qdrant_endpoint=qdrant_url,
        api_key=settings.QDRANT_API_KEY
    )


async def _async_pipeline_wrapper(target_path: Path, file_path: str):
    raw_metadata = await metadata_extractor.extract_metadata(target_path)
    gps_data = metadata_extractor.parse_gps_coordinates(raw_metadata)
    ai_spatial_prediction = await ai_engine.execute_spatial_inference(file_path)
    return gps_data, ai_spatial_prediction


@celery_app.task(name="pipeline.execute_full_analysis", bind=True, max_retries=3)
def execute_full_analysis(self, tracking_id: str, file_path: str):
    logger.info(f"Executing spatial pipeline analysis | Tracking ID: {tracking_id}")
    db_session = SessionLocal()
    target_path = Path(file_path)

    try:
        if not target_path.exists():
            raise FileNotFoundError(f"Source media payload not found at: {file_path}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            gps_data, ai_spatial_prediction = loop.run_until_complete(
                _async_pipeline_wrapper(target_path, file_path)
            )
        finally:
            loop.close()

        primary_match = ai_spatial_prediction.get("primary_match")
        evidence_payload = ai_spatial_prediction.get("visual_evidence_chain", {})

        inferred_lat = primary_match["coordinates"][0]
        inferred_lon = primary_match["coordinates"][1]
        confidence = float(primary_match.get("confidence_score", 0.0))
        accuracy_radius = 5000.0

        metadata_point = None
        if gps_data:
            logger.info(f"Hardware EXIF GPS telemetry extracted: {gps_data}")
            metadata_point = from_shape(Point(gps_data["longitude"], gps_data["latitude"]), srid=4326)

        # Dual-Stage Fallback Trigger Logic
        if confidence < 0.35:
            if gps_data:
                logger.warning(
                    f"Visual model confidence ({confidence:.2f}) below operational threshold (<0.35). "
                    "Routing location coordinates to hardware EXIF sensor data."
                )
                inferred_lon = gps_data["longitude"]
                inferred_lat = gps_data["latitude"]
                accuracy_radius = 15.0  # Precision hardware radius
                evidence_payload["logical_deduction_chain"] += (
                    " [SENSOR FUSION FALLBACK: Rerouted to high-accuracy hardware EXIF metadata]."
                )
            else:
                logger.warning(
                    f"Low visual confidence ({confidence:.2f}) and no hardware EXIF data available. "
                    "Retaining low-confidence inference vector."
                )

        spatial_point = Point(inferred_lon, inferred_lat)
        validated_uuid = uuid.UUID(tracking_id)

        new_scan = GeospatialScan(
            tracking_id=validated_uuid,
            inferred_location=from_shape(spatial_point, srid=4326),
            metadata_location=metadata_point,
            confidence_score=confidence,
            accuracy_radius_meters=accuracy_radius,
            visual_evidence_json=evidence_payload
        )

        db_session.add(new_scan)
        db_session.commit()
        logger.info(f"Scan result saved successfully | ID: {tracking_id}")
        return {"status": "SUCCESS", "tracking_id": tracking_id}

    except Exception as exc:
        db_session.rollback()
        logger.error(f"Worker task error for ID {tracking_id}: {str(exc)}")
        if isinstance(exc, FileNotFoundError):
            return {"status": "FAILED", "reason": str(exc)}
        raise self.retry(exc=exc, countdown=10)
    finally:
        db_session.close()
        # Clean up temporary upload payload
        target_path.unlink(missing_ok=True)
