# RiG CMMS - Large IFC File Processing Architecture

This repository contains a CMMS (Computerized Maintenance Management System) prototype designed to handle large IFC files without crashing. The architecture has been redesigned to support multi-hundred-MB IFC ingestion and parsing.

## Architecture Overview

The system uses a microservices architecture with the following components:

### Frontend (Vercel)
- React-based UI with direct upload capabilities
- Real-time job status polling
- 3D IFC model viewer using web-ifc-viewer

### Backend API (Fly.io/Render)
- FastAPI application running on long-running hosts
- Handles pre-signed URL generation for direct uploads
- Manages job status and metadata
- Serves processed data to frontend

### Background Workers (Celery + Redis)
- Celery workers for heavy IFC processing tasks
- Redis for job queue and status tracking
- Handles IFC parsing, conversion, and Neo4j ingestion

### Cloud Storage (Cloudflare R2)
- Direct multipart uploads bypassing serverless limits
- Resumable uploads for unreliable networks
- Up to 5TB per object support

### Database (PostgreSQL + Neo4j)
- PostgreSQL for job tracking and metadata
- Neo4j for graph-based facility data
- Semantic search with FAISS indexing

## Key Features

### Large File Support
- **Direct Uploads**: Files upload directly to R2, bypassing 4.5MB serverless limits
- **Multipart Uploads**: Support for files up to 5TB using 5MB+ chunks
- **Resumable Uploads**: Network interruption recovery using tus protocol
- **Background Processing**: Heavy parsing moved to dedicated workers

### Scalability
- **Horizontal Scaling**: Multiple Celery workers can process files in parallel
- **Queue Management**: Separate queues for different processing stages
- **Resource Limits**: Configurable memory and CPU limits per worker
- **Auto-scaling**: Workers can scale based on queue depth

### Reliability
- **Job Tracking**: Real-time status updates for all processing jobs
- **Error Handling**: Comprehensive error recovery and retry mechanisms
- **Health Checks**: Monitoring for all service components
- **Graceful Degradation**: Fallback responses when services are unavailable

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Cloudflare R2 account (or AWS S3)
- PostgreSQL database
- Redis instance

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd RiG
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Start infrastructure**:
   ```bash
   docker-compose up -d neo4j redis postgres
   ```

3. **Install Python dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Start the API**:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Start Celery workers**:
   ```bash
   celery -A api.celery_app worker --loglevel=info
   ```

6. **Start frontend**:
   ```bash
   cd ui
   npm install
   npm run dev
   ```

### Production Deployment

#### Fly.io (Recommended)

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Deploy API**:
   ```bash
   fly launch
   fly deploy
   ```

3. **Deploy workers**:
   ```bash
   fly deploy --config fly-worker.toml
   ```

#### Vercel (Frontend)

1. **Connect repository** to Vercel
2. **Set environment variables**:
   - `VITE_API_BASE`: Your Fly.io API URL
3. **Deploy**: Automatic on push to main branch

## Configuration

### Environment Variables

#### Required
- `R2_ACCESS_KEY`: Cloudflare R2 access key
- `R2_SECRET_KEY`: Cloudflare R2 secret key
- `R2_BUCKET_NAME`: R2 bucket name
- `R2_ENDPOINT_URL`: R2 endpoint URL
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `NEO4J_URI`: Neo4j connection string

#### Optional
- `MAX_FILE_SIZE`: Maximum file size (default: 1GB)
- `MIN_PART_SIZE`: Minimum multipart size (default: 5MB)
- `GROQ_API_KEY`: For AI chat functionality
- `SENTRY_DSN`: Error tracking

### File Size Limits

| Component | Limit | Notes |
|-----------|-------|-------|
| Vercel Functions | 4.5MB | Bypassed with direct uploads |
| R2 Multipart | 5TB | 5MB minimum part size |
| Celery Workers | Configurable | Memory/CPU limits per worker |
| Processing Time | 1 hour | Configurable task timeout |

## API Endpoints

### Upload Management
- `POST /upload/session` - Create multipart upload session
- `POST /upload/part/{upload_id}/{part_number}` - Get presigned URL for part
- `POST /upload/complete/{upload_id}` - Complete upload and start processing
- `DELETE /upload/abort/{upload_id}` - Abort upload

### Job Management
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs` - List jobs
- `DELETE /jobs/{job_id}` - Cancel job

### Data Access
- `GET /search` - Semantic search
- `GET /asset/{id}` - Asset details
- `GET /count` - Count entities
- `POST /chat` - AI chat with context

## Monitoring

### Health Checks
- API: `GET /health`
- Celery Flower: `http://localhost:5555`
- Redis: `redis-cli ping`
- PostgreSQL: `pg_isready`

### Logs
- API logs: `fly logs -a rig-cmms-api`
- Worker logs: `fly logs -a rig-cmms-workers`
- Frontend logs: Vercel dashboard

## Troubleshooting

### Common Issues

1. **Upload fails with 413 error**:
   - Ensure using direct uploads, not proxying through API
   - Check file size limits in configuration

2. **Processing jobs timeout**:
   - Increase worker memory allocation
   - Check Neo4j connection and performance
   - Verify IFC file is valid

3. **Frontend can't connect to API**:
   - Check CORS configuration
   - Verify API_BASE environment variable
   - Ensure API is running and accessible

### Performance Optimization

1. **Worker Scaling**:
   ```bash
   # Scale workers based on queue depth
   celery -A api.celery_app worker --concurrency=4
   ```

2. **Database Optimization**:
   - Add indexes for frequently queried fields
   - Optimize Neo4j queries
   - Use connection pooling

3. **Storage Optimization**:
   - Enable R2 lifecycle policies
   - Compress IFC files before upload
   - Use CDN for static assets

## Security Considerations

- **Authentication**: Implement JWT-based auth for production
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: Encrypt sensitive data at rest
- **Network Security**: Use HTTPS everywhere
- **Input Validation**: Validate all file uploads
- **Rate Limiting**: Implement API rate limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
