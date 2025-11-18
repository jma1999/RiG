# Comprehensive Code Explanation: IFC-SPF to RDF Pipeline with Semantic Overlays

## Overview

This document provides a detailed explanation of the RiG (Retrieval over ifcJSON Graphs) codebase, which implements a complete pipeline for converting IFC-SPF (Industry Foundation Classes - STEP Physical File) building models into semantic RDF graphs with multi-layered semantic overlays. The system integrates IFC geometry data with operational semantics (ASHRAE 223P/Brick), sensing ontologies (SSN/SOSA), units (QUDT), and telemetry infrastructure (TimescaleDB, BACnet).

## Architecture Overview

The pipeline follows this flow:

```
IFC-SPF File
    ↓
[MVD Reduction] → Python function based on Facility Management MVD PDF
    ↓
[IFC to RDF] → IFCtoRDF Java JAR (via Python wrapper)
    ↓
[Turtle File] → RDF/OWL compliant graph
    ↓
[GraphDB Ingestion] → Load into GraphDB repository
    ↓
[SHACL Validation] → Validate against IFC-LD SHACL shapes
    ↓
[Semantic Overlays] → Add 223P/Brick/SSN/SOSA/QUDT layers
    ↓
[TimescaleDB] → Initialize for telemetry storage
```

---

## 1. IFC-SPF File Input

### What is IFC-SPF?

IFC-SPF (STEP Physical File) is the standard file format for exchanging building information models. It's a text-based format that follows the STEP (Standard for the Exchange of Product model data) standard, encoding building geometry, properties, and relationships.

### File Location

Input IFC files are stored in:
- `data/raw/ifc/sample_house/20210125Prova.ifc`

The system accepts IFC files in IFC2x3, IFC4, or IFC4x3 formats.

---

## 2. MVD Reduction Using Facility Management MVD PDF

### Purpose

The MVD (Model View Definition) reduction step filters the IFC file to retain only entities relevant to Facility Management operations, significantly reducing file size and processing time while maintaining essential building information.

### Implementation: `ingest/mvd_reduction.py`

#### Key Components

**1. MVD Entity Type Definitions**

The script defines `FACILITY_MGMT_TYPES`, a comprehensive set of IFC entity types essential for facility management:

```python
FACILITY_MGMT_TYPES = {
    # Spatial structure
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
    
    # Core building elements
    "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcRoof", "IfcDoor", 
    "IfcWindow", "IfcColumn", "IfcBeam", "IfcStair", "IfcRailing",
    
    # Distribution systems (HVAC, Electrical, Plumbing)
    "IfcDistributionFlowElement",
    "IfcFlowTerminal",  # Diffusers, grilles, outlets
    "IfcFlowController",  # Valves, dampers
    "IfcFlowMovingDevice",  # Pumps, fans
    "IfcFlowStorageDevice",  # Tanks
    "IfcEnergyConversionDevice",  # AHUs, boilers
    "IfcFlowSegment",  # Ducts, pipes
    "IfcDistributionElement",
    "IfcDistributionChamberElement",
    
    # Systems and relationships
    "IfcSystem", "IfcDistributionSystem",
    "IfcRelContainedInSpatialStructure", "IfcRelAggregates",
    "IfcRelServicesBuildings", "IfcRelAssignsToGroup",
    "IfcRelConnectsElements", "IfcRelConnectsPorts",
    "IfcRelConnectsPortToElement", "IfcRelDefinesByProperties",
    "IfcRelDefinesByType",
    
    # Property sets (essential for FM)
    "IfcPropertySet", "IfcPropertySingleValue", "IfcPropertyBoundedValue",
    "IfcPropertyEnumeratedValue", "IfcPropertyListValue",
    
    # Types, classifications, materials
    "IfcTypeObject", "IfcPropertySetDefinition",
    "IfcMaterial", "IfcMaterialList", "IfcMaterialLayer",
    "IfcElementQuantity",
    
    # Geometric representation
    "IfcProductDefinitionShape", "IfcShapeRepresentation",
    "IfcGeometricRepresentationItem",
}
```

**2. Relationship Collection**

The `get_required_relationships()` function ensures referential integrity by:
- Collecting all GlobalIds of entities we're keeping
- Traversing entity attributes to find referenced entities
- Maintaining relationships between kept entities

**3. Reduction Process**

The `apply_mvd_reduction()` function:
1. Loads the IFC file using IfcOpenShell
2. Identifies entities matching `FACILITY_MGMT_TYPES`
3. Collects required relationships to maintain graph connectivity
4. Creates a reduced IFC file containing only relevant entities
5. Outputs statistics on reduction percentage

**4. MVD PDF Reference**

