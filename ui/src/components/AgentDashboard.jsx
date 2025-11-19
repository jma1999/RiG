import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/env";
import { 
  Activity, 
  Brain, 
  Lightbulb, 
  AlertTriangle, 
  CheckCircle2,
  Play,
  RefreshCw,
  Zap
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function AgentDashboard() {
  const [events, setEvents] = useState([]);
  const [diagnoses, setDiagnoses] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [workflowRunning, setWorkflowRunning] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null);

  useEffect(() => {
    loadRecentEvents();
    const interval = setInterval(loadRecentEvents, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadRecentEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/detection/events?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch (error) {
      console.error("Failed to load events:", error);
    }
  };

  const runDetection = async () => {
    try {
      setWorkflowRunning(true);
      const res = await fetch(`${API_BASE}/agents/detection/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          zone_id: "ex:Zone_Main",
          window_hours: 1
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
        
        // Auto-diagnose first event if any
        if (data.events && data.events.length > 0) {
          await diagnoseEvent(data.events[0]);
        }
      }
    } catch (error) {
      console.error("Detection failed:", error);
    } finally {
      setWorkflowRunning(false);
    }
  };

  const diagnoseEvent = async (event) => {
    try {
      setSelectedEvent(event);
      const res = await fetch(`${API_BASE}/agents/diagnosis/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(event)
      });
      
      if (res.ok) {
        const diagnosis = await res.json();
        setSelectedDiagnosis(diagnosis);
        setDiagnoses(prev => [diagnosis, ...prev].slice(0, 5));
        
        // Auto-generate recommendations
        await generateRecommendations(diagnosis);
      }
    } catch (error) {
      console.error("Diagnosis failed:", error);
    }
  };

  const generateRecommendations = async (diagnosis) => {
    try {
      const res = await fetch(`${API_BASE}/agents/recommendation/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(diagnosis)
      });
      
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data.recommendations || []);
      }
    } catch (error) {
      console.error("Recommendation generation failed:", error);
    }
  };

  const runEndToEndWorkflow = async () => {
    try {
      setWorkflowRunning(true);
      const res = await fetch(`${API_BASE}/agents/workflow/end-to-end?zone_id=ex:Zone_Main`);
      
      if (res.ok) {
        const workflow = await res.json();
        
        if (workflow.status === "complete") {
          // Update UI with workflow results
          if (workflow.workflow.detection.events_detected > 0) {
            setEvents([workflow.workflow.detection.primary_event]);
          }
          
          if (workflow.workflow.diagnosis.primary_hypothesis) {
            setSelectedDiagnosis({
              primary_hypothesis: workflow.workflow.diagnosis.primary_hypothesis
            });
          }
          
          if (workflow.workflow.recommendations.actions) {
            setRecommendations(workflow.workflow.recommendations.actions);
          }
        }
      }
    } catch (error) {
      console.error("Workflow failed:", error);
    } finally {
      setWorkflowRunning(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case "critical": return "bg-red-600 text-white";
      case "high": return "bg-orange-600 text-white";
      case "medium": return "bg-yellow-600 text-black";
      case "low": return "bg-blue-600 text-white";
      default: return "bg-gray-600 text-white";
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case "critical": return "bg-red-600 text-white";
      case "high": return "bg-orange-600 text-white";
      case "medium": return "bg-yellow-600 text-black";
      case "low": return "bg-blue-600 text-white";
      default: return "bg-gray-600 text-white";
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">
            AI Agent Operations Dashboard
          </h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Agent-based IWMS: Detection → Diagnosis → Recommendation workflow
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={runEndToEndWorkflow}
            disabled={workflowRunning}
            className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)] flex items-center gap-2"
          >
            {workflowRunning ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                Run Full Workflow
              </>
            )}
          </Button>
          <Button
            onClick={runDetection}
            disabled={workflowRunning}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Play className="h-4 w-4" />
            Run Detection
          </Button>
        </div>
      </div>

      {/* Agent Workflow Overview */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-6 w-6 text-blue-500" />
                <h3 className="font-semibold text-[var(--palantir-text-primary)]">
                  Detection Agent
                </h3>
              </div>
              <Badge className="bg-blue-600 text-white">{events.length}</Badge>
            </div>
            <p className="text-sm text-[var(--palantir-text-muted)]">
              Monitors telemetry for comfort violations, stability issues, and anomalies
            </p>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Brain className="h-6 w-6 text-purple-500" />
                <h3 className="font-semibold text-[var(--palantir-text-primary)]">
                  Diagnosis Agent
                </h3>
              </div>
              <Badge className="bg-purple-600 text-white">{diagnoses.length}</Badge>
            </div>
            <p className="text-sm text-[var(--palantir-text-muted)]">
              Analyzes events using graph context and generates ranked hypotheses
            </p>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-6 w-6 text-yellow-500" />
                <h3 className="font-semibold text-[var(--palantir-text-primary)]">
                  Recommendation Agent
                </h3>
              </div>
              <Badge className="bg-yellow-600 text-black">{recommendations.length}</Badge>
            </div>
            <p className="text-sm text-[var(--palantir-text-muted)]">
              Proposes concrete actions with safety validation and approval gates
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detection Events */}
      <Card className="palantir-card-elevated">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Detection Events
          </CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">
            Issues detected by the detection agent
          </p>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="text-center py-8 text-[var(--palantir-text-muted)]">
              No events detected. Click "Run Detection" to scan for issues.
            </div>
          ) : (
            <div className="space-y-3">
              {events.map((event) => (
                <div
                  key={event.event_id}
                  className={cn(
                    "p-4 rounded-lg border cursor-pointer transition-all",
                    selectedEvent?.event_id === event.event_id
                      ? "border-[var(--palantir-text-accent)] bg-[var(--palantir-bg-secondary)]"
                      : "border-[var(--palantir-border-primary)] hover:bg-[var(--palantir-hover)]"
                  )}
                  onClick={() => diagnoseEvent(event)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getSeverityColor(event.severity)}>
                          {event.severity}
                        </Badge>
                        <Badge variant="outline">{event.event_type}</Badge>
                      </div>
                      <p className="text-sm font-medium text-[var(--palantir-text-primary)] mb-1">
                        {event.description}
                      </p>
                      <p className="text-xs text-[var(--palantir-text-muted)]">
                        {new Date(event.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        diagnoseEvent(event);
                      }}
                    >
                      <Brain className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diagnosis Results */}
      {selectedDiagnosis && (
        <Card className="palantir-card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Diagnosis Results
            </CardTitle>
            <p className="text-sm text-[var(--palantir-text-muted)]">
              AI-generated hypotheses with confidence scores
            </p>
          </CardHeader>
          <CardContent>
            {selectedDiagnosis.primary_hypothesis && (
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <h4 className="font-semibold text-[var(--palantir-text-primary)]">
                    Primary Hypothesis
                  </h4>
                  <Badge className="bg-purple-600 text-white">
                    {(selectedDiagnosis.primary_hypothesis.confidence * 100).toFixed(0)}% confidence
                  </Badge>
                </div>
                <p className="text-sm text-[var(--palantir-text-primary)] mb-3">
                  {selectedDiagnosis.primary_hypothesis.description}
                </p>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs font-medium text-[var(--palantir-text-muted)] mb-1">
                      Evidence:
                    </p>
                    <ul className="text-xs text-[var(--palantir-text-primary)] list-disc list-inside">
                      {selectedDiagnosis.primary_hypothesis.evidence.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-[var(--palantir-text-muted)] mb-1">
                      Suggested Tests:
                    </p>
                    <ul className="text-xs text-[var(--palantir-text-primary)] list-disc list-inside">
                      {selectedDiagnosis.primary_hypothesis.suggested_tests.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
            
            {selectedDiagnosis.hypotheses && selectedDiagnosis.hypotheses.length > 1 && (
              <div>
                <h4 className="font-semibold text-[var(--palantir-text-primary)] mb-3">
                  Alternative Hypotheses
                </h4>
                <div className="space-y-2">
                  {selectedDiagnosis.hypotheses.slice(1).map((h) => (
                    <div key={h.hypothesis_id} className="p-3 bg-[var(--palantir-bg-secondary)] rounded">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-[var(--palantir-text-primary)]">
                          {h.description}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {(h.confidence * 100).toFixed(0)}%
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card className="palantir-card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5" />
              Recommended Actions
            </CardTitle>
            <p className="text-sm text-[var(--palantir-text-muted)]">
              AI-generated action plans with safety validation
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recommendations.map((rec) => (
                <div
                  key={rec.action_id}
                  className="p-4 border border-[var(--palantir-border-primary)] rounded-lg"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getPriorityColor(rec.priority)}>
                          {rec.priority}
                        </Badge>
                        <Badge variant="outline">{rec.action_type}</Badge>
                        {rec.requires_approval && (
                          <Badge className="bg-yellow-600 text-black">
                            Requires Approval
                          </Badge>
                        )}
                      </div>
                      <h4 className="font-semibold text-[var(--palantir-text-primary)] mb-2">
                        {rec.description}
                      </h4>
                      <p className="text-sm text-[var(--palantir-text-muted)] mb-3">
                        {rec.rationale}
                      </p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="text-xs font-medium text-[var(--palantir-text-muted)] mb-1">
                        Expected Impact:
                      </p>
                      <p className="text-xs text-[var(--palantir-text-primary)]">
                        {rec.expected_impact}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-[var(--palantir-text-muted)] mb-1">
                        Risks:
                      </p>
                      <ul className="text-xs text-[var(--palantir-text-primary)] list-disc list-inside">
                        {rec.risks.map((risk, i) => (
                          <li key={i}>{risk}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    {rec.requires_approval ? (
                      <>
                        <Button size="sm" variant="outline">
                          Approve
                        </Button>
                        <Button size="sm" variant="outline">
                          Reject
                        </Button>
                      </>
                    ) : (
                      <Button size="sm" className="bg-[var(--palantir-text-accent)]">
                        Execute
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

