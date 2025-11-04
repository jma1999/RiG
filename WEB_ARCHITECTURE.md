# Web Development Architecture Documentation

This document provides a comprehensive overview of the RiG (Retrieval over ifcJSON Graphs) MVP architecture, explaining how the frontend, backend, and supporting services work together.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Background Processing](#background-processing)
5. [Data Storage & Databases](#data-storage--databases)
6. [Cloud Storage](#cloud-storage)
7. [Deployment & Hosting](#deployment--hosting)
8. [How It All Works Together](#how-it-all-works-together)
9. [Key Technologies & Why](#key-technologies--why)

---

## Architecture Overview

The RiG MVP is a full-stack web application with a modern microservices architecture:

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │─────▶│  Backend API │─────▶│   Neo4j     │
│  (React)    │      │  (FastAPI)   │      │  (Graph DB) │
│  (Vercel)   │      │  (Fly.io)    │      │             │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                       │
                            ▼                       │
                     ┌──────────────┐              │
                     │   Celery     │              │
                     │   Workers    │──────────────┘
                     │  (Redis)     │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Cloudflare  │
                     │      R2      │
                     │  (S3 Storage) │
                     └──────────────┘
```

---

## Frontend Architecture

### **Technology Stack**

- **React 19.1.1**: Modern UI framework with hooks and functional components
- **Vite 7.1.6**: Next-generation build tool and dev server (replaces Create React App)
- **TypeScript/JavaScript**: Type-safe development with JSX
- **Tailwind CSS 4.1.13**: Utility-first CSS framework for styling
- **Radix UI**: Headless component library for accessible UI primitives
- **React Force Graph 2D**: Graph visualization library
- **web-ifc-viewer**: 3D IFC model viewer (Three.js based)

### **Project Structure**

```
ui/
├── src/
│   ├── App.jsx                 # Root component
│   ├── FacilityOS.jsx          # Main application component
│   ├── components/
│   │   ├── DirectUploadComponent.jsx  # File upload UI
│   │   └── ui/                 # Reusable UI components (Radix-based)
│   ├── lib/
│   │   ├── env.ts             # Environment configuration
│   │   └── utils.ts            # Utility functions
│   └── styles/
│       └── palantir-theme.css  # Custom theme
├── public/
│   └── ifc/                    # Static IFC files and WASM binaries
├── vite.config.js              # Vite configuration
├── package.json                # Dependencies
└── dist/                       # Production build output
```

### **Key Files & Their Purposes**

1. **`ui/src/FacilityOS.jsx`** (1,828 lines)
   - Main application component with all views:
     - Dashboard view (metrics, activity)
     - 3D Model Viewer (IFC file visualization)
     - Graph View (Neo4j relationship visualization)
     - Assets View (facility equipment management)
     - Work Orders View (maintenance task management)
   - Contains AI Assistant component for chat interface
   - Handles routing and state management

2. **`ui/src/components/DirectUploadComponent.jsx`**
   - Handles direct multipart uploads to Cloudflare R2
   - Implements resumable upload functionality
   - Shows upload progress and job status

3. **`ui/vite.config.js`**
   - Configures Vite build tool
   - Sets up React plugin and Tailwind CSS
   - Configures path aliases (@/ for src/)

4. **`ui/src/lib/env.ts`**
   - Determines API base URL based on environment
   - Development: `http://127.0.0.1:8000`
   - Production: Uses `VITE_API_URL` environment variable

### **How the Frontend Runs**

#### **Development Mode**
```bash
cd ui
npm install          # Install dependencies
npm run dev          # Start Vite dev server (port 5173)
```

Vite provides:
- Hot Module Replacement (HMR) for instant updates
- Fast builds using esbuild
- Native ES modules in browser
- Development proxy for API calls

#### **Production Build**
```bash
npm run build        # Creates optimized bundle in dist/
```

Vite:
- Bundles all code with tree-shaking
- Minifies JavaScript/CSS
- Generates production-ready static files
- Assets are hashed for cache busting

### **Frontend Deployment (Vercel)**

**Why Vercel?**
- Zero-configuration deployment for Vite/React
- Automatic HTTPS and CDN
- Git integration (auto-deploy on push)
- Edge functions support
- Free tier for personal projects

**Deployment Process:**
1. Connect GitHub repository to Vercel
2. Set build command: `cd ui && npm run build`
3. Set output directory: `ui/dist`
4. Configure environment variable: `VITE_API_URL` (your Fly.io API URL)
5. Vercel automatically deploys on every push to `main`

**Vercel Configuration:**
- Builds the React app as static files
- Serves them via global CDN
- Handles routing (SPA mode)
- No server-side rendering needed (pure client-side app)

---

## Backend Architecture

### **Technology Stack**

- **FastAPI 0.95.0+**: Modern Python web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Python 3.11+**: Backend programming language
- **Pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management

### **Project Structure**

```
api/
├── main.py              # Main FastAPI application (938 lines)
├── chat.py              # AI chat endpoint with Groq integration
├── celery_app.py        # Celery configuration for background tasks
├── tasks.py             # Background job definitions
├── cloud_storage.py     # Cloudflare R2 upload/download operations
└── celery_app.py        # Celery worker configuration
```

### **Key Files & Their Purposes**

1. **`api/main.py`** (938 lines)
   - Main FastAPI application
   - Defines all REST API endpoints:
     - `/search` - Semantic search in Neo4j graph
     - `/count` - Count entities by type
     - `/asset/{id}` - Get asset details
     - `/workorders` - CRUD for work orders
     - `/upload/session` - Create multipart upload session
     - `/jobs/{job_id}` - Get job status
     - `/health` - Health check endpoint
   - Sets up CORS middleware for cross-origin requests
   - Mounts static files at `/app` route
   - Manages lazy loading of FAISS index and embedding model

2. **`api/chat.py`**
   - AI chat endpoint using Groq LLM (Llama 3 70B)
   - Integrates with graph search tools
   - Converts natural language to graph queries

3. **`api/cloud_storage.py`**
   - Manages multipart uploads to Cloudflare R2
   - Generates presigned URLs for direct client uploads
   - Handles upload completion and file metadata

4. **`api/celery_app.py`**
   - Configures Celery worker infrastructure
   - Sets up Redis as message broker
   - Defines task queues and routing

### **How the Backend Runs**

#### **Development Mode**
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Uvicorn** is the ASGI server that:
- Runs FastAPI application
- Handles HTTP requests
- Manages WebSocket connections
- Provides hot-reload in development (`--reload` flag)

#### **Production Mode**
```bash
# Using Docker
docker build -t rig-api .
docker run -p 8000:8000 rig-api

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Production Considerations:**
- Use multiple workers for concurrency (`--workers 4`)
- Set up proper logging
- Configure reverse proxy (nginx/traefik)
- Use environment variables for secrets

### **Backend Deployment (Fly.io)**

**Why Fly.io?**
- Supports long-running processes (unlike serverless)
- Docker-based deployment
- Global edge network
- Persistent volumes for data storage
- Easy scaling
- Free tier available

**Deployment Configuration (`fly.toml`):**
```toml
app = "rig-cmms-api"
primary_region = "sjc"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  min_machines_running = 1

[machine]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 2048

[[mounts]]
  source = "rig_data"
  destination = "/app/data"
```

**Deployment Process:**
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly deploy
```

**How It Works:**
1. Fly.io builds Docker image from `Dockerfile`
2. Runs container with environment variables
3. Routes traffic from `https://rig-cmms-api.fly.dev` to port 8000
4. Maintains persistent volume for FAISS indices at `/app/data`

**Dockerfile Configuration:**
- Uses Python 3.11-slim base image
- Installs system dependencies (libmagic for file type detection)
- Copies requirements and installs Python packages
- Sets up non-root user for security
- Exposes port 8000
- Runs `uvicorn api.main:app --host 0.0.0.0 --port 8000`

---

## Background Processing

### **Technology Stack**

- **Celery 5.3.0+**: Distributed task queue framework
- **Redis 7-alpine**: Message broker and result backend
- **Flower**: Celery monitoring dashboard

### **How Celery Works**

Celery uses a distributed architecture:

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   FastAPI   │─────▶│    Redis    │─────▶│   Celery     │
│   (API)     │      │  (Broker)   │      │   Workers    │
└─────────────┘      └─────────────┘      └──────────────┘
     │                      │                      │
     │                      │                      │
     └──────────────────────┴──────────────────────┘
                            │
                     (Task Queue)
```

### **Task Definitions (`api/tasks.py`)**

1. **`parse_ifc_file`**: Downloads IFC file from R2, converts to ifcJSON
2. **`convert_ifc_to_json`**: Uses ifcopenshell to parse IFC files
3. **`ingest_to_neo4j`**: Loads ifcJSON data into Neo4j graph database
4. **`build_semantic_index`**: Rebuilds FAISS index for semantic search

### **Celery Configuration (`api/celery_app.py`)**

```python
celery_app = Celery(
    "rig_workers",
    broker=REDIS_URL,        # Redis as message broker
    backend=REDIS_URL,      # Redis for results
    include=["api.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    task_time_limit=3600,   # 1 hour max per task
    worker_prefetch_multiplier=1,
)
```

### **Task Queues**

Different queues for different workloads:
- `ifc_processing`: Heavy IFC parsing tasks
- `neo4j_ingestion`: Database insertion tasks
- `indexing`: FAISS index building tasks

### **How It Runs**

#### **Local Development**
```bash
# Start Redis
docker-compose up -d redis

# Start Celery worker
celery -A api.celery_app worker --loglevel=info

# Start Flower (monitoring UI)
celery -A api.celery_app flower --port=5555
```

#### **Production (Docker Compose)**
```yaml
celery-worker:
  build: .
  command: celery -A api.celery_app worker --loglevel=info --concurrency=2
  environment:
    - REDIS_URL=redis://redis:6379/0
    - NEO4J_URI=bolt://neo4j:7687
  depends_on:
    - redis
    - neo4j
```

### **Job Tracking**

Jobs are tracked in Redis with status:
- `pending`: Queued but not started
- `processing`: Currently running
- `completed`: Finished successfully
- `failed`: Error occurred
- `cancelled`: User cancelled

**Status Updates:**
- Workers update status in Redis during execution
- Frontend polls `/jobs/{job_id}` endpoint
- Real-time updates via status polling

---

## Data Storage & Databases

### **Neo4j Graph Database**

**Purpose:** Stores facility data as a graph with relationships

**Why Neo4j?**
- Native graph database optimized for relationship queries
- Cypher query language is intuitive for graph operations
- Handles complex multi-hop traversals efficiently
- Perfect for IFC building data (spaces, relationships, hierarchies)

**Configuration:**
```yaml
neo4j:
  image: neo4j:5.22-community
  ports:
    - "7474:7474"  # Browser UI
    - "7687:7687"  # Bolt protocol
  environment:
    - NEO4J_AUTH=neo4j/changeme123
    - NEO4J_PLUGINS=["apoc"]
```

**Data Model:**
- Nodes: `IfcEntity` (walls, doors, spaces, etc.)
- Relationships: `CONTAINS`, `IN_STOREY`, `CONNECTED_TO`, `FEEDS`
- Properties: `globalId`, `name`, `type`, `labels`, coordinates

**Usage in Code:**
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    NEO4J_URI, 
    auth=(NEO4J_USER, NEO4J_PASS)
)

# Query example
MATCH (n:IfcEntity {globalId:$id})
OPTIONAL MATCH (n)-[:IN_STOREY]->(st:IfcBuildingStorey)
RETURN n, st
```

### **PostgreSQL**

**Purpose:** Job tracking and metadata storage

**Why PostgreSQL?**
- Reliable relational database
- ACID compliance for job status
- JSON support for flexible metadata
- Standard SQL queries

**Configuration:**
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=rig
    - POSTGRES_USER=rig_user
    - POSTGRES_PASSWORD=rig_password
```

**Usage:**
- Job status tracking
- Work order metadata
- User sessions (future)

### **FAISS Index**

**Purpose:** Vector similarity search for semantic queries

**What is FAISS?**
- Facebook AI Similarity Search library
- Efficient vector database for embeddings
- Enables fast semantic search over graph data

**How It Works:**
1. Text from Neo4j entities is embedded using `sentence-transformers`
2. Embeddings stored in FAISS index
3. Query text is embedded
4. FAISS finds similar entities via vector similarity
5. Results mapped back to Neo4j IDs

**Files:**
- `data/processed/rag/index.faiss` - Binary FAISS index
- `data/processed/rag/meta.json` - ID mapping and metadata

**Embedding Model:**
- Default: `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional vectors
- Fast and accurate for semantic search

---

## Cloud Storage

### **Cloudflare R2**

**Purpose:** Store large IFC files (up to 5TB per file)

**Why Cloudflare R2?**
- S3-compatible API
- No egress fees (unlike AWS S3)
- Supports multipart uploads
- Direct client uploads via presigned URLs
- Cost-effective for large files

### **Direct Upload Architecture**

Traditional approach (problematic):
```
Client → Backend → Storage
(File must go through serverless, limited to 4.5MB-50MB)
```

Direct upload approach (solution):
```
Client → R2 Storage
(Backend only generates presigned URLs, no file transfer)
```

### **Multipart Uploads**

For files > 5MB, use multipart upload:

1. **Create Session** (`POST /upload/session`)
   - Backend generates upload session ID
   - Returns presigned URLs for each part

2. **Upload Parts** (Client-side)
   - Client uploads parts directly to R2
   - Each part 5MB+ in size
   - Up to 10,000 parts (supports 50GB+ files)

3. **Complete Upload** (`POST /upload/complete/{upload_id}`)
   - Backend assembles parts into final file
   - Starts background processing job

**Implementation (`api/cloud_storage.py`):**
```python
class CloudStorageService:
    def create_multipart_upload_session(self, file_name, content_type):
        # Generate unique key
        file_key = f"ifc-files/{uuid.uuid4()}-{file_name}"
        
        # Create multipart upload
        upload = self.s3_client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=file_key,
            ContentType=content_type
        )
        
        return {
            "upload_id": upload["UploadId"],
            "file_key": file_key,
            "presigned_urls": [...]  # For each part
        }
```

### **File Processing Flow**

```
1. User uploads IFC file → Direct to R2
2. Backend queues Celery task → parse_ifc_file.delay(url)
3. Worker downloads from R2 → Converts to ifcJSON
4. Worker ingests to Neo4j → Updates graph
5. Worker builds FAISS index → Updates search
6. Frontend polls job status → Shows completion
```

---

## Deployment & Hosting

### **Frontend: Vercel**

**URL Structure:**
- Production: `https://your-app.vercel.app`
- Preview: `https://your-app-git-branch.vercel.app`

**Build Process:**
1. Vercel detects push to `main` branch
2. Installs dependencies: `cd ui && npm ci`
3. Builds app: `npm run build`
4. Deploys `ui/dist` folder as static site
5. Serves via global CDN

**Environment Variables:**
- `VITE_API_URL`: Backend API URL (https://rig-cmms-api.fly.dev)

### **Backend: Fly.io**

**URL Structure:**
- Production: `https://rig-cmms-api.fly.dev`
- Health Check: `https://rig-cmms-api.fly.dev/health`

**Deployment Process:**
1. Fly.io builds Docker image from `Dockerfile`
2. Pushes image to Fly.io registry
3. Deploys container to selected region (SJC)
4. Routes traffic via Fly.io edge network
5. Maintains persistent volume for `/app/data`

**Auto-scaling:**
- `min_machines_running = 1`: Always 1 instance active
- `auto_stop_machines = false`: Never sleep
- Can scale horizontally for higher load

### **Infrastructure: Docker Compose (Local)**

**Services:**
- `neo4j`: Graph database (ports 7474, 7687)
- `redis`: Message broker (port 6379)
- `postgres`: Relational database (port 5432)
- `celery-worker`: Background task processor
- `celery-flower`: Task monitoring UI (port 5555)

**Start Commands:**
```bash
docker-compose up -d              # Start all services
docker-compose logs -f celery-worker  # View logs
docker-compose down                # Stop all services
```

---

## How It All Works Together

### **Complete Request Flow**

#### **1. User Searches for an Asset**

```
User types "show me all doors" in AI Assistant
    │
    ▼
Frontend (React)
    │
    ├─▶ POST /chat {message: "show me all doors"}
    │
    ▼
Backend (FastAPI)
    │
    ├─▶ Chat handler detects "doors" keyword
    ├─▶ Calls semantic_search("doors")
    │   │
    │   ├─▶ Loads FAISS index (lazy-loaded)
    │   ├─▶ Embeds query text
    │   ├─▶ Searches FAISS for similar vectors
    │   └─▶ Gets top 10 matching entity IDs
    │
    ├─▶ Queries Neo4j for entity details
    │   │
    │   └─▶ MATCH (n:IfcEntity {globalId:$id})
    │       OPTIONAL MATCH (n)-[:IN_STOREY]->(st)
    │       RETURN n, st
    │
    ├─▶ Builds subgraph with relationships
    │
    └─▶ Returns to frontend:
        {
          reply: "I found 5 doors...",
          tool: {
            action: "search",
            hits: [...],
            subgraphs: [...]
          }
        }
    │
    ▼
Frontend (React)
    │
    ├─▶ Updates chat UI with AI response
    ├─▶ Navigates to Graph View
    └─▶ Renders graph with ForceGraph2D
```

#### **2. User Uploads Large IFC File**

```
User clicks "Upload IFC" button
    │
    ▼
Frontend (DirectUploadComponent)
    │
    ├─▶ POST /upload/session
    │   {file_name, file_size, content_type}
    │
    ▼
Backend (FastAPI)
    │
    ├─▶ Creates multipart upload session in R2
    ├─▶ Generates presigned URLs for each part
    └─▶ Returns:
        {
          upload_id: "...",
          file_key: "...",
          presigned_urls: [...]
        }
    │
    ▼
Frontend (DirectUploadComponent)
    │
    ├─▶ Splits file into 5MB+ chunks
    ├─▶ Uploads each chunk directly to R2
    │   (bypasses backend, uses presigned URLs)
    │
    ├─▶ POST /upload/complete/{upload_id}
    │   {parts: [{ETag, PartNumber}]}
    │
    ▼
Backend (FastAPI)
    │
    ├─▶ Completes multipart upload in R2
    ├─▶ Queues Celery task:
    │   parse_ifc_file.delay(file_url, tenant_id, job_id)
    │
    └─▶ Returns: {job_id: "...", status: "pending"}
    │
    ▼
Redis (Message Broker)
    │
    └─▶ Task queued in "ifc_processing" queue
    │
    ▼
Celery Worker
    │
    ├─▶ Receives task from Redis
    ├─▶ Updates job status: "processing"
    │
    ├─▶ Downloads file from R2
    ├─▶ Converts IFC → ifcJSON (ifcopenshell)
    ├─▶ Ingests ifcJSON → Neo4j (via ingest script)
    ├─▶ Builds FAISS index (updates)
    │
    └─▶ Updates job status: "completed"
    │
    ▼
Frontend (Polling)
    │
    ├─▶ Polls GET /jobs/{job_id} every 2 seconds
    ├─▶ Shows progress bar
    └─▶ On completion: Shows success message
```

### **Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   React App  │  │ AI Assistant │  │ 3D Viewer    │     │
│  │  (Vercel)    │  │   (Chat UI)  │  │(web-ifc)     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │ HTTP/REST API    │                  │
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────┐
│                    BACKEND API (Fly.io)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │   Chat API   │  │ Upload API    │     │
│  │   (Uvicorn)  │  │  (Groq LLM)  │  │ (R2 Presign)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │                  │                  │
┌─────────▼──────────┐  ┌────▼──────┐  ┌───────▼──────────┐
│      Neo4j         │  │   Redis    │  │  Cloudflare R2  │
│   (Graph DB)       │  │  (Broker) │  │  (File Storage) │
│                    │  └─────┬─────┘  └─────────────────┘
│  ┌──────────────┐ │        │
│  │ FAISS Index  │ │        │
│  │ (In Memory)  │ │        │
│  └──────────────┘ │        │
└────────────────────┘        │
                              ▼
                      ┌──────────────┐
                      │ Celery Worker│
                      │              │
                      │  - Parse IFC │
                      │  - Ingest    │
                      │  - Index     │
                      └──────────────┘
```

---

## Key Technologies & Why

### **Frontend Technologies**

#### **React**
- **Why:** Industry standard, large ecosystem, component reusability
- **What it does:** Manages UI state and rendering
- **Key features:** Hooks, functional components, virtual DOM

#### **Vite**
- **Why:** Much faster than Webpack, better DX, native ES modules
- **What it does:** Builds and bundles JavaScript/CSS
- **Key features:** Hot Module Replacement, tree-shaking, fast builds

#### **Tailwind CSS**
- **Why:** Rapid styling without writing custom CSS
- **What it does:** Utility-first CSS framework
- **Key features:** Responsive design, dark mode, custom theme support

#### **Radix UI**
- **Why:** Accessible, unstyled components
- **What it does:** Provides headless UI primitives
- **Key features:** Keyboard navigation, ARIA attributes, no styling opinions

### **Backend Technologies**

#### **FastAPI**
- **Why:** Modern, fast, async support, automatic API docs
- **What it does:** Web framework for building REST APIs
- **Key features:** Type hints, Pydantic validation, OpenAPI/Swagger docs

#### **Uvicorn**
- **Why:** Fast ASGI server, supports async/await
- **What it does:** Runs FastAPI application
- **Key features:** WebSocket support, multiple workers, production-ready

#### **Celery**
- **Why:** Industry standard for background tasks, reliable
- **What it does:** Distributed task queue
- **Key features:** Retry logic, scheduling, monitoring, scaling

#### **Redis**
- **Why:** Fast, in-memory, perfect for message queues
- **What it does:** Message broker and result backend for Celery
- **Key features:** Pub/sub, caching, job status storage

### **Database Technologies**

#### **Neo4j**
- **Why:** Native graph database optimized for relationships
- **What it does:** Stores facility data as graph
- **Key features:** Cypher query language, ACID transactions, graph algorithms

#### **PostgreSQL**
- **Why:** Reliable, ACID compliant, JSON support
- **What it does:** Stores job metadata and work orders
- **Key features:** Transactions, joins, JSONB queries

#### **FAISS**
- **Why:** Fastest vector similarity search library
- **What it does:** Enables semantic search over graph data
- **Key features:** GPU support, approximate search, efficient indexing

### **Infrastructure Technologies**

#### **Docker**
- **Why:** Consistent environments, easy deployment
- **What it does:** Containerizes applications
- **Key features:** Isolation, reproducibility, portability

#### **Fly.io**
- **Why:** Supports long-running processes, persistent volumes
- **What it does:** Hosts backend API and workers
- **Key features:** Global edge network, auto-scaling, easy CLI

#### **Vercel**
- **Why:** Zero-config deployment, excellent DX
- **What it does:** Hosts frontend static site
- **Key features:** CDN, automatic HTTPS, preview deployments

#### **Cloudflare R2**
- **Why:** No egress fees, S3-compatible
- **What it does:** Stores large IFC files
- **Key features:** Multipart uploads, presigned URLs, cost-effective

---

## Environment Variables

### **Backend (Fly.io)**

```bash
# Database
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme123
NEO4J_DATABASE=neo4j

# Redis
REDIS_URL=redis://redis:6379/0

# PostgreSQL
DATABASE_URL=postgresql://rig_user:rig_password@postgres:5432/rig

# Cloud Storage
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET_NAME=rig-ifc-files
R2_ENDPOINT_URL=https://your-account.r2.cloudflarestorage.com

# AI
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama3-70b-8192

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# CORS
FRONTEND_ORIGINS=https://your-app.vercel.app
```

### **Frontend (Vercel)**

```bash
VITE_API_URL=https://rig-cmms-api.fly.dev
```

---

## Development Workflow

### **Local Setup**

1. **Start Infrastructure:**
   ```bash
   docker-compose up -d neo4j redis postgres
   ```

2. **Start Backend:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn api.main:app --reload
   ```

3. **Start Workers:**
   ```bash
   celery -A api.celery_app worker --loglevel=info
   ```

4. **Start Frontend:**
   ```bash
   cd ui
   npm install
   npm run dev
   ```

### **Deployment Workflow**

1. **Push to GitHub:**
   ```bash
   git push origin main
   ```

2. **GitHub Actions:**
   - Runs tests
   - Deploys API to Fly.io
   - Builds and deploys frontend to Vercel

3. **Automatic:**
   - CI/CD pipeline handles everything
   - No manual deployment steps needed

---

## Summary

The RiG MVP uses a modern, scalable architecture:

- **Frontend:** React + Vite, deployed on Vercel (static CDN)
- **Backend:** FastAPI + Uvicorn, deployed on Fly.io (containerized)
- **Processing:** Celery + Redis for background jobs
- **Storage:** Neo4j (graph), PostgreSQL (relational), R2 (files), FAISS (vectors)
- **AI:** Groq LLM for natural language interaction
- **Infrastructure:** Docker for local dev, Fly.io/Vercel for production

This architecture supports:
- Large file uploads (direct to R2)
- Real-time semantic search (FAISS + Neo4j)
- Background processing (Celery workers)
- Scalable deployment (horizontal scaling)
- Modern developer experience (fast builds, hot reload)

The system is designed to handle production workloads while maintaining development simplicity.