The MVD specification is documented in:
- `ingest/IFC2x3.pdf` - BuildingSMART Facility Management MVD specification

This PDF defines which IFC entities and relationships are required for facility management use cases, guiding the reduction logic.

### Usage

```bash
python ingest/mvd_reduction.py input.ifc output_reduced.ifc
```

### Output

- Reduced IFC file: `data/processed/rdf/20210125Prova_reduced.ifc`
- Statistics showing reduction percentage and entity type counts

---

## 3. IFC to RDF Conversion: IFCtoRDF Java JAR via Python Wrapper

### Purpose

Converts the IFC-SPF file (reduced or full) into RDF Turtle format using the IFCtoRDF Java tool, which implements the ifcOWL ontology mapping.

### Implementation: `ingest/ifc_to_rdf.py`

#### Key Components

**1. JAR Management**

The script automatically manages the IFCtoRDF JAR file:

```python
IFCTORDF_VERSION = "0.4"
IFCTORDF_JAR_NAME = f"IFCtoRDF-{IFCTORDF_VERSION}-SNAPSHOT-shaded.jar"
IFCTORDF_DOWNLOAD_URL = (
    f"https://github.com/pipauwel/IFCtoRDF/releases/download/"
    f"IFCtoRDF-{IFCTORDF_VERSION}/{IFCTORDF_JAR_NAME}"
)
DEFAULT_JAR_PATH = pathlib.Path(__file__).parent.parent / "tools" / "ifctordf" / IFCTORDF_JAR_NAME
```

- **Auto-download**: If the JAR doesn't exist, it downloads from GitHub releases
- **Location**: `tools/ifctordf/IFCtoRDF-0.4-SNAPSHOT-shaded.jar`
- **Reference**: https://github.com/pipauwel/IFCtoRDF

**2. Java Environment Check**

The `check_java_available()` function:
- Verifies Java JDK 8+ is installed
- Checks Java version
- Provides helpful error messages if Java is missing

**3. Conversion Process**

The `convert_ifc_to_turtle()` function:

```python
def convert_ifc_to_turtle(
    ifc_path: str,
    turtle_path: str,
    base_uri: Optional[str] = None,
    jar_path: Optional[str] = None,
    java_memory: str = "8g"
) -> Dict[str, Any]:
```

**Process Steps:**

1. **Validate Input**: Checks IFC file exists
2. **Check Java**: Ensures Java runtime is available
3. **Ensure JAR**: Downloads JAR if missing
4. **Build Java Command**: Constructs command to run IFCtoRDF:
   ```bash
   java -Xmx8g -Xms8g -jar IFCtoRDF-0.4-SNAPSHOT-shaded.jar \
       --baseURI https://example.com/ifc/ \
       input.ifc output.ttl
   ```
5. **Execute Conversion**: Runs subprocess with timeout (1 hour)
6. **Validate Output**: Checks Turtle file was created
7. **Return Statistics**: File sizes, conversion status

**4. ifcOWL Ontology**

IFCtoRDF converts IFC entities to RDF using the ifcOWL ontology:
- **Namespace**: `http://ifc-ld.org/schemas/ifc2x3#`
- **Classes**: `ifc:IfcDoor`, `ifc:IfcWindow`, `ifc:IfcSpace`, etc.
- **Properties**: IFC attributes become RDF properties
- **Relationships**: IFC relationships become RDF object properties

### Usage

```bash
# Single file
python ingest/ifc_to_rdf.py input.ifc output.ttl --base-uri https://example.com/ifc/

# Directory
python ingest/ifc_to_rdf.py --dir input_dir/ output_dir/ --base-uri https://example.com/ifc/
```

### Output

- Turtle file: `data/processed/rdf/20210125Prova_reduced.ttl`
- Contains RDF triples following ifcOWL ontology
- File size typically 2-5x larger than original IFC (RDF is verbose)

---

## 4. GraphDB Ingestion

### Purpose

Loads the RDF Turtle file into GraphDB, a semantic graph database (RDF triplestore) that enables efficient SPARQL querying and graph operations.

### Implementation: `ingest/graphdb_client.py`

#### Key Components

**1. GraphDBClient Class**

The `GraphDBClient` class provides a Python interface to GraphDB:

```python
class GraphDBClient:
    def __init__(
        self,
        base_url: str = "http://localhost:7200",
        repository: str = "rig-facility-mgmt",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
```

**Configuration:**
- **Base URL**: Default `http://localhost:7200` (GraphDB Desktop)
- **Repository**: `rig-facility-mgmt` (custom repository name)
- **Authentication**: Optional username/password for server deployments

**2. Repository Management**

**Create Repository:**
```python
def create_repository(
    self,
    title: Optional[str] = None,
    description: Optional[str] = None,
    ruleset: str = "empty"
) -> bool:
```

