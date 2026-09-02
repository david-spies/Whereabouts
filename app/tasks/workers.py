import os
from celery import Celery
from pathlib import Path
import asyncio
from app.services.metadata_extractor import MetadataExtractorService
from app.ml.geo_scanner import WhereaboutsAIEngine

# Instantiate Celery Worker Stack
celery_app = Celery(
    "whereabouts_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("DATABASE_URL")
)

metadata_service = MetadataExtractorService()
ai_engine = WhereaboutsAIEngine(
    qdrant_endpoint=os.getenv("QDRANT_HOST", "http://qdrant:6333"), 
    api_key=os.getenv("QDRANT_API_KEY", "LOCAL_DEVELOPMENT_DUMMY_KEY")
)

@celery_app.task(name="pipeline.execute_full_analysis")
def execute_full_analysis(file_str_path: str):
    """
    Decoupled Task Execution Pipeline executing within worker clusters.
    Keeps blocking operations off the main API web nodes.
    """
    file_path = Path(file_str_path)
    
    # Run async extraction methods in Worker context safely
    loop = asyncio.get_event_loop()
    raw_metadata = loop.run_until_complete(metadata_service.extract_metadata(file_path))
    extracted_gps = metadata_service.parse_gps_coordinates(raw_metadata)
    
    # Run heavy PyTorch / VLM prediction matrices
    ai_spatial_prediction = loop.run_until_complete(ai_engine.execute_spatial_inference(str(file_path)))
    
    # Cleanup resource file pointers out of band
    file_path.unlink(missing_ok=True)
    
    return {
        "metadata_check": {
            "exif_found": extracted_gps is not None,
            "extracted_gps": extracted_gps
        },
        "visual_estimation": {
            "latitude": ai_spatial_prediction["primary_match"]["coordinates"][0],
            "longitude": ai_spatial_prediction["primary_match"]["coordinates"][1],
            "confidence": ai_spatial_prediction["primary_match"]["confidence_score"],
            "evidence_logs": ai_spatial_prediction["visual_evidence_chain"]
        }
    }
