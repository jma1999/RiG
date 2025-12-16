# Architecture Update: AI-Native Agent-Based IWMS

## Summary of Changes

This update transforms the RiG platform from a semantic graph visualization tool into a **true AI-native, agent-based IWMS platform** that can compete with incumbent solutions.

## Key Architectural Additions

### 1. Twin Tools Layer (`tools/`)

**Purpose**: Well-typed abstractions that prevent agents from constructing raw SPARQL/SQL/BACnet commands.

**Components:**
- `graph_tools.py`: Graph query abstractions (zone context, equipment context, control chains)
- `timeseries_tools.py`: Telemetry query abstractions with anomaly detection
- `bacnet_tools.py`: Secure, gated BACnet control operations

**Benefits:**
- Type safety for agent operations
- Encapsulation of complex queries
- Safety validation built-in
- Easy to extend with new tools

### 2. Agent Skills Framework (`agents/`)

**Purpose**: Replace generic chat with specialized agent capabilities.

**Agents:**

#### Detection Agent (`detection_agent.py`)
- **Always-on monitoring** of telemetry
- Detects: comfort violations, stability issues, energy anomalies
- Creates structured `DetectionEvent` objects
- Runs on schedule or stream

#### Diagnosis Agent (`diagnosis_agent.py`)
- **Triggered by detection events**
- Gathers context from graph + timeseries
- Generates ranked hypotheses with confidence scores
- Uses LLM reasoning for root cause analysis
- Suggests diagnostic tests

#### Recommendation Agent (`recommendation_agent.py`)
- **Triggered by diagnoses**
- Proposes concrete actions (setpoint changes, work orders, inspections)
- Validates actions against SHACL safety rules
- Provides rationale and risk assessment
- Requires human approval for control operations

### 3. BACnet Integration (`api/bacnet.py`)

**Purpose**: Direct integration with building automation systems.

**Capabilities:**
- Read BACnet values via semantic bindings
- Propose BACnet writes (with safety checks)
- Execute approved writes (human-in-the-loop)
- List all BACnet bindings from graph

**Safety:**
- All writes require approval
- Safety checks validate against constraints
- Actions are logged and auditable

### 4. Agent API Endpoints (`api/agents.py`)

**Endpoints:**
- `POST /agents/detection/run` - Run detection agent
- `GET /agents/detection/events` - Get recent events
- `POST /agents/diagnosis/analyze` - Analyze an event
- `POST /agents/recommendation/generate` - Generate recommendations
- `GET /agents/workflow/end-to-end` - Run complete workflow

### 5. Frontend Updates

**New Components:**
- `AgentDashboard.jsx`: Shows agent workflows, events, diagnoses, recommendations
- Updated `TelemetryDashboard.jsx`: Fixed empty state, shows mock data when DB unavailable
- Updated `FacilityOS.jsx`: Added "AI Agents" tab, updated branding

**Key Features:**
- Visual agent workflow: Detection → Diagnosis → Recommendation
- Real-time event monitoring
- Hypothesis display with confidence scores
- Action approval interface
- End-to-end workflow execution

## How to Use

### 1. Initialize TimescaleDB

```bash
# Start TimescaleDB
docker-compose up -d timescaledb

# Initialize schema
python scripts/init_timescaledb.py

# Seed sample data
python scripts/seed_sat_timeseries.py
```

### 2. Start the API

```bash
uvicorn api.main:app --reload
```

### 3. Access Agent Dashboard

1. Navigate to the web app
2. Click "AI Agents" tab
3. Click "Run Full Workflow" to see agents in action

### 4. Run Detection

```bash
curl -X POST http://localhost:8000/agents/detection/run \
  -H "Content-Type: application/json" \
  -d '{"zone_id": "ex:Zone_Main", "window_hours": 1}'
```

### 5. Use BACnet Tools