- Creates GraphDB repository via REST API
- Configures inference ruleset (empty, rdfs, owl-horst)
- Sets query timeout and exception handling

**Repository Configuration:**
```json
{
    "id": "rig-facility-mgmt",
    "title": "RiG Facility Management",
    "type": "graphdb:FreeSailRepository",
    "params": [
        {"id": "ruleset", "value": "empty"},
        {"id": "query-timeout", "value": "0"}
    ]
}
```

**3. Turtle File Loading**

**Load Process:**
```python
def load_turtle_file(
    self,
    turtle_path: str,
    context: Optional[str] = None,
    base_uri: Optional[str] = None
) -> bool:
```

**Steps:**
1. Reads Turtle file content
2. Prepares HTTP headers: `Content-Type: application/x-turtle`
3. POSTs to GraphDB REST API: `/repositories/{repo}/statements`
4. GraphDB parses and stores RDF triples
5. Returns success/failure status

**API Endpoint:**
```
POST http://localhost:7200/repositories/rig-facility-mgmt/statements
Content-Type: application/x-turtle

[Turtle file content]
```

**4. SPARQL Query Execution**

```python
def execute_sparql_query(
    self,
    query: str,
    output_format: str = "json"
) -> Dict[str, Any]:
```

Uses SPARQLWrapper library to execute queries:
- **Endpoint**: `http://localhost:7200/repositories/rig-facility-mgmt`
- **Formats**: JSON, XML, Turtle
- **Authentication**: Supports basic auth if configured

**Example Query:**
```sparql
PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
SELECT ?door ?name
WHERE {
    ?door a ifc:IfcDoor .
    OPTIONAL { ?door ifc:name ?name }
}
LIMIT 50
```

**5. JSON-LD Export**

```python
def export_as_jsonld(
    self,
    output_path: str,
    context: Optional[str] = None,
    base_uri: Optional[str] = None
) -> bool:
```

- Executes CONSTRUCT query to get all triples
- Converts RDF graph to JSON-LD format
- Writes to file for external use

### GraphDB Setup

**Installation:**
1. Download GraphDB Desktop: https://www.ontotext.com/products/graphdb/graphdb-free/
2. Launch GraphDB Desktop
3. Access at `http://localhost:7200`

**Repository Creation:**
- Via GUI: Setup → Repositories → Create new repository
- Via Python: `python ingest/graphdb_client.py create --repository rig-facility-mgmt`

### Usage

```bash
# Create repository
python ingest/graphdb_client.py create --repository rig-facility-mgmt

# Load Turtle file
python ingest/graphdb_client.py load file.ttl --repository rig-facility-mgmt

# Execute SPARQL query
python ingest/graphdb_client.py query "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

# Export as JSON-LD
python ingest/graphdb_client.py export output.jsonld --repository rig-facility-mgmt
```

### How Ingestion Works

1. **Turtle File Parsing**: GraphDB parses the Turtle syntax into RDF triples
2. **Triple Storage**: Each triple (subject, predicate, object) is stored in the repository
3. **Indexing**: GraphDB creates indexes for efficient querying
4. **Inference**: If ruleset is enabled, GraphDB infers additional triples
5. **Statistics**: Repository tracks statement count, entity count, graph size

**Example Triple:**
```
<https://example.com/ifc/IfcFlowTerminal_136276> 
    a 
    <http://ifc-ld.org/schemas/ifc2x3#IfcFlowTerminal> .
```

This triple states: "The entity IfcFlowTerminal_136276 is of type IfcFlowTerminal"

---

## 5. SHACL Validation

### Purpose

Validates the RDF graph against SHACL (Shapes Constraint Language) shapes to ensure IFC-LD compliance and data quality.

### Implementation: `ingest/shacl_validation.py`

#### Key Components

**1. SHACL Shapes File**

The validation uses SHACL shapes defined in:
- `ingest/ifc2x3.ttl` - SHACL shapes for IFC2x3 schema validation

This file contains:
- **Node Shapes**: Define constraints on IFC entity types
- **Property Shapes**: Define constraints on properties
- **Constraint Types**: minCount, maxCount, datatype, class, etc.

**2. Validation Process**

```python
def validate_graph(
    data_graph_path: str,
    shacl_shapes_path: str,
    ont_graph_path: Optional[str] = None,
    inference: str = "none"
) -> Dict[str, Any]:
```

**Steps:**

1. **Load Data Graph**: Parses Turtle file into RDF graph
2. **Load SHACL Shapes**: Parses SHACL shapes file
3. **Load Ontology** (optional): For RDFS/OWL inference
4. **Execute Validation**: Uses `pyshacl` library:
   ```python
   conforms, results_graph, results_text = pyshacl.validate(
       data_graph,
       shacl_graph=shapes_graph,
       ont_graph=ont_graph,
       inference=inference,
       abort_on_first=False
   )
   ```
