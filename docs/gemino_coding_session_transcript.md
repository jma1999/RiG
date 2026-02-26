# Gemino IWMS — Coding Session Transcript

*Development transcript reconstructed from the `gemino-iwms` codebase.*

---

## Project Overview

**Gemino IWMS** (AI-Native Integrated Workplace Management System) is a facility management dashboard with an AI chat agent. It uses a semantic knowledge graph (IFC/Brick/ASHRAE 223P) and Gemini for natural-language interaction with building data.

**Stack:** React 19, TypeScript, Vite 6, Tailwind CSS, D3.js, Recharts, Google Gemini API (`@google/genai`)

---

## Session 1: Project Scaffolding

### 1.1 Initialize Vite + React + TypeScript

```bash
npm create vite@latest gemino-iwms -- --template react-ts
cd gemino-iwms
npm install
```

### 1.2 Add Dependencies

```bash
npm install @google/genai react-dom recharts lucide-react d3
npm install -D @types/node @vitejs/plugin-react typescript vite
```

**Dependencies added:**
- `@google/genai` — Gemini API for chat + function calling
- `recharts` — Area/Bar charts for telemetry and energy
- `lucide-react` — Icons (Database, Activity, Wrench, Zap, etc.)
- `d3` — Force-directed graph visualization

### 1.3 Configure Vite

- Port 3000, host `0.0.0.0` for local dev
- Env: `GEMINI_API_KEY` / `API_KEY` injected via `define`
- Path alias: `@` → project root

### 1.4 Tailwind + Custom Theme

