# ACM BuildSys 2026: Case Study & Conclusions

## Replicable Methodology for Semantic Digital Twin Construction

---

## 1. Test Subject Selection: IFC-SPF Encoding

### Rationale for Small House Model
- Selected `20210125Prova_reduced.ifc` as test subject
- IFC-SPF (STEP Physical File) encoding chosen over ifcXML/ifcJSON for:
  - Industry-standard exchange format (ISO 10303-21)
  - Compact representation (~3-5x smaller than XML equivalent)
  - Native support by IFCtoRDF converter toolchain
- Model characteristics:
  - Building elements: walls, doors, windows, spaces, flow terminals
  - Spatial hierarchy: IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey → IfcSpace
  - MEP elements: IfcFlowTerminal instances for HVAC integration

### File Structure Analysis
- IFC-SPF header contains schema declaration: `FILE_SCHEMA(('IFC2X3'))`
- Entity instances referenced by `#ID` notation
- Relationships encoded via `IfcRelContainedInSpatialStructure`, `IfcRelAggregates`

---

## 2. IFC to RDF Conversion Pipeline

### Conversion Toolchain
- **Tool**: IFCtoRDF v0.4 (Pieter Pauwels, Ghent University)
- **Reference**: https://github.com/pipauwel/IFCtoRDF
- **Output ontology**: ifcOWL (W3C Linked Building Data Community Group)

### Key Function: `convert_ifc_to_turtle()`

```python
def convert_ifc_to_turtle(
    ifc_path: str,
    turtle_path: str,
    base_uri: Optional[str] = None,
    jar_path: Optional[str] = None,
    java_memory: str = "8g"
) -> Dict[str, Any]:
    """
    Convert IFC-SPF file to RDF Turtle format using IFCtoRDF.
    """
    java_cmd = [
        "java",
        f"-Xmx{java_memory}",
        f"-Xms{java_memory}",
        "-jar", str(jar_path),
    ]
    if base_uri:
        java_cmd.extend(["--baseURI", base_uri])
    java_cmd.append(str(ifc_path))
    java_cmd.append(str(turtle_path))
    
    result = subprocess.run(java_cmd, capture_output=True, timeout=3600)
```

### CLI Invocation
```bash
python ingest/ifc_to_rdf.py \
    data/raw/20210125Prova.ifc \
    data/processed/rdf/20210125Prova.ttl \
    --base-uri https://example.com/ifc/
```

### Conversion Statistics
- Input: IFC-SPF file size $S_{ifc}$
- Output: Turtle file size $S_{ttl}$
- Expansion ratio: $\rho = \frac{S_{ttl}}{S_{ifc}} \approx 2.5 - 4.0$

### Triple Generation Model
- Each IFC entity instance generates $n$ triples where:

$$
n_{triples} = 1 + |A_{direct}| + |R_{inverse}|
$$

Where:
- $1$ = rdf:type declaration
- $|A_{direct}|$ = count of direct attributes
- $|R_{inverse}|$ = count of inverse relationships

---

## 3. GraphDB Repository Ingestion

### GraphDB Client Initialization

```python
from ingest.graphdb_client import GraphDBClient

client = GraphDBClient(
    base_url="http://localhost:7200",
    repository="rig-facility-mgmt"
)
client.create_repository(ruleset="empty")
```

### Turtle Loading Function

```python
def load_turtle_file(
    self,
    turtle_path: str,
    context: Optional[str] = None
) -> bool:
    """Load Turtle file into GraphDB repository."""
    with open(turtle_path, 'r', encoding='utf-8') as f:
        turtle_content = f.read()
    
    headers = {"Content-Type": "application/x-turtle"}
    response = self.session.post(
        self.statements_url,
        data=turtle_content.encode('utf-8'),
        headers=headers,
        timeout=300
    )
    return response.status_code in [204, 201, 200]
```

### SPARQL Endpoint Configuration
- Query endpoint: `http://localhost:7200/repositories/{repo}`
- Update endpoint: `http://localhost:7200/repositories/{repo}/statements`
- Protocol: SPARQL 1.1 Query/Update over HTTP

---

## 4. Semantic Overlay Architecture: Brick + ASHRAE 223P

### Ontology Selection Rationale

| Ontology | Purpose | Namespace Prefix |
|----------|---------|------------------|
| **ifcOWL** | Physical geometry, spatial structure | `ifc:` |
| **Brick Schema** | Operational vocabulary, point classification | `brick:` |
| **ASHRAE 223P** | Equipment topology, connection semantics | `s223:` |
| **SSN/SOSA** | Sensor/observation modeling | `sosa:` |
| **QUDT** | Units and quantities | `qudt:`, `unit:` |