5. **Parse Results**: Extracts constraint violations
6. **Return Report**: Validation status, violation count, details

**3. Validation Results**

The function returns:
```python
{
    "conforms": bool,  # True if validation passed
    "validation_passed": bool,
    "triple_count": int,
    "shapes_count": int,
    "violations": [
        {
            "subject": str,  # Entity URI with violation
            "predicate": str,  # Constraint type
            "object": str  # Violation details
        }
    ],
    "violation_count": int,
    "results_text": str  # Human-readable report
}
```

**4. Common Validation Checks**

SHACL shapes validate:
- **Type Constraints**: Entities must be valid IFC types
- **Property Constraints**: Required properties present, correct types
- **Cardinality**: minCount/maxCount for relationships
- **Value Constraints**: Datatypes, ranges, enumerations
- **Logical Constraints**: AND, OR, NOT combinations

### Usage

```bash
python ingest/shacl_validation.py data.ttl ingest/ifc2x3.ttl --output validation_results.json
```

### Integration in Pipeline

The validation step is integrated into the complete pipeline (`ingest/ifc_to_rdf_pipeline.py`) and runs automatically after GraphDB ingestion.

---

## 6. Complete Pipeline Orchestration

### Implementation: `ingest/ifc_to_rdf_pipeline.py`

This script orchestrates all steps in sequence:

```python
def run_pipeline(
    input_ifc: str,
    output_dir: str,
    base_uri: Optional[str] = None,
    graphdb_url: str = "http://localhost:7200",
    graphdb_repo: str = "rig-facility-mgmt",
    validate: bool = True,
    shacl_shapes: Optional[str] = None,
    export_jsonld: bool = False,
    skip_mvd: bool = False
) -> Dict[str, Any]:
```

**Pipeline Steps:**

1. **MVD Reduction** (optional)
   - Applies Facility Management MVD rules
   - Outputs reduced IFC file

2. **IFC to RDF Conversion**
   - Converts IFC to Turtle using IFCtoRDF
   - Outputs RDF Turtle file

3. **GraphDB Ingestion**
   - Creates repository if needed
   - Loads Turtle file into GraphDB
   - Returns statistics

4. **SHACL Validation**
   - Validates against IFC-LD SHACL shapes
   - Reports constraint violations

5. **JSON-LD Export** (optional)
   - Exports repository as JSON-LD
   - For external use or backup

### Usage

```bash
python ingest/ifc_to_rdf_pipeline.py data/raw/ifc/sample_house/20210125Prova.ifc \
    --output-dir data/processed/rdf/ \
    --base-uri https://example.com/ifc/ \
    --graphdb-repo rig-facility-mgmt \
    --export-jsonld
```

---

## 7. Semantic Overlays: Custom Turtle File with 223P/Brick/SSN/SOSA/QUDT

### Purpose

After loading the base IFC-LD graph, we add semantic overlays that enrich the building model with:
- **ASHRAE 223P**: Standard for semantic data models in building operations
- **Brick Schema**: Operational vocabulary for building systems
- **SSN/SOSA**: W3C ontologies for sensors, observations, and actuation
- **QUDT**: Quantities, units, dimensions, and types

### Implementation: `data/semantic/ft_136276_semantic.ttl`

This file demonstrates the semantic overlay pattern for a single IFC Flow Terminal instance.

#### File Structure

**1. Namespace Declarations**

```turtle
@prefix ex:           <https://example.com/rig#> .
@prefix inst:         <https://example.com/ifc/> .
@prefix ifc:          <http://ifc-ld.org/schemas/ifc2x3#> .

@prefix brick:        <https://brickschema.org/schema/Brick#> .
@prefix tag:          <https://brickschema.org/schema/BrickTag#> .
@prefix ref:          <https://brickschema.org/schema/Brick/ref#> .

@prefix s223:         <http://data.ashrae.org/standard223#> .
@prefix g36:          <http://data.ashrae.org/standard223/1.0/extensions/g36#> .

@prefix sosa:         <http://www.w3.org/ns/sosa/> .

@prefix qudt:         <http://qudt.org/schema/qudt/> .
@prefix quantitykind: <http://qudt.org/vocab/quantitykind/> .
@prefix unit:         <http://qudt.org/vocab/unit/> .

@prefix bacnet:       <http://data.ashrae.org/bacnet/2020#> .
```

**2. IFC Element to Operations Mapping**

