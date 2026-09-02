# app/workers/celery_app.py
import os
from celery import Celery

def create_celery_app() -> Celery:
    """
    Factory function to instantiate and harden the Celery broker instance.
    Utilizes a lightweight RPC backend to completely decouple task state tracking 
    from SQLAlchemy database dependencies, avoiding runtime environment driver crashes.
    """
    # 1. Fetch raw environment broker configuration strings safely
    raw_broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@127.0.0.1:5672//")

    # 2. Hardcode the backend to transient RPC messaging. 
    # This prevents Celery from evaluating DATABASE_URL strings, skipping the 
    # dynamic SQLAlchemy import verification entirely.
    sanitized_backend = "rpc://"

    # 3. Instantiate the master Celery application node object
    app = Celery(
        "whereabouts_tasks",
        broker=raw_broker_url,
        backend=sanitized_backend
    )

    # 4. Enforce enterprise operational configurations
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        
        # Concurrency ceiling: Prevent high-throughput media tasks from overwhelming VRAM/RAM pools
        worker_prefetch_multiplier=1,
        
        # Keep result tracking active over the AMQP channels for WebSocket synchronization loops
        task_ignore_result=False,
    )

    # 5. Automatically detect tasks registered under the workers domain pipeline
    app.autodiscover_tasks(["app.workers"])
    
    return app

# Instantiate the application node for invocation by the CLI command process
celery_app = create_celery_app()
