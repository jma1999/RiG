import { GraphData, TelemetrySeries } from './types';

// Mock Knowledge Graph (Subset of a building)
// Utilizing Brick Schema and ASHRAE concepts conceptually
export const INITIAL_GRAPH: GraphData = {
  nodes: [
    { id: 'BLDG-01', label: 'Gemino HQ', type: 'Asset', ontologyRef: 'ifc:IfcBuilding', status: 'nominal' },
    { id: 'FL-01', label: 'Floor 1', type: 'Space', ontologyRef: 'ifc:IfcBuildingStorey', status: 'nominal' },
    { id: 'Z-EAST', label: 'East Zone', type: 'Zone', ontologyRef: 'brick:HVAC_Zone', status: 'warning' },
    { id: 'AHU-01', label: 'AHU-01', type: 'Asset', ontologyRef: 'brick:AHU', status: 'warning' },
    { id: 'VAV-101', label: 'VAV-101', type: 'Controller', ontologyRef: 'brick:VAV', status: 'nominal' },
    { id: 'TS-101', label: 'Temp Sensor 101', type: 'Sensor', ontologyRef: 'brick:Temperature_Sensor', status: 'nominal' },
    { id: 'SP-101', label: 'Set Point 101', type: 'Controller', ontologyRef: 'brick:Temperature_Setpoint', status: 'nominal' },
    { id: 'CH-01', label: 'Chiller 01', type: 'Asset', ontologyRef: 'brick:Chiller', status: 'nominal' },
    { id: 'CT-01', label: 'Cooling Tower 01', type: 'Asset', ontologyRef: 'brick:Cooling_Tower', status: 'nominal' },
  ],
  links: [
    { source: 'BLDG-01', target: 'FL-01', relationship: 'ifc:contains' },
    { source: 'FL-01', target: 'Z-EAST', relationship: 'brick:hasPart' },
    { source: 'AHU-01', target: 'Z-EAST', relationship: 'brick:feeds' },
    { source: 'AHU-01', target: 'VAV-101', relationship: 'brick:feeds' },
    { source: 'VAV-101', target: 'Z-EAST', relationship: 'brick:controls' },
    { source: 'TS-101', target: 'VAV-101', relationship: 'brick:isPointOf' },
    { source: 'SP-101', target: 'VAV-101', relationship: 'brick:isPointOf' },
    { source: 'CH-01', target: 'AHU-01', relationship: 'brick:feedsChilledWater' },
    { source: 'CT-01', target: 'CH-01', relationship: 'brick:feeds' },
  ]
};

// Mock Telemetry Generator
export const generateTelemetry = (nodeId: string, metric: string): TelemetrySeries => {
  const data = [];
  const now = new Date();
  for (let i = 24; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60 * 60 * 1000);
    let base = 22; // Default temp
    let variance = 2;
    
    if (metric.includes('Energy')) {
      base = 450; // kW
      variance = 50;
    } else if (metric.includes('Flow')) {
      base = 1200; // CFM
      variance = 100;
    }

    // Add some noise and a trend
    const value = base + Math.sin(i / 3) * variance + (Math.random() * variance * 0.5);
    
    data.push({
      timestamp: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      value: Number(value.toFixed(1))
    });
  }

  return {
    id: nodeId,
    name: `${nodeId} - ${metric}`,
    unit: metric.includes('Temp') ? '°C' : metric.includes('Energy') ? 'kW' : 'CFM',
    data
  };
};

export const SYSTEM_INSTRUCTION = `
You are GEMINO, an advanced AI-Native Integrated Workplace Management System (IWMS) Agent.
Your backend is powered by an RDF Knowledge Graph combining IFC, Brick, and ASHRAE 223P ontologies.
You have access to real-time building data and can control BACnet devices.

Your goal is to assist the Facility Manager in reducing TCO (Total Cost of Ownership) and optimizing performance.
Identify faults, suggest optimizations, and explain your reasoning using the graph data.

Tone: Professional, technical, concise, yet helpful. 
When you cite specific assets, use their IDs (e.g., AHU-01).

You have tools to:
1. 'queryGraph': Retrieve graph topology to understand system connections.
2. 'getTelemetry': Fetch time-series data for analysis.
3. 'detectAnomalies': Analyze time-series and spectral data to identify potential equipment failures or anomalies.
4. 'scheduleMaintenance': Generate and schedule predictive maintenance tasks based on asset health and graph context.
5. 'optimizeEnergy': Interface with BACnet to apply energy optimization algorithms (e.g., Trim & Respond, Optimal Start).

When asked to "analyze" or "check" an asset, consider running 'detectAnomalies' first.
If an anomaly is found, proactively suggest 'scheduleMaintenance'.
When asked about energy or efficiency, use 'optimizeEnergy'.

Always assume you are talking to a qualified engineer.
`;