```turtle
# Link IFC element → operations/controls-level terminal
ex:representsIfcElement
    a owl:ObjectProperty ;
    rdfs:label "represents IFC element"@en .

# Operations-facing terminal corresponding to inst:IfcFlowTerminal_136276
ex:FT_136276
    a brick:Terminal_Unit ,
      s223:TerminalUnit ,
      s223:Equipment ;
    rdfs:label "IfcFlowTerminal_136276 (supply terminal)"@en ;
    ex:representsIfcElement inst:IfcFlowTerminal_136276 ;
```

**Key Points:**
- `ex:FT_136276` is a new entity representing the operational view
- Links to IFC element via `ex:representsIfcElement`
- Typed as both Brick (`brick:Terminal_Unit`) and 223P (`s223:TerminalUnit`)

**3. Point Graph (Brick Layer)**

```turtle
ex:FT_136276
    brick:hasPoint
        ex:FT_136276_air-temp ,
        ex:FT_136276_air-flow ,
        ex:FT_136276_damper-position ,
        ex:FT_136276_damper-command ,
        ex:FT_136276_run-status ;
```

Brick schema defines operational points (sensors, setpoints, commands) connected to equipment.

**4. Property Graph (223P Layer)**

```turtle
ex:FT_136276
    s223:hasProperty
        ex:FT_136276_air-temp ,
        ex:FT_136276_air-flow ,
        ex:FT_136276_damper-position ,
        ex:FT_136276_damper-command ,
        ex:FT_136276_run-status ;
```

223P standardizes properties (observable, actuatable) for building systems.

**5. Supply Air Temperature Point (Complete Example)**

```turtle
ex:FT_136276_air-temp
    a s223:Property ,
      s223:QuantifiableProperty ,
      s223:QuantifiableObservableProperty ,
      sosa:ObservableProperty ,
      brick:Supply_Air_Temperature_Sensor ;
    rdfs:label "FT_136276 supply air temperature"@en ;

    # QUDT semantics
    qudt:hasQuantityKind quantitykind:Temperature ;
    qudt:hasUnit        unit:DEG_C ;

    # 223 aspect: this is a supply-side role
    s223:hasAspect      s223:Role-Supply ;

    # External references (BACnet + timeseries)
    s223:hasExternalReference
        ex:FT_136276_air-temp_bacnetRef ,
        ex:FT_136276_air-temp_ts .
```

**Layered Semantics:**
- **223P**: `s223:QuantifiableObservableProperty` - observable, measurable property
- **Brick**: `brick:Supply_Air_Temperature_Sensor` - operational sensor type
- **SOSA**: `sosa:ObservableProperty` - W3C standard for observations
- **QUDT**: `qudt:hasQuantityKind quantitykind:Temperature`, `qudt:hasUnit unit:DEG_C` - units and quantities

**6. BACnet External Reference**

```turtle
ex:FT_136276_air-temp_bacnetRef
    a s223:ExternalReference ,
      s223:BACnetExternalReference ,
      ref:ExternalReference ,
      ref:BACnetReference ;
    rdfs:label "BACnet binding for FT_136276 SAT"@en ;

    ex:bacnetDeviceInstance  "1001"^^xsd:unsignedInt ;
    ex:bacnetObjectType      "analogInput"^^xsd:string ;
    ex:bacnetObjectInstance  "1"^^xsd:unsignedInt ;
    ex:bacnetPropertyId      "presentValue"^^xsd:string .
```

Links the semantic property to BACnet protocol binding:
- Device instance: 1001
- Object type: analogInput
- Object instance: 1
- Property: presentValue

**7. Timeseries Reference**

```turtle
ex:FT_136276_air-temp_ts
    a s223:ExternalReference ,
      ref:ExternalReference ,
      ref:TimeseriesReference ;
    rdfs:label "Timeseries for FT_136276 SAT"@en ;

    ex:tsId         "ft_136276_sat"^^xsd:string ;
    ex:tsDatabase   "rig_timeseries"^^xsd:string ;
    ex:tsTable      "ft_136276_sat"^^xsd:string ;
    ex:tsColumn     "value"^^xsd:string ;
    ex:tsTimeColumn "ts"^^xsd:string .
```

Links to TimescaleDB storage:
- **tsId**: `ft_136276_sat` - unique identifier linking GraphDB and TimescaleDB
- **tsDatabase**: `rig_timeseries` - database name
- **tsTable**: `ft_136276_sat` - table name
- **tsColumn**: `value` - value column
- **tsTimeColumn**: `ts` - timestamp column

**8. Zone Connectivity**

```turtle
ex:Zone_Main
    a s223:Zone ,
      brick:Location ;
    rdfs:label "Main House Zone"@en .

ex:FT_136276
    s223:connected  ex:Zone_Main ;
    brick:serves    ex:Zone_Main .

ex:Zone_Main
    ex:hasIfcSpatialContext inst:IfcBuildingStorey_134958 .
```

