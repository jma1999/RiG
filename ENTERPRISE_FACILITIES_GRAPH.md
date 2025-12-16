# Enterprise Facilities Graph Architecture
## Based on Joel Bender's BACSI Work at Cornell

This document outlines the architecture for a **semantic + operational stack** that transforms the RiG platform into an enterprise-grade Facilities Data Fabric, informed by Cornell's BACSI project and ASHRAE standards alignment.

---

## 1. The Semantic + Operational Stack

### Three-Layer Foundation

| Layer | Standard | Purpose | Implementation |
|-------|----------|---------|----------------|
| **Physical** | **ASHRAE 223** | Canonical identities for equipment/points and their relationships (JSON-LD) | 223 contexts, SHACL profile for points & systems |
| **Comms** | **ASHRAE 135 (BACnet/SC)** | Discovery, COV/polling, alarm/event ingestion, write commands (governed) | BACnet→Brick/223 mapping, "last value" snapshot model |
| **Logical** | **ASHRAE 231 (Modelica/CDL)** | Control logic & simulation blocks; surrogate/RC models; FDD motifs | CDL block library mapped to graph, R2R links to telemetry |

### View Ontologies (Interoperability Layers)

- **Brick Schema**: Operational vocabulary for building systems
- **Haystack**: Tag-based building data model
- **SAREF4BLDG**: Smart appliances reference model
- **DBO (Digital Building Ontology)**: Building information modeling
- **REC (Real Estate Core)**: Tenant/occupant views

**Key Insight**: These are **view adapters** over the same instance graph, not separate databases.

---

## 2. Layer Collapse: The Enterprise Facilities Graph

Real deployments require **cross-domain joins** across:
- **Controls** (BACnet, BMS)
- **HR** (Workday: roles, responsibility, on-call)
- **Finance** (EBS/Kuali: billing, cost allocation)
- **Asset Management** (Maximo: lifecycle, PM schedules, spares)
- **Scheduling** (Office365: room calendars, occupancy)
- **Network** (Network Engineering: VLAN, switch/port topology)
- **Space** (Facilities Inventory: space ownership, occupancy)

### Architecture Pattern: Named Subgraphs

```
Enterprise Graph
├── controls/*      (BACnet, BMS, points, equipment)
├── finance/*       (EBS/Kuali billing, meters, cost centers)
├── hr/*            (Workday org structure, roles, responsibility)
├── workorders/*    (Maximo assets, PM schedules, WOs)
├── space/*         (Facilities Inventory, IFC-LD/LBD spaces)
├── net/*           (Network topology, VLANs, devices)
└── scheduling/*     (Office365 calendars, occupancy)
```

### Stable Identities + Crosswalks

**Cross-domain identity mapping**:

```turtle
# Space: IFC-LD ↔ Facilities Inventory
ex:Space_101
    a ifc:IfcSpace ;
    ex:hasFacilitiesInventoryId "FAC-101-A" ;
    ex:hasWorkdayLocationId "WD-LOC-789" .

# Asset: IFC ↔ Maximo
ex:AHU_3
    a brick:AHU ;
    ex:hasMaximoAssetId "MAX-ASSET-456" ;
    ex:hasMaximoLocationId "MAX-LOC-123" .

# Person: Workday ↔ Org Chart
ex:Person_JohnDoe
    a foaf:Person ;
    ex:hasWorkdayId "WD-EMP-12345" ;
    ex:responsibleFor ex:Building_A ;
    ex:onCallFor ex:Zone_Main .

# Calendar: Office365 ↔ Space
ex:Room_Conference_A
    a s223:Zone ;
    ex:hasOffice365CalendarId "cal-room-conf-a@cornell.edu" ;
    ex:hasOccupancyProxy ex:Room_Conference_A_occupancy .
```

---

## 3. Data Contracts per Domain

Each integration source publishes a **1-page contract**:

### Contract Structure

```yaml
Domain: controls
Source: BACnet/IP
Scope:
  - Entities: Devices, Objects (AI/AO/AV/BI/BO/BV), Points
  - Primary Keys: Device Instance, Object Instance
  - IRI Policy: https://rig.example.com/controls/{device}/{object}
Freshness:
  - Mode: push (COV) + pull (polling)
  - Latency: < 5 seconds (COV), < 60 seconds (polling)
Shapes:
  - SHACL: shacl/controls/bacnet-point.ttl
  - Required: deviceInstance, objectType, objectInstance, presentValue
Provenance:
  - Writer: BACnet Gateway Service
  - PII: None
  - Security: VLAN-segmented, VPN for remote access
SLAs:
  - Error Budget: 99.5% uptime
  - Fallback: Synthetic last-value if feed fails > 5 min
```