- CDN Tailwind in `index.html`
- Custom `nexus` palette: `900`–`500`, `accent` (#00f0ff), `success`, `warning`, `danger`
- Fonts: Inter (sans), JetBrains Mono (mono)
- Custom scrollbar styling

---

## Session 2: Type System & Constants

### 2.1 Define Types (`types.ts`)

- **GraphNode** — id, label, type (Asset|Space|Sensor|Controller|Zone), ontologyRef, status
- **GraphLink** — source, target, relationship
- **GraphData** — nodes, links
- **TelemetrySeries** — id, name, unit, data (timestamp/value)
- **Alert** — id, assetId, message, severity, timestamp
- **MaintenanceTask** — id, assetId, task, reason, scheduledDate, priority, status
- **ChatMessage** — id, role, content, timestamp, toolInvocation
- **AppState** — currentView, graphData, telemetryData, selectedNodeId, isLoading, alerts, maintenanceTasks, energySavings

### 2.2 Mock Data (`constants.ts`)

**INITIAL_GRAPH** — 9 nodes, 9 links:
- Building (BLDG-01) → Floor 1 → East Zone
- AHU-01, VAV-101, Temp Sensor 101, Set Point 101, Chiller 01, Cooling Tower 01
- Relationships: `ifc:contains`, `brick:hasPart`, `brick:feeds`, `brick:controls`, `brick:isPointOf`, `brick:feedsChilledWater`
- Status: Z-EAST and AHU-01 set to `warning` for demo anomalies

**generateTelemetry()** — 25-hour mock time series with sine + noise; supports Temperature, Energy, AirFlow metrics

**SYSTEM_INSTRUCTION** — System prompt for Gemini:
- Role: GEMINO IWMS Agent
- Backend: RDF Knowledge Graph (IFC, Brick, ASHRAE 223P)
- Tools: queryGraph, getTelemetry, detectAnomalies, scheduleMaintenance, optimizeEnergy
- Tone: Professional, technical, concise
- Guidance: Use detectAnomalies before scheduleMaintenance; use optimizeEnergy for efficiency questions

---

## Session 3: Gemini Service & Tool Definitions

### 3.1 GeminiService (`services/geminiService.ts`)

- Model: `gemini-2.5-flash`
- `sendMessage(history, message, toolHandlers)` — chat with function calling
- If API key missing → return error message

### 3.2 Tool Declarations (FunctionDeclaration)

1. **queryGraph** — query, depth → search knowledge graph
2. **getTelemetry** — assetId, metric → time-series data
3. **detectAnomalies** — assetId → spectral/anomaly analysis
4. **scheduleMaintenance** — assetId, task, reason, priority → work order
5. **optimizeEnergy** — strategy, targetZone → BACnet optimization

### 3.3 Tool Execution Flow

- On `functionCalls` from response → invoke handlers → send tool outputs back → get final text

---

## Session 4: App Shell & Layout

### 4.1 App Structure (`App.tsx`)

Three-column layout:
1. **Left:** Narrow sidebar (16px) — nav icons (Graph, Data, Ops, Energy), Bell, Settings
2. **Center:** Chat panel (450px) — Gemino AI header, ChatInterface
3. **Right:** Canvas — header with search + stats (Health 98.5%, Savings), viewport for panels

### 4.2 Tool Handlers (in App)

- **onQueryGraph** — filter nodes by query, expand links, update graphData, switch to graph view
- **onGetTelemetry** — call `generateTelemetry()`, set telemetryData, switch to telemetry view
- **onDetectAnomalies** — 50% chance if node is `warning`; create Alert, switch to maintenance
- **onScheduleMaintenance** — create MaintenanceTask (+2 days), switch to maintenance
- **onOptimizeEnergy** — increment energySavings by 350, switch to energy view

### 4.3 View Routing

- `renderContent()` switches on `currentView`: graph | telemetry | maintenance | energy
- Node click on Sensor → auto-load telemetry and switch view

---

## Session 5: UI Components

### 5.1 ChatInterface (`components/ChatInterface.tsx`)

- Empty state: "Hello, Manager", Gemino AI intro, 3 suggestion buttons
- Message list: user (right, nexus-700 bubble), model (left, slate text)
- Tool invocation badge: "Action: queryGraph, getTelemetry"
- Loading: bouncing dots + "Gemino AI" label
- Input: rounded, focus ring, Enter to send, disabled when loading
- Footer: "AI can make mistakes. Verify critical operations."

### 5.2 KnowledgeGraph (`components/KnowledgeGraph.tsx`)

- D3 force simulation: link, charge, center, collide
- Nodes: circle radius by type (Asset 12px, others 8px); fill by status (warning=amber, critical=red, nominal=cyan/green)
- Links: gray stroke, arrow markers
- Labels: monospace, 10px
- Draggable nodes
- Legend: Asset, Sensor/Point, Warning

### 5.3 TelemetryPanel (`components/TelemetryPanel.tsx`)

- Empty: "No telemetry stream selected" + hint
- With data: Recharts AreaChart, gradient fill, CartesianGrid, Tooltip
- Header: name, "Live Stream", current value + unit

### 5.4 MaintenancePanel (`components/MaintenancePanel.tsx`)

- Header: "PREDICTIVE MAINTENANCE OPS", Active Alerts count, Scheduled count
- Two columns: Active Anomalies (alert cards), Scheduled Tasks (task cards)
- Empty states: "System Nominal" / "No pending maintenance tasks"

### 5.5 EnergyPanel (`components/EnergyPanel.tsx`)

- Header: "ENERGY OPTIMIZATION", savings badge
- BarChart: baseline vs optimized load (mock 7 time points)
- Strategy cards: Trim & Respond, Optimal Start, 12.4% Load Reduction

---

## Session 6: Polish & Metadata

### 6.1 Branding

- Logo: Infinity icon in gradient (nexus-accent → blue-600)
- Title: "ge∞ino" with "AGENT" badge
- Page title: "Gemino IWMS | AI-Native Property Intelligence"

### 6.2 metadata.json

```json
{
  "name": "Gemino IWMS",
  "description": "AI-Native Integrated Workplace Management System leveraging Semantic Knowledge Graphs (IFC/Brick/ASHRAE) for autonomous building operations and cost optimization."
}
```

### 6.3 README

- Run: `npm install`, set `GEMINI_API_KEY` in `.env.local`, `npm run dev`
- Link to AI Studio app

---

## File Structure (Final)

```
gemino-iwms/
├── App.tsx
├── index.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── metadata.json
├── constants.ts
├── types.ts
├── .env.local
├── .gitignore
├── components/
│   ├── ChatInterface.tsx
│   ├── KnowledgeGraph.tsx
│   ├── TelemetryPanel.tsx
│   ├── MaintenancePanel.tsx
│   └── EnergyPanel.tsx
└── services/
    └── geminiService.ts
```

---

## Run Instructions

```bash
cd gemino-iwms
npm install
# Set GEMINI_API_KEY in .env.local
npm run dev
# → http://localhost:3000
```

---

*Transcript generated from codebase analysis. Original coding session history is not available.*