Links operational zones to IFC spatial structure:
- Zone defined in 223P/Brick
- Connected to IFC building storey via `ex:hasIfcSpatialContext`

### Semantic Layer Architecture

```
┌─────────────────────────────────────────┐
│  IFC-LD Layer (Physical Geometry)      │
│  inst:IfcFlowTerminal_136276            │
└─────────────────────────────────────────┘
              ↓ ex:representsIfcElement
┌─────────────────────────────────────────┐
│  223P/Brick Layer (Operations)         │
│  ex:FT_136276 (Terminal Unit)          │
│  - s223:hasProperty                    │
│  - brick:hasPoint                      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  SOSA Layer (Sensing/Actuation)         │
│  sosa:ObservableProperty                │
│  sosa:ActuatableProperty                │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  QUDT Layer (Units/Quantities)         │
│  qudt:hasQuantityKind                   │
│  qudt:hasUnit                           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  External References                    │
│  - BACnet (s223:BACnetExternalReference)│
│  - TimescaleDB (ref:TimeseriesReference)│
└─────────────────────────────────────────┘
```

### Loading Semantic Overlays

After loading the base IFC-LD graph, load the semantic overlays:

```bash
python ingest/graphdb_client.py load data/semantic/ft_136276_semantic.ttl --repository rig-facility-mgmt
```

---

## 8. TimescaleDB Initialization for Telemetry and BACnet

### Purpose

TimescaleDB is initialized to store time-series telemetry data from building systems, linked to semantic properties via the `tsId` identifier.

### Implementation

#### 1. Docker Compose Configuration: `docker-compose.yml`

```yaml
services:
  timescaledb:
    image: timescale/timescaledb:2.16.1-pg16
    environment:
      POSTGRES_USER: rig_user
      POSTGRES_PASSWORD: rig_password
      POSTGRES_DB: rig_timeseries
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  timescale_data:
```

**Configuration:**
- **Image**: TimescaleDB 2.16.1 on PostgreSQL 16
- **Database**: `rig_timeseries`
- **User**: `rig_user`
- **Password**: `rig_password`
- **Port**: 5432

#### 2. TimescaleDB Schema

The schema is defined to store telemetry data:

```sql
-- Create hypertable for time-series data
CREATE TABLE telemetry_sample (
    time TIMESTAMPTZ NOT NULL,
    point_id TEXT NOT NULL,
    value DOUBLE PRECISION,
    quality TEXT
);

-- Convert to hypertable (TimescaleDB feature)
SELECT create_hypertable('telemetry_sample', 'time');

-- Create index on point_id for fast lookups
CREATE INDEX idx_telemetry_sample_point_id ON telemetry_sample (point_id);
```

**Key Features:**
- **Hypertable**: TimescaleDB automatically partitions by time
- **point_id**: Links to GraphDB via `tsId` (e.g., `ft_136276_sat`)
- **time**: Timestamp column for time-series queries
- **value**: Numeric telemetry value
- **quality**: Data quality flag (e.g., "good", "bad", "uncertain")

#### 3. Data Seeding: `scripts/seed_sat_timeseries.py`

This script demonstrates inserting telemetry data:

```python
import psycopg2
from datetime import datetime, timedelta, timezone
import random

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="rig_timeseries",
    user="rig_user",
    password="rig_password",
)

point_id = "ft_136276_sat"  # Links to GraphDB tsId

# Generate 60 minutes of data at 1-min resolution
now = datetime.now(timezone.utc)
base_temp = 20.0

rows = []
for i in range(60):
    ts = now - timedelta(minutes=(60 - i))
    base_temp += random.uniform(-0.1, 0.1)
    rows.append((ts, point_id, round(base_temp, 2), "good"))

cur.executemany(
    """
    INSERT INTO telemetry_sample (time, point_id, value, quality)
    VALUES (%s, %s, %s, %s)
    """,
    rows,
)
```

**Key Points:**
- **point_id**: `ft_136276_sat` matches `ex:tsId` in semantic Turtle file
- **Time-series data**: Timestamped values at regular intervals
- **Quality flags**: Indicate data reliability

#### 4. Linking GraphDB and TimescaleDB

The link between GraphDB (semantic) and TimescaleDB (telemetry) is established via:

1. **GraphDB**: `ex:tsId "ft_136276_sat"` in semantic overlay
2. **TimescaleDB**: `point_id = 'ft_136276_sat'` in telemetry table

**Query Pattern:**