```bash
# List BACnet bindings
curl http://localhost:8000/bacnet/bindings

# Read a value
curl -X POST http://localhost:8000/bacnet/read \
  -H "Content-Type: application/json" \
  -d '{"binding_ref": "ex:FT_136276_air-temp_bacnetRef"}'

# Propose a write (requires approval)
curl -X POST http://localhost:8000/bacnet/write/propose \
  -H "Content-Type: application/json" \
  -d '{
    "binding_ref": "ex:FT_136276_air-temp_bacnetRef",
    "new_value": 22.0,
    "reason": "Adjust setpoint for comfort"
  }'
```

## Architecture Highlights

### Why This is Novel

1. **Semantic Foundation**: Multi-ontology RDF graph (IFC-LD + 223P + Brick + SSN/SOSA + QUDT)
2. **Agent-Based Operations**: Not just chat - actual building management agents
3. **Safety-First Control**: All control operations validated and gated
4. **Explainable AI**: Every recommendation traceable through graph + timeseries
5. **Standards-Based**: Open RDF/SPARQL/JSON-LD, not proprietary

### How It Disrupts Incumbent IWMS

| Aspect | Legacy IWMS | This Platform |
|--------|-------------|---------------|
| **Data Entry** | Manual forms | Automated from IFC + semantic overlays |
| **Issue Detection** | Reactive (user reports) | Proactive (agents monitor) |
| **Diagnosis** | Manual investigation | AI-generated hypotheses |
| **Actions** | Manual work orders | Agent-proposed, validated actions |
| **Integration** | Proprietary APIs | Open semantic standards |
| **Explainability** | Limited | Full traceability through graph |

## Next Steps for Full Implementation

1. **State Estimation**: Add Kalman filters for data assimilation
2. **Surrogate Models**: Neural operators for fast predictions
3. **Uncertainty Quantification**: SBI for confidence intervals
4. **External System Integration**: Workday, Maximo, EBS, Office365
5. **Control Algorithms**: MPC, reinforcement learning
6. **Real BACnet Gateway**: Connect to actual BACnet networks

## Files Created/Modified

### New Files
- `tools/graph_tools.py` - Graph query abstractions
- `tools/timeseries_tools.py` - Telemetry query abstractions
- `tools/bacnet_tools.py` - BACnet control abstractions
- `agents/detection_agent.py` - Detection agent
- `agents/diagnosis_agent.py` - Diagnosis agent
- `agents/recommendation_agent.py` - Recommendation agent
- `api/agents.py` - Agent API endpoints
- `api/bacnet.py` - BACnet API endpoints
- `api/graphdb.py` - GraphDB API endpoints
- `api/telemetry.py` - Telemetry API endpoints (updated)
- `ui/src/components/AgentDashboard.jsx` - Agent dashboard UI
- `ui/src/components/TelemetryDashboard.jsx` - Telemetry dashboard (updated)
- `scripts/init_timescaledb.py` - TimescaleDB initialization script
- `AGENT_ARCHITECTURE.md` - Architecture documentation

### Modified Files
- `api/main.py` - Registered new routers
- `ui/src/FacilityOS.jsx` - Added agent dashboard, updated branding
- `CODE_EXPLANATION.md` - Existing documentation

## Testing the Architecture

1. **Start services:**
   ```bash
   docker-compose up -d timescaledb
   python scripts/init_timescaledb.py
   python scripts/seed_sat_timeseries.py
   ```

2. **Start API:**
   ```bash
   uvicorn api.main:app --reload
   ```

3. **Access web app:**
   - Navigate to http://localhost:5173
   - Click "AI Agents" tab
   - Click "Run Full Workflow"
   - Observe: Detection → Diagnosis → Recommendation pipeline

4. **Check telemetry:**
   - Click "Live Telemetry" tab
   - Should show mock data if TimescaleDB is empty
   - Real data appears after seeding

5. **Test BACnet:**
   - Click "AI Agents" tab
   - Run workflow to generate recommendations
   - Recommendations may include BACnet actions requiring approval