### Layering Pattern
- Base layer: ifcOWL triples (auto-generated from IFC)
- Overlay layer: Brick/223P triples (manually or semi-auto constructed)
- Linking predicate: `ex:representsIfcElement` bridges IFC instance → operational entity

### Namespace Declarations

```turtle
@prefix ifc:   <http://ifc-ld.org/schemas/ifc2x3#> .
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix s223:  <http://data.ashrae.org/standard223#> .
@prefix sosa:  <http://www.w3.org/ns/sosa/> .
@prefix qudt:  <http://qudt.org/schema/qudt/> .
@prefix unit:  <http://qudt.org/vocab/unit/> .
```

### Multi-Classification Pattern
- Single entity typed under multiple ontologies:

```turtle
ex:FT_136276
    a brick:Terminal_Unit ,
      s223:TerminalUnit ,
      s223:Equipment ;
    ex:representsIfcElement inst:IfcFlowTerminal_136276 ;
    brick:hasPoint ex:FT_136276_air-temp ;
    s223:hasProperty ex:FT_136276_air-temp .
```

### Semantic Equivalence
- Brick `brick:hasPoint` ≈ 223P `s223:hasProperty` for sensor points
- Enables query federation across both vocabularies

---

## 5. SHACL Validation Framework

### SHACL Purpose
- W3C Shapes Constraint Language (SHACL) for RDF validation
- Ensures data quality gates in promotion pipeline: `raw → validated → published`

### BACnet Point Shape Definition

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <https://example.com/rig#> .
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .

ex:BACnetPointShape
    a sh:NodeShape ;
    sh:targetClass brick:Point ;
    sh:property [
        sh:path ex:bacnetDeviceInstance ;
        sh:datatype xsd:unsignedInt ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:message "BACnet point must have a device instance"@en ;
    ] ;
    sh:property [
        sh:path ex:bacnetObjectType ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:in ("analogInput" "analogOutput" "analogValue" 
               "binaryInput" "binaryOutput" "binaryValue") ;
    ] ;
    sh:property [
        sh:path qudt:hasUnit ;
        sh:nodeKind sh:IRI ;
        sh:minCount 1 ;
        sh:message "BACnet point must have a QUDT unit"@en ;
    ] .
```

### Validation Function

```python
import pyshacl
from rdflib import Graph

def validate_graph(
    data_graph_path: str,
    shacl_shapes_path: str,
    inference: str = "none"
) -> Dict[str, Any]:
    """Validate RDF graph against SHACL shapes."""
    data_graph = Graph()
    data_graph.parse(data_graph_path, format='turtle')
    
    shapes_graph = Graph()
    shapes_graph.parse(shacl_shapes_path, format='turtle')
    
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference=inference,
        abort_on_first=False
    )
    
    return {
        "conforms": conforms,
        "triple_count": len(data_graph),
        "violation_count": count_violations(results_graph)
    }
```

### Validation Metrics
- Conformance rate: $C = \frac{|E_{valid}|}{|E_{total}|}$
- Where $E_{valid}$ = entities passing all shape constraints

---

## 6. Mock Sensor Point Simulation & Semantic Normalization

### Simulated Point: Supply Air Temperature (SAT)

#### TimescaleDB Schema

```sql
CREATE TABLE telemetry_sample (
    time        TIMESTAMPTZ NOT NULL,
    point_id    TEXT NOT NULL,
    value       DOUBLE PRECISION,
    quality     TEXT
);
SELECT create_hypertable('telemetry_sample', 'time');
```

#### Data Generation Function

```python
@router.post("/seed/{point_id}")
async def seed_telemetry_data(point_id: str, count: int = 60):
    """Seed mock telemetry data for testing."""
    now = datetime.now(timezone.utc)
    
    # Temperature sensor: base 20°C with noise
    if "sat" in point_id.lower():
        base_value = 20.0
    elif "saf" in point_id.lower():
        base_value = 150.0  # CFM for flow
    
    rows = []
    for i in range(count):
        ts = now - timedelta(minutes=(count - i))
        base_value += random.uniform(-0.1, 0.1)
        rows.append((ts, point_id, round(base_value, 2), "GOOD"))
```

### Semantic Normalization TTL

```turtle
ex:FT_136276_air-temp
    a s223:Property ,
      s223:QuantifiableObservableProperty ,
      sosa:ObservableProperty ,
      brick:Supply_Air_Temperature_Sensor ;
    rdfs:label "FT_136276 supply air temperature"@en ;
    
    # QUDT unit binding
    qudt:hasQuantityKind quantitykind:Temperature ;
    qudt:hasUnit unit:DEG_C ;
    
    # BACnet external reference
    s223:hasExternalReference ex:FT_136276_air-temp_bacnetRef ;
    
    # Timeseries external reference (IRI link to dynamic data)
    s223:hasExternalReference ex:FT_136276_air-temp_ts .