```sparql
# Get telemetry reference for a property
PREFIX ex: <https://example.com/rig#>
PREFIX s223: <http://data.ashrae.org/standard223#>

SELECT ?property ?tsId ?tsDatabase ?tsTable
WHERE {
    ?property a s223:QuantifiableObservableProperty .
    ?property s223:hasExternalReference ?tsRef .
    ?tsRef ex:tsId ?tsId .
    ?tsRef ex:tsDatabase ?tsDatabase .
    ?tsRef ex:tsTable ?tsTable .
}
```

Then query TimescaleDB:
```sql
SELECT time, value, quality
FROM telemetry_sample
WHERE point_id = 'ft_136276_sat'
  AND time >= NOW() - INTERVAL '1 hour'
ORDER BY time;
```

#### 5. BACnet Integration

BACnet references in the semantic overlay enable:
- **Protocol Binding**: Link semantic properties to BACnet objects
- **Device Discovery**: Map BACnet devices to building systems
- **Data Acquisition**: Read/write values via BACnet protocol

**BACnet Reference Structure:**
```turtle
ex:FT_136276_air-temp_bacnetRef
    a s223:BACnetExternalReference ;
    ex:bacnetDeviceInstance  "1001" ;
    ex:bacnetObjectType      "analogInput" ;
    ex:bacnetObjectInstance  "1" ;
    ex:bacnetPropertyId      "presentValue" .
```

**BACnet Query Pattern:**
```sparql
# Find all properties with BACnet bindings
PREFIX ex: <https://example.com/rig#>
PREFIX s223: <http://data.ashrae.org/standard223#>

SELECT ?property ?deviceInstance ?objectType ?objectInstance
WHERE {
    ?property s223:hasExternalReference ?bacnetRef .
    ?bacnetRef a s223:BACnetExternalReference .
    ?bacnetRef ex:bacnetDeviceInstance ?deviceInstance .
    ?bacnetRef ex:bacnetObjectType ?objectType .
    ?bacnetRef ex:bacnetObjectInstance ?objectInstance .
}
```

### Initialization Steps

1. **Start TimescaleDB:**
   ```bash
   docker-compose up -d timescaledb
   ```

2. **Create Schema:**
   ```sql
   CREATE TABLE telemetry_sample (
       time TIMESTAMPTZ NOT NULL,
       point_id TEXT NOT NULL,
       value DOUBLE PRECISION,
       quality TEXT
   );
   SELECT create_hypertable('telemetry_sample', 'time');
   CREATE INDEX idx_telemetry_sample_point_id ON telemetry_sample (point_id);
   ```

3. **Seed Data:**
   ```bash
   python scripts/seed_sat_timeseries.py
   ```

4. **Verify Link:**
   - Check GraphDB for `ex:tsId` values
   - Check TimescaleDB for matching `point_id` values

---

## 9. SPARQL-Based GraphRAG

### Purpose

After loading data into GraphDB, the system provides GraphRAG (Graph Retrieval-Augmented Generation) using SPARQL queries instead of Cypher.

### Implementation: `rag/sparql_rag.py`

#### Key Components

**1. SPARQLGraphRAG Class**

```python
class SPARQLGraphRAG:
    def __init__(
        self,
        graphdb_client: GraphDBClient,
        llm_client=None,
        max_hops: int = 3,
        top_k: int = 20
    ):
```

**2. Natural Language to SPARQL**

The `natural_language_to_sparql()` function converts questions to SPARQL:
- Keyword-based pattern matching
- Generates appropriate SPARQL queries
- In production, would use LLM for better query generation

**3. Graph Neighborhood Expansion**

The `expand_neighborhood()` function:
- Takes seed entity URIs
- Traverses graph relationships
- Returns connected nodes and edges
- Configurable max hops (default: 3)

**4. Evidence Building**

The `build_evidence()` function:
1. Converts question to SPARQL
2. Executes query to find seed entities
3. Expands neighborhood around seeds
4. Returns evidence graph for LLM context

### Usage

```bash
python rag/sparql_rag.py "how many doors are in the building?" \
    --repository rig-facility-mgmt \
    --top-k 20
```

---

## 10. File Structure Summary

