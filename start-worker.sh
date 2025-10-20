#!/bin/bash
# Startup script for RiG CMMS workers

set -e

echo "Starting RiG CMMS workers..."

# Wait for dependencies
echo "Waiting for Redis..."
while ! redis-cli -u $REDIS_URL ping > /dev/null 2>&1; do
  echo "Redis not ready, waiting..."
  sleep 2
done
echo "Redis is ready!"

echo "Waiting for PostgreSQL..."
while ! pg_isready -d $DATABASE_URL > /dev/null 2>&1; do
  echo "PostgreSQL not ready, waiting..."
  sleep 2
done
echo "PostgreSQL is ready!"

echo "Waiting for Neo4j..."
while ! curl -f http://localhost:7474 > /dev/null 2>&1; do
  echo "Neo4j not ready, waiting..."
  sleep 2
done
echo "Neo4j is ready!"

# Start Celery worker
echo "Starting Celery worker..."
celery -A api.celery_app worker --loglevel=info --concurrency=2 --queues=ifc_processing,neo4j_ingestion,indexing