### Example Contracts

- **controls**: BACnet discovery → mapping → events → commands
- **finance**: EBS/Kuali billing → meters → spaces → cost centers
- **hr**: Workday org → roles → responsibility → on-call routing
- **workorders**: Maximo assets → PM schedules → WOs → history
- **scheduling**: Office365 calendars → occupancy → setpoint tuning
- **net**: Network topology → VLAN → switch/port → device diagnostics

---

## 4. Governance: Promotion Pipeline

### Staging Graphs

```
raw → validated → published
```

**Per-domain promotion**:

1. **Raw**: Ingested data, no validation
2. **Validated**: SHACL-gated, domain-specific shapes applied
3. **Published**: Available for queries, dashboards, APIs

### Gate = SHACL

Domain-specific shapes:
- `shacl/controls/bacnet-point.ttl` - BACnet point completeness
- `shacl/finance/meter-billing.ttl` - Meter → space → cost center linkage
- `shacl/hr/org-role.ttl` - Workday org structure, responsibility chains
- `shacl/workorders/asset-lifecycle.ttl` - Maximo asset completeness
- `shacl/scheduling/calendar-space.ttl` - Office365 calendar → space mapping

### Context Versioning

Pin ontology versions:
- `brick:1.3.0`
- `s223:1.0.0`
- `qudt:2.1.0`

Log which version produced each published snapshot.

### Change Impact Links

When a point/asset name changes:
```turtle
ex:Point_OldName
    owl:sameAs ex:Point_NewName ;
    ex:renamedAt "2024-01-15T10:00:00Z"^^xsd:dateTime ;
    ex:renamedBy ex:User_Admin .
```

Preserves history, prevents dashboard 404s.

---

## 5. BACnet Leverage (Operational Excellence)

### Discovery → Mapping

1. **BACnet Discovery**: Scan network for devices, objects
2. **Semantic Mapping**: ObjectType → Brick/223 class
3. **Address Resolution**: Device/object instances → IRIs
4. **Unit Normalization**: BACnet units → QUDT URIs
5. **Equipment/Space Links**: Bind to graph entities

### Events Pipeline

```
COV/Alarms → Event Graph
```

Event structure:
- Severity (info, warning, critical)
- Dedup keys (device + object + timestamp)
- Correlation motifs (e.g., "fan cmd=ON & flow=0" → fault pattern)

### Command Guardrails

- **Role-based allowlist**: Which users/roles can write which points
- **Pre-flight checks**: Schedules, locks, emergency "safe mode"
- **Audit trail**: All writes logged with provenance

**Client value**: One secure, governed control surface across vendors.

---

## 6. Logical Layer Strength (231/CDL)

### FDD Motifs as CDL Blocks

Represent common fault patterns:
- "Supply air temp deviation > 2°C for > 15 min"
- "Device status ≠ commanded status"
- "Fan ON but flow = 0"

As CDL blocks tied to equipment/point IRIs.

### Parameter Sets in Graph

Store thresholds, time constants:
```turtle
ex:FDD_Rule_SAT_Deviation
    a cdl:FDDBlock ;
    cdl:hasParameter ex:threshold_2degC ;
    cdl:hasParameter ex:timeWindow_15min ;
    cdl:appliesTo ex:FT_136276_air-temp .
```

SHACL checks parameters exist.

### Surrogates/RC Models

Bind surrogate models to equipment/zone IRIs:
```turtle
ex:Zone_Main
    ex:hasSurrogateModel ex:RC_Model_Zone_Main ;
    ex:hasUncertainty [
        ex:mean 24.3 ;
        ex:stdDev 0.8 ;
        ex:confidence 0.95
    ] .
```

### Close the Loop

Recommendations (WO templates, setpoint changes) are graph entities:
```turtle
ex:Recommendation_001
    a ex:Recommendation ;
    ex:proposedAction ex:SetpointChange_001 ;
    ex:evidence ex:Diagnosis_001 ;
    ex:confidence 0.85 .
```

---

## 7. People, Process, Money: First-Class Citizens

### Workday (HR/Roles)

- **Who owns** building/space/system → affects approval & on-call routing
- **Org structure** → responsibility chains
- **On-call schedules** → escalation paths

### Maximo (Assets/WOs)

- **Asset lifecycle**: Install, maintain, replace
- **PM schedules**: Preventive maintenance linked to equipment IRIs
- **Spares & warranty**: Inventory tracking
- **History intact**: IRIs preserve history across replacements

### EBS/Kuali (Billing)

- **Cost allocation**: Meters → spaces → cost centers
- **Anomalies → chargeback narratives**: Energy spikes → tenant billing
- **Reporting**: Finance-ready dashboards

