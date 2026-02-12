# IFC-LD RDF Pipeline - Implementation Guide

## Overview

This document describes the new IFC-LD RDF pipeline that replaces the previous Neo4j-based LPG approach. The pipeline converts IFC-SPF files to RDF graphs, validates them with SHACL, and enables SPARQL-based GraphRAG.

## Architecture

```
IFC-SPF → MVD Reduction → IFC-LD Converter (default) or IFCtoRDF → Turtle → GraphDB → SHACL Validation → JSON-LD → GraphRAG (SPARQL + LLM)
```

- **IFC-LD converter**: Uses [devonsparks/ifcld-service](https://github.com/devonsparks/ifcld-service) for native IFC-LD output (default).
- **NL-to-SPARQL**: Uses OpenAI LLM when `OPENAI_API_KEY` is set; falls back to keyword heuristics otherwise.
- **Graph traversal**: Neighborhood expansion with ranking (hop distance, connectivity, keyword match).

## Components

### 1. MVD Schema Reduction (`ingest/mvd_reduction.py`)

**Purpose**: Reduce IFC file size by applying Facility Management MVD rules.

**Usage**:
```bash
python ingest/mvd_reduction.py input.ifc output_reduced.ifc
```

**Features**:
- Filters entities based on Facility Management MVD requirements
- Keeps essential spatial structure, building elements, and distribution systems
- Reduces file size for faster RDF conversion

### 2. IFC to RDF Conversion (IFC-LD or IFCtoRDF)

**Default: IFC-LD converter** (`ingest/ifc_to_rdf_ifcld.py`)

Uses the [ifcld-service](https://github.com/devonsparks/ifcld-service) HTTP API for native IFC-LD output.

**Prerequisites**:
```bash
# Start IFC-LD service via Docker
docker compose --profile ifcld up -d ifcld-service
# Or: docker build -f Dockerfile.ifcld . && docker run -d -p 5000:5000 <image>
```

**Usage** (via pipeline):
```bash
python ingest/ifc_to_rdf_pipeline.py input.ifc --output-dir data/processed/rdf --converter ifcld
```

**Alternative: IFCtoRDF** (`ingest/ifc_to_rdf.py`) – Peter Pauwels ifcOWL converter

```bash
python ingest/ifc_to_rdf_pipeline.py input.ifc --converter ifctordf
# Requires Java JDK 8+ and IFCtoRDF JAR
```

### 3. GraphDB Client (`ingest/graphdb_client.py`)

**Purpose**: Manage GraphDB repositories and load Turtle files.

**Usage**:
```bash
# Create repository
python ingest/graphdb_client.py create --repository rig-facility-mgmt

# Load Turtle file
python ingest/graphdb_client.py load file.ttl --repository rig-facility-mgmt

# Export as JSON-LD
python ingest/graphdb_client.py export output.jsonld --repository rig-facility-mgmt

# Execute SPARQL query
python ingest/graphdb_client.py query "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
```

**Features**:
- Repository management (create, delete, list)
- Load Turtle files into repositories
- Execute SPARQL queries
- Export as JSON-LD

### 4. SHACL Validation (`ingest/shacl_validation.py`)

**Purpose**: Validate RDF graphs against SHACL shapes for IFC-LD compliance.

**Usage**:
```bash
python ingest/shacl_validation.py data.ttl ingest/ifc2x3.ttl --output validation_results.json
```

**Features**:
- Validates RDF graphs against IFC2x3 SHACL schema
- Reports constraint violations
- Supports RDFS and OWL inference

### 5. Complete Pipeline (`ingest/ifc_to_rdf_pipeline.py`)

**Purpose**: Orchestrate the complete IFC to RDF pipeline.

**Usage**:
```bash
python ingest/ifc_to_rdf_pipeline.py input.ifc \
    --output-dir data/processed/rdf/ \
    --base-uri https://example.com/ifc/ \
    --graphdb-repo rig-facility-mgmt \
    --export-jsonld
```

**Steps**:
1. MVD schema reduction (optional)
2. IFC to RDF (Turtle) conversion
3. GraphDB ingestion
4. SHACL validation
5. JSON-LD export (optional)

### 6. SPARQL GraphRAG (`rag/sparql_rag.py`)

**Purpose**: GraphRAG using SPARQL queries with LLM-based NL-to-SPARQL and neighborhood expansion ranking.

**Usage**:
```bash
# With OpenAI (set OPENAI_API_KEY for LLM-based SPARQL generation)
python rag/sparql_rag.py "show me all doors" --repository rig-facility-mgmt --top-k 20

# Heuristics only (no API key needed)
python rag/sparql_rag.py "how many doors are in the building?" --no-llm --output evidence.json
```

**Features**:
- **LLM-based NL-to-SPARQL**: Uses OpenAI GPT-4o-mini when `OPENAI_API_KEY` is set
- **Heuristics fallback**: Keyword-based patterns when LLM unavailable
- **Neighborhood expansion ranking**: Ranks nodes by hop distance, connectivity, and keyword match
- Evidence building for LLM context

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Ensure Java JDK 8+ is installed for IFCtoRDF.

### 2. Set Up GraphDB Desktop

1. Download and install GraphDB Desktop
2. Launch GraphDB Desktop
3. Open browser to `http://localhost:7200`
4. Create repository: `rig-facility-mgmt`
   - See `GRAPHDB_SETUP.md` for detailed instructions

### 3. Run Complete Pipeline

```bash
# Run complete pipeline
python ingest/ifc_to_rdf_pipeline.py data/raw/ifc/sample_house/20210125Prova.ifc \
    --output-dir data/processed/rdf/ \
    --base-uri https://example.com/ifc/ \
    --graphdb-repo rig-facility-mgmt \
    --export-jsonld

# Test SPARQL GraphRAG
python rag/sparql_rag.py "how many doors are in the building?" \
    --repository rig-facility-mgmt
```

## Configuration

### Environment Variables

```bash
# GraphDB
GRAPHDB_URL=http://localhost:7200
GRAPHDB_REPOSITORY=rig-facility-mgmt
GRAPHDB_USERNAME=  # Optional
GRAPHDB_PASSWORD=  # Optional

# IFC-LD converter (default)
IFCLD_SERVICE_URL=http://localhost:5000

# OpenAI for NL-to-SPARQL (optional; falls back to heuristics if unset)
OPENAI_API_KEY=
OPENAI_NL2SPARQL_MODEL=gpt-4o-mini

# IFCtoRDF (when --converter ifctordf)
IFCTORDF_JAR_PATH=  # Optional, auto-downloads if not set
JAVA_MEMORY=8g  # Java heap memory

# Base URI for RDF
BASE_URI=https://example.com/ifc/
```

## File Structure

```
data/
├── raw/
│   └── ifc/
│       └── sample_house/
│           └── 20210125Prova.ifc
└── processed/
    └── rdf/
        ├── 20210125Prova_reduced.ifc  # MVD-reduced IFC
        ├── 20210125Prova.ttl          # RDF Turtle
        └── 20210125Prova.jsonld        # JSON-LD export

ingest/
├── mvd_reduction.py          # MVD schema reduction
├── ifc_to_rdf.py             # IFC to RDF conversion
├── graphdb_client.py          # GraphDB client
├── shacl_validation.py       # SHACL validation
├── ifc_to_rdf_pipeline.py    # Complete pipeline
├── ifc2x3.ttl                # SHACL shapes
└── IFC2x3.pdf                # MVD specification

tools/
└── ifctordf/
    └── IFCtoRDF-0.4-SNAPSHOT-shaded.jar  # Auto-downloaded
```

## Next Steps

### 1. API Integration

Update `api/main.py` and `api/chat.py` to use SPARQL instead of Cypher:
- Replace Neo4j client with GraphDB client
- Replace Cypher queries with SPARQL queries
- Update semantic search to use SPARQL

### 2. Frontend Updates

Update `ui/src/FacilityOS.jsx`:
- Replace Neo4j graph visualization with RDF graph visualization
- Update API calls to use SPARQL endpoints
- Add AI-native work order creation workflow

### 3. Telemetry Integration

Design 223P schema integration:
- Map telemetry data to RDF
- Integrate with GraphDB
- Enable telemetry queries via SPARQL

### 4. Remove Deprecated Code

After migration is complete:
- Remove Neo4j-related files
- Remove Cypher-based GraphRAG
- Update documentation

## Troubleshooting

### IFCtoRDF JAR Download Fails

**Solution**: Manually download from:
- https://github.com/pipauwel/IFCtoRDF/releases
- Place in `tools/ifctordf/IFCtoRDF-0.4-SNAPSHOT-shaded.jar`

### Java Not Found

**Solution**: Install Java JDK 8+:
- macOS: `brew install openjdk@11`
- Linux: `sudo apt-get install openjdk-11-jdk`
- Windows: Download from Oracle or AdoptOpenJDK

### GraphDB Connection Refused

**Solution**: 
1. Ensure GraphDB Desktop is running
2. Check URL: `http://localhost:7200`
3. Verify repository exists

### SHACL Validation Errors

**Solution**:
1. Check SHACL shapes file: `ingest/ifc2x3.ttl`
2. Verify RDF graph uses correct IFC-LD namespaces
3. Check validation output for specific violations

## Resources

- **IFCtoRDF**: https://github.com/pipauwel/IFCtoRDF
- **GraphDB**: https://www.ontotext.com/products/graphdb/
- **SHACL**: https://www.w3.org/TR/shacl/
- **IFC-LD**: https://ifc-ld.org/
- **SPARQL**: https://www.w3.org/TR/sparql11-query/