# Timeseries Reference (links static graph → dynamic store)
ex:FT_136276_air-temp_ts
    a s223:ExternalReference ,
      ref:TimeseriesReference ;
    ex:tsId         "ft_136276_sat"^^xsd:string ;
    ex:tsDatabase   "rig_timeseries"^^xsd:string ;
    ex:tsTable      "telemetry_sample"^^xsd:string ;
    ex:tsColumn     "value"^^xsd:string .
```

### Static/Dynamic Data Separation

$$
G_{total} = G_{static} \cup \text{IRI}(G_{dynamic})
$$

Where:
- $G_{static}$ = RDF triples in GraphDB (metadata, topology, units)
- $G_{dynamic}$ = time-series rows in TimescaleDB (values, timestamps)
- $\text{IRI}(\cdot)$ = reference link via `ex:tsId` predicate

---

## 7. GraphRAG Implementation

### Architecture Overview
- **Retrieval**: SPARQL queries over semantic graph
- **Augmentation**: Neighborhood expansion around seed entities
- **Generation**: LLM context assembly from graph evidence

### SPARQLGraphRAG Class

```python
class SPARQLGraphRAG:
    def __init__(
        self,
        graphdb_client: GraphDBClient,
        llm_client=None,
        max_hops: int = 3,
        top_k: int = 20
    ):
        self.client = graphdb_client
        self.max_hops = max_hops
        self.top_k = top_k
```

### Natural Language → SPARQL Translation

```python
def natural_language_to_sparql(self, question: str) -> str:
    """Convert NL question to SPARQL query."""
    question_lower = question.lower()
    
    if "how many" in question_lower and "door" in question_lower:
        return """
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        SELECT (COUNT(DISTINCT ?door) as ?count)
        WHERE { ?door a ifc:IfcDoor . }
        """
    
    # Keyword-based fallback
    keywords = [w for w in question.split() if len(w) > 3]
    keyword_filter = " || ".join(
        [f'CONTAINS(LCASE(?name), "{k.lower()}")' for k in keywords[:3]]
    )
    return f"""
    PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
    SELECT ?entity ?name ?type WHERE {{
        ?entity a ?type .
        FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/ifc2x3#Ifc"))
        OPTIONAL {{ ?entity rdfs:label ?name }}
        FILTER ({keyword_filter})
    }} LIMIT 50
    """
```

### Neighborhood Expansion Algorithm

```python
def expand_neighborhood(self, seed_uris: List[str], max_hops: int = 3):
    """Expand graph neighborhood around seed URIs."""
    query = f"""
    SELECT DISTINCT ?seed ?entity ?predicate ?object
    WHERE {{
        VALUES ?seed {{ <{seed_uris[0]}> }}
        {{
            ?seed ?predicate ?object .
            BIND(?seed AS ?entity)
        }}
        UNION
        {{
            ?entity ?predicate ?seed .
        }}
        UNION
        {{
            ?seed ?p1 ?intermediate .
            ?intermediate ?predicate ?object .
            BIND(?intermediate AS ?entity)
        }}
    }} LIMIT 500
    """
    return self.execute_sparql_query(query)
```

### Evidence Building Pipeline

```python
def build_evidence(self, question: str, top_k: int = 20) -> Dict:
    """Build evidence graph from natural language question."""
    # Step 1: NL → SPARQL
    sparql_query = self.natural_language_to_sparql(question)
    
    # Step 2: Execute query → seed URIs
    results = self.execute_sparql_query(sparql_query)
    seed_uris = extract_uris(results)
    
    # Step 3: Neighborhood expansion
    neighborhood = self.expand_neighborhood(seed_uris[:top_k])
    
    return {
        "question": question,
        "sparql_query": sparql_query,
        "focus_seeds": seed_uris,
        "nodes": neighborhood["nodes"],
        "edges": neighborhood["edges"]
    }
