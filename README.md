# RiG CMMS
Retrieval over ifcJSON Graphs _for AI-Native CMMS_

**🚀 Now supports large IFC files (up to 5TB) with direct uploads and background processing!**

### IFC-GraphRAG-CMMS

Goal: Load large IFC files into a property graph, power GraphRAG + LLM, and enable safe CRUD for CMMS with enterprise-grade scalability.

### Repo layout

## Architecture Overview

### New Scalable Architecture (2024)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server     │    │   Background    │
│   (Vercel)      │◄──►│   (Fly.io)       │◄──►│   Workers       │
│   React + 3D    │    │   FastAPI        │    │   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐            │
         │              │   Cloud Storage  │            │
         │              │   (R2/S3)        │            │
         │              │   Direct Uploads │            │
         │              └─────────────────┘            │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Databases     │
                    │   Neo4j + PG    │
                    │   Redis Queue   │
                    └─────────────────┘
```

### Key Improvements
- **Direct Uploads**: Files upload directly to R2, bypassing 4.5MB serverless limits
- **Background Processing**: Heavy IFC parsing moved to dedicated Celery workers
- **Scalable Storage**: Support for files up to 5TB using multipart uploads
- **Real-time Status**: Job tracking and progress updates
- **Enterprise Ready**: Production-grade deployment with monitoring

- **data/raw**: Source IFC and ifcJSON files (e.g., architectural, mechanical models).
- **ingest/**: Scripts to load and transform ifcJSON into Neo4j property graphs.
- **neo4j/**: Dockerized Neo4j database, with plugins (APOC) and persistent volumes.
- **graph/**: Cypher schema and constraints for graph structure.
- **rag/**: Retrieval-Augmented Generation (RAG) pipeline, embeddings, and FAISS index.
- **scripts/**: Utility scripts (e.g., connectivity checks).

---

## Key Libraries

- **ifcopenshell**: Reads and writes IFC files, used for merging models.
- **neo4j**: Python driver for interacting with the Neo4j graph database.
- **dotenv**: Loads environment variables from `.env` files.
- **sentence-transformers**: Generates text embeddings for semantic search.
- **faiss**: Efficient similarity search and clustering of dense vectors.
- **numpy**: Numerical operations, especially for embeddings.

---

## Main Functions & Scripts

### 1. IFC File Merging
- `data/raw/ifc/sample_hospital/merge_ifc_files.py`
	- Merges architectural and mechanical IFC files using ifcopenshell.
	- Outputs a combined IFC file for unified graph ingestion.

### 2. Ingestion to Neo4j
- `ingest/ifcjson_to_neo4j.py`
	- Loads ifcJSON, extracts entities, properties, and relationships.
	- Maps IFC types to CMMS classes, flattens property sets, and creates nodes/edges in Neo4j.
	- Handles spatial, system, and connectivity relationships.

### 3. Graph Schema
- `graph/schema.cypher`
	- Defines constraints and indexes for efficient querying in Neo4j.

### 4. RAG Pipeline
- `rag/build_index.py`
	- Fetches nodes and context from Neo4j.
	- Builds text “cards” for each node, generates embeddings, and creates a FAISS index.
- `rag/query.py`
	- Uses semantic and lexical search to find relevant nodes for a question.
	- Expands graph neighborhoods and builds evidence for LLM-based answers.
- `rag/answer.py`
	- Loads evidence and prints summary information (e.g., rooms, storeys).

### 5. Utility Scripts
- `scripts/bolt_check.py`
	- Verifies Neo4j connectivity and APOC plugin status.

---

## Example Data Flow

1. **Merge IFC files** (if needed) → `merge_ifc_files.py`
2. **Convert to ifcJSON** (external or via script)
3. **Ingest to Neo4j** → `ifcjson_to_neo4j.py`
4. **Apply schema** → `schema.cypher`
5. **Build RAG index** → `build_index.py`
6. **Query graph** → `query.py`, `answer.py`

---

## Diagram: RAG Pipeline

```
[Neo4j Graph]
		 |
		 v
[build_index.py] --(embeddings)--> [FAISS Index]
		 |
		 v
[query.py] <--- User Question
		 |
		 v
[answer.py] --(evidence)--> Output
```

---

## Explanations


---

## Quick Start (New Architecture)

### 🚀 Deploy to Production

1. **Set up Cloudflare R2**:
   ```bash
   # Create R2 bucket and get credentials
   # Add to .env file
   ```

2. **Deploy API to Fly.io**:
   ```bash
   fly launch
   fly deploy
   ```

3. **Deploy Frontend to Vercel**:
   ```bash
   # Connect GitHub repo to Vercel
   # Set VITE_API_BASE environment variable
   ```

4. **Test with large files**:
   ```bash
   python test_architecture.py
   ```

### 🏠 Local Development

```bash
# Start infrastructure
docker-compose up -d

# Start API
uvicorn api.main:app --reload

# Start workers
celery -A api.celery_app worker --loglevel=info

# Start frontend
cd ui && npm run dev
```

---

## Getting Started & Implementation Guide

### Prerequisites
- Python 3.8+
- Docker Desktop (for Neo4j)
- Install dependencies: `pip install -r requirements.txt`

### Step-by-Step Usage
1. **Set up your environment**
	- Create and activate a Python virtual environment: `python3 -m venv venv && source venv/bin/activate`
	- Install required packages: `pip install -r requirements.txt`

2. **Prepare your data**
	- Place your IFC and ifcJSON files in `data/raw/ifc/sample_hospital/`.
	- (Optional) Merge IFC files using `merge_ifc_files.py`.

3. **Start Neo4j**
	- Run: `docker compose up -d` (from the project root)
	- Access Neo4j at [http://localhost:7474](http://localhost:7474) (default user: neo4j, password: changeme123)

4. **Ingest data into Neo4j**
	- Run: `python ingest/ifcjson_to_neo4j.py data/raw/ifc/sample_hospital/SampleHospital_Arch.json --source Arch`
	- Run: `python ingest/ifcjson_to_neo4j.py data/raw/ifc/sample_hospital/SampleHospital_Mech.json --source Mech`

5. **Apply graph schema**
	- Use Neo4j browser or cypher-shell: `:play graph/schema.cypher`

6. **Build RAG index**
	- Run: `python rag/build_index.py`

7. **Query and retrieve answers**
	- Run: `python rag/query.py "Your question here"`
	- Run: `python rag/answer.py` to preview evidence

### Main Files & Their Purpose
- `data/raw/ifc/sample_hospital/merge_ifc_files.py`: Merges multiple IFC files into one.
- `ingest/ifcjson_to_neo4j.py`: Loads ifcJSON files into Neo4j, mapping entities and relationships.
- `graph/schema.cypher`: Defines graph constraints and indexes for Neo4j.
- `rag/build_index.py`: Builds semantic embeddings and FAISS index from graph data.
- `rag/query.py`: Retrieves relevant nodes for a question using semantic and lexical search.
- `rag/answer.py`: Summarizes and previews evidence from queries.
- `scripts/bolt_check.py`: Checks Neo4j connectivity and APOC plugin status.

### Directory Structure Overview
- `data/raw/`: Source IFC and ifcJSON files.
- `data/processed/`: Processed exports and graph dumps.
- `ingest/`: Data loaders and graphizers.
- `graph/`: Cypher queries and schema.
- `neo4j/`: Docker volumes and plugins.
- `rag/`: RAG pipeline scripts and index files.
- `scripts/`: Utility scripts.
- `docs/`: Documentation and diagrams.

---

For more details, see comments in each script or reach out via Issues in the repository.
