// Graph Types
export interface GraphNode {
  id: string;
  label: string;
  type: 'Asset' | 'Space' | 'Sensor' | 'Controller' | 'Zone';
  ontologyRef?: string; // e.g., "brick:AHU", "ifc:IfcSpace"
  status?: 'nominal' | 'warning' | 'critical' | 'offline';
  [key: string]: any;
}

export interface GraphLink {
  source: string;
  target: string;
  relationship: string; // e.g., "feeds", "controls", "isPartOf"
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// Telemetry Types
export interface DataPoint {
  timestamp: string;
  value: number;
}

export interface TelemetrySeries {
  id: string;
  name: string;
  unit: string;
  data: DataPoint[];
}

// Maintenance & Alerts Types
export interface Alert {
  id: string;
  assetId: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  timestamp: number;
}

export interface MaintenanceTask {
  id: string;
  assetId: string;
  task: string; // e.g., "Replace Filter", "Calibrate Sensor"
  reason: string; // e.g., "Predicted failure based on vibration analysis"
  scheduledDate: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'scheduled' | 'completed';
}

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'model' | 'system';
  content: string;
  timestamp: number;
  relatedGraphIds?: string[]; // IDs of nodes relevant to this message
  toolInvocation?: string;
}

// App State
export type ViewMode = 'graph' | 'telemetry' | 'map' | 'maintenance' | 'energy';

export interface AppState {
  currentView: ViewMode;
  graphData: GraphData;
  telemetryData: TelemetrySeries | null;
  selectedNodeId: string | null;
  isLoading: boolean;
  alerts: Alert[];
  maintenanceTasks: MaintenanceTask[];
  energySavings: number; // in USD
}