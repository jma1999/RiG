# AI-Native Agent Architecture

## Overview

This document describes the agent-based architecture that transforms the semantic digital twin into an operational AI-native IWMS platform.

## Architecture Principles

### 1. Skills, Not Chat

Instead of a generic chatbot, the system implements **agent skills** - well-defined capabilities that perform specific IWMS operations:

- **Asset & Topology Understanding**: Query equipment, zones, and relationships
- **State & Performance Understanding**: Analyze telemetry and compute KPIs
- **Fault Detection & Diagnosis**: Identify issues and determine root causes
- **Action Planning**: Propose concrete, validated actions
- **Reporting & Explanation**: Generate explainable recommendations

### 2. Twin Tools Layer

All agent operations go through a **Twin Tools** abstraction layer that provides:

- **Graph Tools** (`tools/graph_tools.py`): Typed SPARQL query abstractions
- **Timeseries Tools** (`tools/timeseries_tools.py`): SQL query abstractions with anomaly detection
- **BACnet Tools** (`tools/bacnet_tools.py`): Secure, gated building automation control

Agents **never** construct raw SPARQL/SQL/BACnet commands - they use these typed tools.

### 3. Agent Workflow

```
Detection Agent (Always-On)
    ↓
    Detects: Comfort violations, stability issues, energy anomalies
    ↓
    Creates: DetectionEvent objects
    ↓
Diagnosis Agent (Triggered by Events)
    ↓
    Uses: Graph context + Timeseries data + LLM reasoning
    ↓
    Generates: Ranked hypotheses with confidence scores
    ↓
Recommendation Agent (Triggered by Diagnosis)
    ↓
    Uses: Graph context + Safety rules (SHACL)
    ↓
    Proposes: Concrete actions (setpoint changes, work orders, inspections)
    ↓
    Validates: Actions against safety constraints
    ↓
Human-in-the-Loop Approval
    ↓
Execution (BACnet writes, work order creation, etc.)
```

## Implementation

### Detection Agent (`agents/detection_agent.py`)

**Capabilities:**
- Monitors telemetry for comfort violations (temperature outside 20-26°C)
- Detects stability issues (short cycling, oscillations)
- Identifies energy anomalies
- Creates structured `DetectionEvent` objects

**Usage:**
```python
from agents.detection_agent import DetectionAgent
from tools.graph_tools import GraphTools
from tools.timeseries_tools import TimeseriesTools

detection = DetectionAgent(graph_tools, timeseries_tools)
events = detection.detect_comfort_violations("ex:Zone_Main", timedelta(hours=1))
```

### Diagnosis Agent (`agents/diagnosis_agent.py`)

**Capabilities:**
- Gathers context from graph (zone, equipment, control chain)
- Retrieves timeseries data for relevant points
- Generates ranked hypotheses with confidence scores
- Suggests diagnostic tests

**Usage:**
```python
from agents.diagnosis_agent import DiagnosisAgent

diagnosis = DiagnosisAgent(graph_tools, timeseries_tools)
result = diagnosis.diagnose_event(event)

# Access primary hypothesis
primary = result.primary_hypothesis
print(f"Hypothesis: {primary.description}")
print(f"Confidence: {primary.confidence:.2%}")
```

### Recommendation Agent (`agents/recommendation_agent.py`)

**Capabilities:**
- Generates concrete action plans
- Validates actions against safety rules
- Links actions to affected zones/equipment
- Provides rationale and risk assessment

**Usage:**
```python
from agents.recommendation_agent import RecommendationAgent

recommendation = RecommendationAgent(graph_tools, bacnet_tools)
actions = recommendation.generate_recommendations(diagnosis_result)

for action in actions:
    print(f"{action.description} (Priority: {action.priority})")
    print(f"Requires approval: {action.requires_approval}")
```

## API Endpoints

### Detection
- `POST /agents/detection/run` - Run detection on zone/point
- `GET /agents/detection/events` - Get recent detection events

### Diagnosis
- `POST /agents/diagnosis/analyze` - Analyze a detection event

### Recommendation
- `POST /agents/recommendation/generate` - Generate recommendations from diagnosis

### End-to-End Workflow
- `GET /agents/workflow/end-to-end?zone_id=...` - Run complete workflow

## BACnet Integration

### BACnet Tools (`tools/bacnet_tools.py`)

**Capabilities:**
- Read BACnet values (via binding references from GraphDB)
- Propose BACnet writes (with safety checks)
- Execute approved writes (human-in-the-loop)

**Safety:**
- All writes require approval
- Safety checks validate against SHACL constraints
- Actions are logged and auditable

**API Endpoints:**
- `POST /bacnet/read` - Read BACnet value
- `POST /bacnet/write/propose` - Propose write (requires approval)
- `POST /bacnet/write/execute` - Execute approved write
- `GET /bacnet/pending-actions` - List pending actions
- `GET /bacnet/bindings` - List all BACnet bindings

## Frontend Integration

### Agent Dashboard (`ui/src/components/AgentDashboard.jsx`)

The agent dashboard showcases:
- **Detection Events**: Real-time issues detected by agents
- **Diagnosis Results**: AI-generated hypotheses with confidence
- **Recommendations**: Actionable plans with approval gates
- **End-to-End Workflow**: Complete agent pipeline execution

### Key Features:
- Visual workflow: Detection → Diagnosis → Recommendation
- Confidence scores and evidence display
- Action approval interface
- Real-time updates

## How This Disrupts Incumbent IWMS

| Feature | Legacy IWMS | This Platform |
|---------|-------------|---------------|
| **Data Model** | Tables, manual tagging | Multi-ontology RDF graph (IFC-LD + 223P + Brick + SSN/SOSA + QUDT) |
| **Model Creation** | Manual data entry | Automated from IFC + semantic overlays |
| **Operations** | Static forms, reports | Agent-driven: auto-detection, diagnosis, recommendations |
| **Integration** | Walled garden | Open standards (RDF/SPARQL/JSON-LD) |
| **Explainability** | Black box | Traceable through graph + timeseries evidence |
| **Control** | Manual or reactive | Predictive, uncertainty-aware, safety-validated |

## Next Steps

1. **Add State Estimation**: Kalman filters for data assimilation
2. **Add Surrogate Models**: Neural operators for fast predictions
3. **Add Uncertainty Quantification**: SBI for confidence intervals
4. **Extend to External Systems**: Workday, Maximo, EBS integration
5. **Add Control Algorithms**: MPC, reinforcement learning for optimization