```
RiG/
├── data/
│   ├── raw/
│   │   └── ifc/
│   │       └── sample_house/
│   │           └── 20210125Prova.ifc          # Input IFC-SPF file
│   ├── processed/
│   │   └── rdf/
│   │       ├── 20210125Prova_reduced.ifc     # MVD-reduced IFC
│   │       ├── 20210125Prova_reduced.ttl      # RDF Turtle output
│   │       └── 20210125Prova_reduced.jsonld   # JSON-LD export
│   └── semantic/
│       └── ft_136276_semantic.ttl             # Semantic overlays
│
├── ingest/
│   ├── mvd_reduction.py                       # MVD reduction script
│   ├── ifc_to_rdf.py                          # IFC to RDF converter wrapper
│   ├── graphdb_client.py                      # GraphDB client
│   ├── shacl_validation.py                    # SHACL validator
│   ├── ifc_to_rdf_pipeline.py                 # Complete pipeline
│   ├── ifc2x3.ttl                             # SHACL shapes
│   └── IFC2x3.pdf                             # MVD specification PDF
│
├── tools/
│   └── ifctordf/
│       └── IFCtoRDF-0.4-SNAPSHOT-shaded.jar   # IFCtoRDF Java tool
│
├── scripts/
│   └── seed_sat_timeseries.py                 # TimescaleDB data seeding
│
├── rag/
│   └── sparql_rag.py                          # SPARQL-based GraphRAG
│
├── docker-compose.yml                         # TimescaleDB configuration
│
└── CODE_EXPLANATION.md                        # This document
```

---

## 11. Complete Workflow Example

### Step-by-Step Execution

**1. Start Infrastructure:**
```bash
# Start TimescaleDB
docker-compose up -d timescaledb

# Start GraphDB Desktop (manual)
# Access at http://localhost:7200
```

**2. Run Complete Pipeline:**
```bash
python ingest/ifc_to_rdf_pipeline.py \
    data/raw/ifc/sample_house/20210125Prova.ifc \
    --output-dir data/processed/rdf/ \
    --base-uri https://example.com/ifc/ \
    --graphdb-repo rig-facility-mgmt \
    --export-jsonld
```

**3. Load Semantic Overlays:**
```bash
python ingest/graphdb_client.py load \
    data/semantic/ft_136276_semantic.ttl \
    --repository rig-facility-mgmt
```

**4. Initialize TimescaleDB Schema:**
```sql
CREATE TABLE telemetry_sample (
    time TIMESTAMPTZ NOT NULL,
    point_id TEXT NOT NULL,
    value DOUBLE PRECISION,
    quality TEXT
);
SELECT create_hypertable('telemetry_sample', 'time');
CREATE INDEX idx_telemetry_sample_point_id ON telemetry_sample (point_id);
```

**5. Seed Telemetry Data:**
```bash
python scripts/seed_sat_timeseries.py
```

**6. Query with SPARQL GraphRAG:**
```bash
python rag/sparql_rag.py "show me all flow terminals" \
    --repository rig-facility-mgmt
```

---

## 12. Key Design Decisions

### Why RDF Instead of Neo4j?

- **Standards Compliance**: RDF/SPARQL are W3C standards
- **Semantic Interoperability**: Better integration with ontologies (223P, Brick, SOSA, QUDT)
- **IFC-LD Alignment**: IFC-LD is RDF-based
- **Multi-ontology Support**: Easier to combine multiple ontologies

### Why Multiple Semantic Layers?

- **IFC-LD**: Physical geometry and building structure
- **223P**: Standardized building operations semantics
- **Brick**: Operational vocabulary for building systems
- **SOSA**: W3C standard for sensors and observations
- **QUDT**: Standardized units and quantities
- **Each layer serves a specific purpose** and enables different types of queries

### Why TimescaleDB?

- **Time-series Optimization**: Hypertables automatically partition by time
- **Performance**: Optimized for time-series queries (aggregations, window functions)
- **Scalability**: Handles high-frequency telemetry data
- **PostgreSQL Compatibility**: Standard SQL, easy integration

### Why BACnet References?

- **Protocol Integration**: Links semantic model to operational protocols
- **Device Discovery**: Maps semantic properties to physical devices
- **Data Acquisition**: Enables reading/writing values via BACnet

---

## 13. Future Enhancements

1. **Automated Semantic Overlay Generation**: Generate overlays automatically from IFC properties
2. **LLM-based SPARQL Generation**: Use LLMs to convert natural language to SPARQL
3. **Real-time Telemetry Ingestion**: Stream telemetry data from BACnet to TimescaleDB
4. **GraphQL API**: Expose GraphDB data via GraphQL for frontend consumption
5. **Work Order Generation**: Use semantic model to generate maintenance work orders

---

## Conclusion

This codebase implements a complete pipeline from IFC-SPF building models to semantic RDF graphs with multi-layered semantic overlays. The system integrates:

- **Physical Geometry**: IFC-LD for building structure
- **Operations Semantics**: 223P/Brick for building systems
- **Sensing/Actuation**: SOSA for observations and actuation
- **Units/Quantities**: QUDT for standardized measurements
- **Telemetry Storage**: TimescaleDB for time-series data
- **Protocol Integration**: BACnet for building automation

The architecture enables rich semantic queries, data validation, and integration with building automation systems, providing a foundation for AI-native CMMS (Computerized Maintenance Management System) applications.

