# GraphDB Desktop Setup Guide

This guide walks you through setting up GraphDB Desktop for the RiG Facility Management system.

## What is GraphDB?

GraphDB is a semantic graph database (RDF triplestore) that stores and queries RDF data using SPARQL. It's the replacement for Neo4j in our new RDF-based architecture.

## Installation

1. **Download GraphDB Desktop**
   - Visit: https://www.ontotext.com/products/graphdb/graphdb-free/
   - Download GraphDB Desktop (Free edition is sufficient)
   - Install following the platform-specific instructions

2. **Launch GraphDB Desktop**
   - Open the GraphDB Desktop application
   - It will start a local GraphDB server on `http://localhost:7200`

## Creating a Repository via GUI

### Step 1: Open GraphDB Workbench

1. Once GraphDB Desktop is running, open your web browser
2. Navigate to: `http://localhost:7200`
3. You should see the GraphDB Workbench interface

### Step 2: Create a New Repository

1. **Click "Setup"** in the left sidebar
2. **Click "Repositories"** tab
3. **Click "Create new repository"** button (top right)
4. Fill in the repository details:
   - **Repository ID**: `rig-facility-mgmt` (or your preferred name)
   - **Repository title**: `RiG Facility Management`
   - **Repository type**: Select `Free` (for GraphDB Free)
   - **Ruleset**: Select `empty` (no inference) or `rdfs` (RDFS inference)
   - Leave other settings as default
5. **Click "Create"**

### Step 3: Verify Repository

1. You should see your new repository in the repositories list
2. **Click on the repository name** to open it
3. You should see the repository dashboard with:
   - Statistics (currently 0 statements)
   - SPARQL query interface
   - Import/Export options

## Loading Data via GUI

### Method 1: Import Turtle File

1. **Open your repository** (click on it in the repositories list)
2. **Click "Import"** in the left sidebar
3. **Click "Upload RDF files"**
4. **Click "Choose Files"** and select your Turtle (.ttl) file
5. **Select import settings**:
   - **Target graph**: Leave as default (default graph)
   - **Base URI**: Optional - leave blank or set to your base URI
6. **Click "Import"**
7. Wait for the import to complete (you'll see progress)
8. **Refresh the page** to see updated statistics

### Method 2: Use Command Line (Alternative)

If you prefer using the command line:

```bash
# Using the Python GraphDB client
python ingest/graphdb_client.py load path/to/file.ttl \
    --repository rig-facility-mgmt
```

## Querying via GUI

### SPARQL Query Interface

1. **Open your repository**
2. **Click "SPARQL"** in the left sidebar
3. You'll see the SPARQL query editor

### Example Queries

**Count all IFC entities:**
```sparql
PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
SELECT (COUNT(DISTINCT ?entity) as ?count)
WHERE {
    ?entity a ?type .
    FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/ifc2x3#Ifc"))
}
```

**Find all doors:**
```sparql
PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?door ?name
WHERE {
    ?door a ifc:IfcDoor .
    OPTIONAL { ?door ifc:name ?name }
    OPTIONAL { ?door rdfs:label ?name }
}
LIMIT 50
```

**Find all spaces (rooms):**
```sparql
PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
SELECT ?space ?name
WHERE {
    ?space a ifc:IfcSpace .
    OPTIONAL { ?space ifc:name ?name }
}
LIMIT 50
```

### Running Queries

1. **Type your SPARQL query** in the editor
2. **Click "Run"** or press `Ctrl+Enter` (Windows/Linux) or `Cmd+Enter` (Mac)
3. Results will appear in a table below the query editor
4. You can **export results** as CSV, JSON, or XML

## Exporting Data

### Export as Turtle

1. **Open your repository**
2. **Click "Export"** in the left sidebar
3. **Select export format**: Turtle (.ttl)
4. **Select graph**: Default graph or specific named graph
5. **Click "Export"**
6. File will download to your default download location

### Export as JSON-LD

Use the Python client:

```bash
python ingest/graphdb_client.py export output.jsonld \
    --repository rig-facility-mgmt
```

## Repository Management

### View Statistics

1. **Open your repository**
2. **Dashboard** shows:
   - Total statements (triples)
   - Number of entities
   - Graph size

### Delete Repository

1. **Click "Setup"** → **"Repositories"**
2. **Click the trash icon** next to the repository
3. **Confirm deletion**

### Backup Repository

1. **Export all data** as Turtle (see Exporting Data above)
2. Save the exported file as a backup

## Troubleshooting

### GraphDB Desktop Won't Start

- Check if port 7200 is already in use
- Restart GraphDB Desktop
- Check system requirements (Java, memory)

### Import Fails

- Check file format (must be valid Turtle/RDF)
- Check file size (large files may need more memory)
- Check GraphDB logs for errors

### Queries Return Empty Results

- Verify data was loaded (check statistics)
- Check namespace prefixes (IFC ontology URIs)
- Verify SPARQL query syntax

### Connection Refused

- Ensure GraphDB Desktop is running
- Check URL: `http://localhost:7200`
- Verify firewall settings

## Next Steps

After setting up GraphDB:

1. **Run the IFC to RDF pipeline**:
   ```bash
   python ingest/ifc_to_rdf_pipeline.py data/raw/ifc/sample_house/20210125Prova.ifc \
       --output-dir data/processed/rdf/ \
       --graphdb-repo rig-facility-mgmt
   ```

2. **Validate with SHACL**:
   ```bash
   python ingest/shacl_validation.py data/processed/rdf/*.ttl ingest/ifc2x3.ttl
   ```

3. **Test SPARQL GraphRAG**:
   ```bash
   python rag/sparql_rag.py "show me all doors" \
       --repository rig-facility-mgmt
   ```

## Resources

- **GraphDB Documentation**: https://graphdb.ontotext.com/documentation/
- **SPARQL Tutorial**: https://www.w3.org/TR/sparql11-query/
- **RDF Primer**: https://www.w3.org/TR/rdf11-primer/

