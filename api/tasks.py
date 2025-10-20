"""
Background tasks for IFC processing and ingestion.
"""
import os
import json
import uuid
import tempfile
import subprocess
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from celery import current_task
from celery_app import celery_app
from dotenv import load_dotenv

load_dotenv()

# Cloud storage configuration
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rig-ifc-files")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "https://your-account-id.r2.cloudflarestorage.com")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/rig")

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DB = os.getenv("NEO4J_DATABASE", "neo4j")


class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def update_job_status(job_id: str, status: str, progress: int = 0, message: str = "", metadata: Dict[str, Any] = None):
    """Update job status in database."""
    # This would typically update a PostgreSQL database
    # For now, we'll use Redis as a simple store
    import redis
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    
    job_data = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    
    redis_client.hset(f"job:{job_id}", mapping=job_data)
    redis_client.expire(f"job:{job_id}", 86400)  # Expire after 24 hours


@celery_app.task(bind=True, name="api.tasks.parse_ifc_file")
def parse_ifc_file(self, file_url: str, tenant_id: str, job_id: str = None) -> Dict[str, Any]:
    """
    Parse an IFC file from cloud storage and extract building data.
    
    Args:
        file_url: URL to the IFC file in cloud storage
        tenant_id: Tenant identifier for multi-tenancy
        job_id: Optional job ID for tracking
    
    Returns:
        Dict containing parsing results and metadata
    """
    if not job_id:
        job_id = str(uuid.uuid4())
    
    try:
        update_job_status(job_id, JobStatus.PROCESSING, 0, "Starting IFC file download...")
        
        # Download file from cloud storage
        import boto3
        s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY
        )
        
        # Extract bucket and key from URL
        bucket_name = R2_BUCKET_NAME
        file_key = file_url.split('/')[-1]  # Simple extraction, improve as needed
        
        update_job_status(job_id, JobStatus.PROCESSING, 10, "Downloading IFC file...")
        
        # Download to temporary file
        with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as temp_file:
            s3_client.download_file(bucket_name, file_key, temp_file.name)
            ifc_path = temp_file.name
        
        update_job_status(job_id, JobStatus.PROCESSING, 30, "Converting IFC to JSON...")
        
        # Convert IFC to JSON using existing tools
        json_path = ifc_path.replace('.ifc', '.json')
        conversion_result = convert_ifc_to_json.delay(ifc_path, json_path, job_id)
        
        # Wait for conversion to complete
        conversion_result.get(timeout=1800)  # 30 minute timeout
        
        update_job_status(job_id, JobStatus.PROCESSING, 60, "Ingesting data to Neo4j...")
        
        # Ingest to Neo4j
        ingestion_result = ingest_to_neo4j.delay(json_path, tenant_id, job_id)
        ingestion_result.get(timeout=1800)  # 30 minute timeout
        
        update_job_status(job_id, JobStatus.PROCESSING, 90, "Building semantic index...")
        
        # Rebuild semantic index
        index_result = build_semantic_index.delay(job_id)
        index_result.get(timeout=600)  # 10 minute timeout
        
        # Cleanup temporary files
        os.unlink(ifc_path)
        if os.path.exists(json_path):
            os.unlink(json_path)
        
        update_job_status(job_id, JobStatus.COMPLETED, 100, "IFC processing completed successfully")
        
        return {
            "job_id": job_id,
            "status": JobStatus.COMPLETED,
            "message": "IFC file processed successfully",
            "tenant_id": tenant_id,
            "file_url": file_url
        }
        
    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, 0, f"Processing failed: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="api.tasks.convert_ifc_to_json")
def convert_ifc_to_json(self, ifc_path: str, json_path: str, job_id: str = None) -> Dict[str, Any]:
    """
    Convert IFC file to JSON format using ifc2json tools.
    
    Args:
        ifc_path: Path to input IFC file
        json_path: Path for output JSON file
        job_id: Job ID for status tracking
    
    Returns:
        Dict containing conversion results
    """
    try:
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 20, "Converting IFC to JSON...")
        
        # Use the existing ifc2json tool
        result = subprocess.run([
            sys.executable, "extras/tools/ifc2json/ifc2json.py",
            ifc_path, json_path
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            raise Exception(f"IFC conversion failed: {result.stderr}")
        
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 50, "IFC conversion completed")
        
        return {
            "success": True,
            "json_path": json_path,
            "message": "IFC converted to JSON successfully"
        }
        
    except Exception as e:
        if job_id:
            update_job_status(job_id, JobStatus.FAILED, 0, f"Conversion failed: {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(bind=True, name="api.tasks.ingest_to_neo4j")
def ingest_to_neo4j(self, json_path: str, tenant_id: str, job_id: str = None) -> Dict[str, Any]:
    """
    Ingest IFC JSON data into Neo4j database.
    
    Args:
        json_path: Path to IFC JSON file
        tenant_id: Tenant identifier
        job_id: Job ID for status tracking
    
    Returns:
        Dict containing ingestion results
    """
    try:
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 70, "Ingesting data to Neo4j...")
        
        # Use existing ingestion script
        result = subprocess.run([
            sys.executable, "ingest/ifcjson_to_neo4j.py",
            json_path, "--tenant", tenant_id
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            raise Exception(f"Neo4j ingestion failed: {result.stderr}")
        
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 85, "Neo4j ingestion completed")
        
        return {
            "success": True,
            "message": "Data ingested to Neo4j successfully",
            "tenant_id": tenant_id
        }
        
    except Exception as e:
        if job_id:
            update_job_status(job_id, JobStatus.FAILED, 0, f"Ingestion failed: {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(bind=True, name="api.tasks.build_semantic_index")
def build_semantic_index(self, job_id: str = None) -> Dict[str, Any]:
    """
    Rebuild the semantic search index from current Neo4j data.
    
    Args:
        job_id: Job ID for status tracking
    
    Returns:
        Dict containing indexing results
    """
    try:
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 95, "Building semantic index...")
        
        # Use existing index building script
        result = subprocess.run([
            sys.executable, "rag/build_index.py"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            raise Exception(f"Index building failed: {result.stderr}")
        
        if job_id:
            update_job_status(job_id, JobStatus.PROCESSING, 100, "Semantic index built successfully")
        
        return {
            "success": True,
            "message": "Semantic index built successfully"
        }
        
    except Exception as e:
        if job_id:
            update_job_status(job_id, JobStatus.FAILED, 0, f"Index building failed: {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=2)


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get current status of a job."""
    import redis
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    
    job_data = redis_client.hgetall(f"job:{job_id}")
    if not job_data:
        return None
    
    # Convert bytes to strings
    return {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in job_data.items()}
