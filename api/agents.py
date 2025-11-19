"""
Agent API endpoints - Expose agent capabilities via REST API.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from datetime import datetime, timedelta
import sys
import pathlib
import os

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
try:
    from tools.graph_tools import GraphTools
    from tools.timeseries_tools import TimeseriesTools
    from tools.bacnet_tools import BACnetTools
    from agents.detection_agent import DetectionAgent
    from agents.diagnosis_agent import DiagnosisAgent
    from agents.recommendation_agent import RecommendationAgent
    from ingest.graphdb_client import GraphDBClient
except ImportError as e:
    # Handle import errors gracefully
    print(f"Warning: Could not import agent modules: {e}")
    GraphTools = None
    TimeseriesTools = None
    BACnetTools = None
    DetectionAgent = None
    DiagnosisAgent = None
    RecommendationAgent = None
    GraphDBClient = None

router = APIRouter()

# Initialize tools and agents
_graphdb_client = None
_graph_tools = None
_timeseries_tools = None
_bacnet_tools = None
_detection_agent = None
_diagnosis_agent = None
_recommendation_agent = None


def get_agents():
    """Initialize and return agent instances."""
    global _graphdb_client, _graph_tools, _timeseries_tools, _bacnet_tools
    global _detection_agent, _diagnosis_agent, _recommendation_agent
    
    if GraphDBClient is None:
        raise HTTPException(status_code=503, detail="Agent modules not available")
    
    if _graphdb_client is None:
        _graphdb_client = GraphDBClient(
            base_url=os.getenv("GRAPHDB_URL", "http://localhost:7200"),
            repository=os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")
        )
        _graph_tools = GraphTools(_graphdb_client)
        _timeseries_tools = TimeseriesTools()
        _bacnet_tools = BACnetTools()
        _detection_agent = DetectionAgent(_graph_tools, _timeseries_tools)
        _diagnosis_agent = DiagnosisAgent(_graph_tools, _timeseries_tools)
        _recommendation_agent = RecommendationAgent(_graph_tools, _bacnet_tools)
    
    return {
        "detection": _detection_agent,
        "diagnosis": _diagnosis_agent,
        "recommendation": _recommendation_agent
    }


class DetectionRequest(BaseModel):
    zone_id: Optional[str] = None
    point_id: Optional[str] = None
    window_hours: int = 1


class DiagnosisRequest(BaseModel):
    event_id: str
    event_type: str
    severity: str
    zone_id: Optional[str] = None
    equipment_id: Optional[str] = None
    point_id: str
    description: str
    metrics: Dict[str, Any]


@router.post("/detection/run")
async def run_detection(request: DetectionRequest = Body(...)):
    """Run detection agent on specified zone or point."""
    try:
        agents = get_agents()
        detection = agents["detection"]
        
        events = []
        if request.zone_id:
            events = detection.detect_comfort_violations(
                request.zone_id,
                timedelta(hours=request.window_hours)
            )
        elif request.point_id:
            events = detection.detect_stability_issues(
                request.point_id,
                timedelta(hours=request.window_hours)
            )
        else:
            events = detection.run_detection_cycle()
        
        return {
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "zone_id": e.zone_id,
                    "equipment_id": e.equipment_id,
                    "point_id": e.point_id,
                    "description": e.description,
                    "metrics": e.metrics
                }
                for e in events
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/detection/events")
async def get_detection_events(limit: int = Query(10, ge=1, le=100)):
    """Get recent detection events."""
    try:
        agents = get_agents()
        detection = agents["detection"]
        events = detection.get_recent_events(limit)
        
        return {
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "description": e.description,
                    "metrics": e.metrics
                }
                for e in events
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.post("/diagnosis/analyze")
async def analyze_event(request: DiagnosisRequest = Body(...)):
    """Analyze a detection event and generate diagnosis."""
    try:
        from agents.detection_agent import DetectionEvent
        
        # Create detection event from request
        event = DetectionEvent(
            event_id=request.event_id,
            timestamp=datetime.now(),
            event_type=request.event_type,
            severity=request.severity,
            zone_id=request.zone_id,
            equipment_id=request.equipment_id,
            point_id=request.point_id,
            description=request.description,
            metrics=request.metrics
        )
        
        agents = get_agents()
        diagnosis = agents["diagnosis"]
        result = diagnosis.diagnose_event(event)
        
        return {
            "event_id": result.event_id,
            "timestamp": result.timestamp.isoformat(),
            "hypotheses": [
                {
                    "hypothesis_id": h.hypothesis_id,
                    "description": h.description,
                    "confidence": h.confidence,
                    "evidence": h.evidence,
                    "suggested_tests": h.suggested_tests,
                    "likelihood": h.likelihood
                }
                for h in result.hypotheses
            ],
            "primary_hypothesis": {
                "hypothesis_id": result.primary_hypothesis.hypothesis_id,
                "description": result.primary_hypothesis.description,
                "confidence": result.primary_hypothesis.confidence,
                "evidence": result.primary_hypothesis.evidence,
                "suggested_tests": result.primary_hypothesis.suggested_tests,
                "likelihood": result.primary_hypothesis.likelihood
            } if result.primary_hypothesis else None,
            "context": result.context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


@router.post("/recommendation/generate")
async def generate_recommendations(diagnosis_result: Dict[str, Any] = Body(...)):
    """Generate recommendations based on a diagnosis."""
    try:
        from agents.diagnosis_agent import DiagnosisResult, Hypothesis
        
        # Reconstruct diagnosis result from request
        hypotheses = [
            Hypothesis(
                hypothesis_id=h["hypothesis_id"],
                description=h["description"],
                confidence=h["confidence"],
                evidence=h["evidence"],
                suggested_tests=h["suggested_tests"],
                likelihood=h["likelihood"]
            )
            for h in diagnosis_result.get("hypotheses", [])
        ]
        
        primary = None
        if diagnosis_result.get("primary_hypothesis"):
            ph = diagnosis_result["primary_hypothesis"]
            primary = Hypothesis(
                hypothesis_id=ph["hypothesis_id"],
                description=ph["description"],
                confidence=ph["confidence"],
                evidence=ph["evidence"],
                suggested_tests=ph["suggested_tests"],
                likelihood=ph["likelihood"]
            )
        
        diagnosis = DiagnosisResult(
            event_id=diagnosis_result["event_id"],
            timestamp=datetime.fromisoformat(diagnosis_result["timestamp"]),
            hypotheses=hypotheses,
            primary_hypothesis=primary,
            context=diagnosis_result.get("context", {})
        )
        
        agents = get_agents()
        recommendation = agents["recommendation"]
        recommendations = recommendation.generate_recommendations(diagnosis)
        
        return {
            "recommendations": [
                {
                    "action_id": r.action_id,
                    "action_type": r.action_type,
                    "description": r.description,
                    "priority": r.priority,
                    "affected_zones": r.affected_zones,
                    "affected_equipment": r.affected_equipment,
                    "rationale": r.rationale,
                    "expected_impact": r.expected_impact,
                    "risks": r.risks,
                    "requires_approval": r.requires_approval
                }
                for r in recommendations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")


@router.get("/workflow/end-to-end")
async def run_end_to_end_workflow(zone_id: str = Query(...)):
    """
    Run complete agent workflow: Detection → Diagnosis → Recommendation.
    
    This demonstrates the AI-native architecture in action.
    """
    try:
        agents = get_agents()
        
        # Step 1: Detection
        detection = agents["detection"]
        events = detection.detect_comfort_violations(zone_id)
        
        if not events:
            return {
                "status": "no_issues",
                "message": "No issues detected in zone",
                "zone_id": zone_id
            }
        
        # Step 2: Diagnosis (use first event)
        event = events[0]
        diagnosis = agents["diagnosis"]
        diagnosis_result = diagnosis.diagnose_event(event)
        
        # Step 3: Recommendation
        recommendation = agents["recommendation"]
        recommendations = recommendation.generate_recommendations(diagnosis_result)
        
        return {
            "status": "complete",
            "zone_id": zone_id,
            "workflow": {
                "detection": {
                    "events_detected": len(events),
                    "primary_event": {
                        "event_id": event.event_id,
                        "type": event.event_type,
                        "severity": event.severity,
                        "description": event.description
                    }
                },
                "diagnosis": {
                    "hypotheses_count": len(diagnosis_result.hypotheses),
                    "primary_hypothesis": {
                        "description": diagnosis_result.primary_hypothesis.description if diagnosis_result.primary_hypothesis else None,
                        "confidence": diagnosis_result.primary_hypothesis.confidence if diagnosis_result.primary_hypothesis else None
                    }
                },
                "recommendations": {
                    "actions_count": len(recommendations),
                    "actions": [
                        {
                            "type": r.action_type,
                            "description": r.description,
                            "priority": r.priority,
                            "requires_approval": r.requires_approval
                        }
                        for r in recommendations
                    ]
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