```

### Retrieval Relevance Scoring
- Seed entity relevance score based on graph distance:

$$
\text{score}(e) = \alpha^{d(e, q)}
$$

Where:
- $d(e, q)$ = shortest path distance from entity $e$ to query seed $q$
- $\alpha \in (0, 1)$ = decay factor (default: 0.5)
- Entities at distance 0 (seeds): score = 1.0
- Entities at distance 1: score = 0.5
- Entities at distance 2: score = 0.25

---

## 8. Quantitative Evaluation Metrics

### Graph Statistics

| Metric | Formula | Description |
|--------|---------|-------------|
| Triple count | $|T|$ | Total RDF triples in repository |
| Entity count | $|E| = |\{s : (s, \text{rdf:type}, o) \in T\}|$ | Distinct typed entities |
| Relationship density | $\rho = \frac{|T| - |E|}{|E|}$ | Avg. predicates per entity |

### Query Performance

$$
\text{Latency}_{avg} = \frac{1}{n} \sum_{i=1}^{n} t_{response}^{(i)}
$$

### SHACL Conformance Rate

$$
C_{SHACL} = \frac{|E_{conforming}|}{|E_{targeted}|} \times 100\%
$$

### Evidence Recall

$$
R@k = \frac{|\text{RelevantEntities} \cap \text{TopK}|}{|\text{RelevantEntities}|}
$$

---

## 9. Key Code Artifacts Summary

| Component | File Path | Key Function |
|-----------|-----------|--------------|
| IFC→RDF Conversion | `ingest/ifc_to_rdf.py` | `convert_ifc_to_turtle()` |
| GraphDB Client | `ingest/graphdb_client.py` | `GraphDBClient.load_turtle_file()` |
| SHACL Validation | `ingest/shacl_validation.py` | `validate_graph()` |
| Semantic Overlay | `data/semantic/ft_136276_semantic.ttl` | Turtle definitions |
| SHACL Shapes | `shacl/controls/bacnet-point.ttl` | `ex:BACnetPointShape` |
| GraphRAG | `rag/sparql_rag.py` | `SPARQLGraphRAG.build_evidence()` |
| Telemetry API | `api/telemetry.py` | `seed_telemetry_data()` |

---

## 10. Reproducibility Checklist

### Prerequisites
- [ ] Java JDK 8+ (for IFCtoRDF)
- [ ] Python 3.11+ with `rdflib`, `pyshacl`, `SPARQLWrapper`
- [ ] GraphDB Desktop/Server (port 7200)
- [ ] TimescaleDB (PostgreSQL extension)

### Steps to Reproduce
1. Convert IFC to RDF:
   ```bash
   python ingest/ifc_to_rdf.py input.ifc output.ttl --base-uri https://example.com/ifc/
   ```

2. Create GraphDB repository:
   ```bash
   python ingest/graphdb_client.py create --repository rig-facility-mgmt
   ```

3. Load base IFC-LD triples:
   ```bash
   python ingest/graphdb_client.py load output.ttl
   ```

4. Load semantic overlay:
   ```bash
   python ingest/graphdb_client.py load data/semantic/ft_136276_semantic.ttl
   ```

5. Validate with SHACL:
   ```bash
   python ingest/shacl_validation.py output.ttl shacl/controls/bacnet-point.ttl
   ```

6. Seed telemetry data:
   ```bash
   curl -X POST "http://localhost:8000/telemetry/seed/ft_136276_sat?count=60"
   ```

7. Run GraphRAG query:
   ```bash
   python rag/sparql_rag.py "Find all supply air temperature sensors"
   ```

---

## 11. Conclusions

### Key Contributions
- Standards-first architecture using W3C RDF, SHACL, SPARQL
- Static/dynamic data separation via IRI references
- Multi-ontology layering (ifcOWL + Brick + 223P + SSN/SOSA + QUDT)
- LLM-agnostic GraphRAG over semantic building data

### Limitations
- Manual semantic overlay construction (future: auto-generation from BACnet discovery)
- NL→SPARQL translation limited to keyword patterns (future: LLM-based generation)
- Single-building test case (future: multi-building portfolio evaluation)

### Future Work
- Automated Brick/223P classification from IFC element types
- Real BACnet/IP integration for live telemetry
- Federated SPARQL queries across distributed building graphs
- Fine-tuned LLM for domain-specific SPARQL generation

---

## References

```bibtex
@inproceedings{pauwels2017ifcowl,
  title={Express to OWL for construction industry: Towards a recommendable and usable ifcOWL ontology},
  author={Pauwels, Pieter and Terkaj, Walter},
  booktitle={Automation in Construction},
  volume={63},
  pages={100--133},
  year={2016}
}

@misc{brick2019,
  title={Brick: A uniform metadata schema for buildings},
  author={Balaji, Bharathan and others},
  howpublished={https://brickschema.org},
  year={2019}
}

@standard{ashrae223,
  title={ASHRAE Standard 223P: Designation and Classification of Semantic Tags for Building Data},
  organization={ASHRAE},
  year={2024}
}

@misc{shacl2017,
  title={Shapes Constraint Language (SHACL)},
  author={W3C},
  howpublished={https://www.w3.org/TR/shacl/},
  year={2017}
}
```