### Office365 (Scheduling)

- **Occupancy proxy**: Calendar bookings → occupancy estimates
- **Blend with CO₂/temp**: Tune setpoints & FDD thresholds
- **Room availability**: Space utilization analytics

### Network Topology

- **Device ↔ VLAN ↔ switch/port**: Cyber triage
- **"Is it the network?" diagnostics**: Fault isolation
- **Security segmentation**: VLAN boundaries for access control

---

## 8. Productization: Reference APIs

### Core Endpoints

```
GET /graph/:iri
  → Compacted JSON-LD for any entity (with context version)

POST /ask
  → GraphRAG Q&A returns answer + evidence IRIs + proposed actions

GET /fdd/:building
  → Open faults with root causes & confidence

POST /workorders
  → Creates WO payload (or pushes to Maximo)

GET /audits/validation
  → Latest SHACL reports per domain
```

### Domain-Specific Endpoints

```
GET /controls/points/:point_id
  → Point metadata + latest value + BACnet binding

GET /finance/meters/:meter_id/billing
  → Billing history + cost allocation

GET /hr/org/:person_id/responsibility
  → Responsibility chain + on-call routing

GET /workorders/assets/:asset_id/lifecycle
  → Asset history + PM schedule + spares

GET /scheduling/spaces/:space_id/occupancy
  → Calendar bookings + occupancy proxy + setpoint recommendations
```

---

## 9. Acceptance Tests (Client Confidence)

### Test 1: Rename Resilience
- Rename a point/device upstream
- **Expected**: Published graph updates, dashboards don't 404, history remains linked via `owl:sameAs`

### Test 2: Network Fault Isolation
- Simulate VLAN outage
- **Expected**: Alarms show network fault, no spurious HVAC WOs

### Test 3: Org Restructure Adaptation
- Org restructure in Workday
- **Expected**: On-call routing and approval flows adapt automatically

### Test 4: Cross-Domain Query
- Query: "Who is responsible for the AHU serving the conference room that's overheating?"
- **Expected**: Returns person (Workday) + equipment (controls) + space (IFC-LD) + diagnosis (FDD)

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [x] 223 + Brick + QUDT + SSN/SOSA contexts
- [ ] Domain-specific SHACL shapes (controls, finance, hr, workorders)
- [ ] Data contracts structure
- [ ] Named subgraphs in GraphDB

### Phase 2: Cross-Domain Integration (Week 3-4)
- [ ] Workday integration stub (org structure, roles)
- [ ] Maximo integration stub (assets, WOs)
- [ ] Office365 integration stub (calendars)
- [ ] Network topology integration stub
- [ ] EBS/Kuali integration stub (billing)

### Phase 3: Governance (Week 5-6)
- [ ] Promotion pipeline (raw → validated → published)
- [ ] SHACL-gated validation per domain
- [ ] Context versioning
- [ ] Change impact tracking (`owl:sameAs`)

### Phase 4: Operational Excellence (Week 7-8)
- [ ] Enhanced BACnet integration (discovery, mapping, events, commands)
- [ ] Command guardrails (role-based, pre-flight checks)
- [ ] FDD/CDL logical layer representation
- [ ] Surrogate models + uncertainty quantification

### Phase 5: Productization (Week 9-10)
- [ ] Enterprise graph API endpoints
- [ ] GraphRAG enhancements (multi-store retrieval)
- [ ] Acceptance tests
- [ ] Documentation & client onboarding

---

## 11. Thesis Contribution Summary

### Claims

1. **Standards-aligned spine**: 223 (physical), 135/BACnet (comms), 231/CDL (logic) + view ontologies
2. **Enterprise graph with view adapters**: One instance graph, many stakeholder contexts; SHACL-gated promotion
3. **Operational integration & governance**: Discovery→mapping→events→commands with security and provenance
4. **Outcomes**: Fewer integration hours, durable IDs over change, faster root-cause, safer commands, finance-ready reporting

### Novelty

- **First** to operationalize the full 223/135/231 stack in a production IWMS
- **First** to demonstrate "layer collapse" as a feature (enterprise graph with cross-domain joins)
- **First** to apply SHACL-gated promotion pipelines for facilities data
- **First** to integrate controls, HR, finance, assets, scheduling, and network topology in a single semantic twin

---

## References

- ASHRAE 223: Semantic Data Models for Building Operations
- ASHRAE 135: BACnet - A Data Communication Protocol for Building Automation and Control Networks
- ASHRAE 231: Control Description Language (CDL) and Modelica Integration
- Cornell BACSI Project: Building Automation & Controls Systems Integration
- Brick Schema: https://brickschema.org
- QUDT: Quantities, Units, Dimensions, and Types


