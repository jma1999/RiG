import { GoogleGenAI, FunctionDeclaration, Type } from "@google/genai";
import { SYSTEM_INSTRUCTION } from '../constants';

// Tools Definitions
const queryGraphTool: FunctionDeclaration = {
  name: "queryGraph",
  description: "Search the knowledge graph for assets, spaces, or systems matching a query or connected to a root node.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      query: { type: Type.STRING, description: "Search term or Asset ID" },
      depth: { type: Type.NUMBER, description: "Depth of traversal (default 1)" }
    },
    required: ["query"]
  }
};

const getTelemetryTool: FunctionDeclaration = {
  name: "getTelemetry",
  description: "Get historical time-series data for a specific asset and metric.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      assetId: { type: Type.STRING, description: "The ID of the asset (e.g., AHU-01)" },
      metric: { type: Type.STRING, description: "Metric type (Temperature, Energy, AirFlow)" }
    },
    required: ["assetId", "metric"]
  }
};

const detectAnomaliesTool: FunctionDeclaration = {
  name: "detectAnomalies",
  description: "Analyze asset time-series data for anomalies and potential failures.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      assetId: { type: Type.STRING, description: "The ID of the asset to analyze" }
    },
    required: ["assetId"]
  }
};

const scheduleMaintenanceTool: FunctionDeclaration = {
  name: "scheduleMaintenance",
  description: "Schedule a predictive maintenance task for an asset.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      assetId: { type: Type.STRING, description: "The ID of the asset" },
      task: { type: Type.STRING, description: "Description of the task (e.g., 'Replace bearings')" },
      reason: { type: Type.STRING, description: "Reason for the task (e.g., 'Vibration anomaly')" },
      priority: { type: Type.STRING, description: "Priority level (high, medium, low)" }
    },
    required: ["assetId", "task", "reason"]
  }
};

const optimizeEnergyTool: FunctionDeclaration = {
  name: "optimizeEnergy",
  description: "Run energy optimization algorithms via BACnet interface.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      strategy: { type: Type.STRING, description: "Optimization strategy (e.g., 'Trim & Respond', 'Night Purge')" },
      targetZone: { type: Type.STRING, description: "Target zone or system ID" }
    },
    required: ["strategy"]
  }
};

export class GeminiService {
  private client: GoogleGenAI;
  private model: string;

  constructor() {
    const apiKey = process.env.API_KEY || ''; 
    this.client = new GoogleGenAI({ apiKey });
    this.model = 'gemini-2.5-flash';
  }

  async sendMessage(
    history: { role: 'user' | 'model'; parts: { text: string }[] }[],
    message: string,
    toolHandlers: {
      onQueryGraph: (args: any) => Promise<any>;
      onGetTelemetry: (args: any) => Promise<any>;
      onDetectAnomalies: (args: any) => Promise<any>;
      onScheduleMaintenance: (args: any) => Promise<any>;
      onOptimizeEnergy: (args: any) => Promise<any>;
    }
  ) {
    if (!process.env.API_KEY) {
      return {
        text: "Error: API Key is missing. Please set the API_KEY environment variable.",
        toolCalls: []
      };
    }

    try {
      const chat = this.client.chats.create({
        model: this.model,
        config: {
          systemInstruction: SYSTEM_INSTRUCTION,
          tools: [{ 
            functionDeclarations: [
              queryGraphTool, 
              getTelemetryTool, 
              detectAnomaliesTool, 
              scheduleMaintenanceTool, 
              optimizeEnergyTool
            ] 
          }],
        },
        history: history,
      });

      // Fix: chat.sendMessage returns the response object directly
      const response = await chat.sendMessage({ message });
      
      let finalResponseText = response.text || "";
      const toolCalls = response.functionCalls || [];

      if (toolCalls.length > 0) {
        const toolOutputs = [];
        
        for (const call of toolCalls) {
          let output = { result: "Success" };
          
          if (call.name === "queryGraph") {
            output = await toolHandlers.onQueryGraph(call.args);
          } else if (call.name === "getTelemetry") {
            output = await toolHandlers.onGetTelemetry(call.args);
          } else if (call.name === "detectAnomalies") {
            output = await toolHandlers.onDetectAnomalies(call.args);
          } else if (call.name === "scheduleMaintenance") {
            output = await toolHandlers.onScheduleMaintenance(call.args);
          } else if (call.name === "optimizeEnergy") {
            output = await toolHandlers.onOptimizeEnergy(call.args);
          }
          
          toolOutputs.push({
            functionResponse: {
              name: call.name,
              response: output
            }
          });
        }

        const finalResult = await chat.sendMessage({
             message: toolOutputs
        });
        
        finalResponseText = finalResult.text || finalResponseText;
      }

      return {
        text: finalResponseText,
        toolCalls: toolCalls.map(tc => tc.name)
      };

    } catch (error) {
      console.error("Gemini Error:", error);
      return {
        text: "I encountered an error processing your request. Please try again.",
        toolCalls: []
      };
    }
  }
}

export const geminiService = new GeminiService();