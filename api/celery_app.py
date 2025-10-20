"""
Celery configuration for background IFC processing tasks.
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery instance
celery_app = Celery(
    "rig_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing
celery_app.conf.task_routes = {
    "api.tasks.parse_ifc_file": {"queue": "ifc_processing"},
    "api.tasks.convert_ifc_to_json": {"queue": "ifc_processing"},
    "api.tasks.ingest_to_neo4j": {"queue": "neo4j_ingestion"},
    "api.tasks.build_semantic_index": {"queue": "indexing"},
}

if __name__ == "__main__":
    celery_app.start()
