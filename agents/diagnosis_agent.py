"""
Diagnosis Agent - Analyzes events and determines root causes.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from tools.graph_tools import GraphTools
from tools.timeseries_tools import TimeseriesTools
from agents.detection_agent import DetectionEvent


@dataclass
class Hypothesis:
    """Diagnostic hypothesis."""
    hypothesis_id: str
    description: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str]
    suggested_tests: List[str]
    likelihood: str  # "low", "medium", "high"


@dataclass
class DiagnosisResult:
    """Complete diagnosis result."""
    event_id: str
    timestamp: datetime
    hypotheses: List[Hypothesis]
    primary_hypothesis: Optional[Hypothesis]
    context: Dict[str, Any]


class DiagnosisAgent:
    """
    Diagnosis agent that analyzes events and determines root causes.
    
    Uses graph context, timeseries data, and LLM reasoning to generate
    ranked hypotheses with confidence scores.
    """
    
    def __init__(
        self,
        graph_tools: GraphTools,
        timeseries_tools: TimeseriesTools,
        llm_client=None
    ):
        self.graph_tools = graph_tools
        self.timeseries_tools = timeseries_tools
        self.llm_client = llm_client
    
    def diagnose_event(self, event: DetectionEvent) -> DiagnosisResult:
        """
        Diagnose a detection event.
        
        Args:
            event: Detection event to diagnose
            
        Returns:
            Diagnosis result with ranked hypotheses
        """
        # Gather context
        context = self._gather_context(event)
        
        # Generate hypotheses based on event type
        if event.event_type == "comfort_violation":
            hypotheses = self._diagnose_comfort_violation(event, context)
        elif event.event_type == "stability_issue":
            hypotheses = self._diagnose_stability_issue(event, context)
        else:
            hypotheses = self._diagnose_generic(event, context)
        
        # Rank hypotheses by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        primary = hypotheses[0] if hypotheses else None
        
        return DiagnosisResult(
            event_id=event.event_id,
            timestamp=datetime.now(),
            hypotheses=hypotheses,
            primary_hypothesis=primary,
            context=context
        )
    
    def _gather_context(self, event: DetectionEvent) -> Dict[str, Any]:
        """Gather context for diagnosis."""
        context = {
            "event": {
                "type": event.event_type,
                "severity": event.severity,
                "description": event.description,
                "metrics": event.metrics
            }
        }
        
        # Get zone context if available
        if event.zone_id:
            try:
                zone_context = self.graph_tools.get_zone_context(event.zone_id)
                context["zone"] = {
                    "id": zone_context.zone_id,
                    "name": zone_context.zone_name,
                    "equipment_count": len(zone_context.equipment),
                    "points_count": len(zone_context.points)
                }
                
                # Get control chain
                control_chain = self.graph_tools.get_control_chain(event.zone_id)
                context["control_chain"] = control_chain
            except Exception as e:
                context["zone_error"] = str(e)
        
        # Get equipment context if available
        if event.equipment_id:
            try:
                equip_context = self.graph_tools.get_equipment_context(event.equipment_id)
                context["equipment"] = {
                    "id": equip_context.equipment_id,
                    "name": equip_context.equipment_name,
                    "type": equip_context.equipment_type,
                    "points_count": len(equip_context.points)
                }
            except Exception as e:
                context["equipment_error"] = str(e)
        
        # Get timeseries data for the point
        if event.point_id:
            try:
                end = datetime.now()
                start = end - timedelta(hours=24)
                data = self.timeseries_tools.get_timeseries(event.point_id, start, end)
                context["timeseries"] = {
                    "data_points": len(data),
                    "recent_values": [d.value for d in data[-10:]] if data else []
                }
            except Exception as e:
                context["timeseries_error"] = str(e)
        
        return context
    
    def _diagnose_comfort_violation(
        self,
        event: DetectionEvent,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses for comfort violations."""
        hypotheses = []
        
        temp = event.metrics.get("temperature", 0)
        deviation = event.metrics.get("deviation", 0)
        
        # Hypothesis 1: Damper stuck
        if temp > 26.0:  # Overheating
            hypotheses.append(Hypothesis(
                hypothesis_id="damper_stuck_closed",
                description="Supply damper may be stuck closed, preventing adequate cooling",
                confidence=0.7,
                evidence=[
                    f"Zone temperature {temp:.1f}°C exceeds comfort maximum",
                    "Control chain includes damper control points"
                ],
                suggested_tests=[
                    "Check damper command vs feedback position",
                    "Verify damper actuator is responding",
                    "Check for schedule override"
                ],
                likelihood="high"
            ))
        
        # Hypothesis 2: Supply air temperature issue
        hypotheses.append(Hypothesis(
            hypothesis_id="supply_air_temp_issue",
            description="Supply air temperature from AHU may be incorrect",
            confidence=0.6,
            evidence=[
                f"Zone temperature deviation: {deviation:.1f}°C",
                "Upstream AHU supply temperature affects zone"
            ],
            suggested_tests=[
                "Check AHU supply air temperature setpoint",
                "Verify AHU cooling/heating coil operation",
                "Check for AHU faults"
            ],
            likelihood="medium"
        ))
        
        # Hypothesis 3: Schedule override
        hypotheses.append(Hypothesis(
            hypothesis_id="schedule_override",
            description="Zone schedule may be overridden or incorrect",
            confidence=0.4,
            evidence=[
                "Temperature outside comfort band during occupied hours",
                "No equipment faults detected"
            ],
            suggested_tests=[
                "Check zone schedule in BMS",
                "Verify occupancy schedule",
                "Check for manual overrides"
            ],
            likelihood="low"
        ))
        
        return hypotheses
    
    def _diagnose_stability_issue(
        self,
        event: DetectionEvent,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses for stability issues."""
        hypotheses = []
        
        change_rate = event.metrics.get("change_rate", 0)
        
        # Hypothesis 1: Control loop oscillation
        hypotheses.append(Hypothesis(
            hypothesis_id="control_oscillation",
            description="Control loop may be oscillating due to aggressive tuning",
            confidence=0.7,
            evidence=[
                f"High variability: {change_rate:.1%} of readings show >1°C changes",
                "Rapid on/off cycling pattern"
            ],
            suggested_tests=[
                "Review PID controller tuning parameters",
                "Check for sensor noise or drift",
                "Verify control loop deadband settings"
            ],
            likelihood="high"
        ))
        
        # Hypothesis 2: Sensor fault
        hypotheses.append(Hypothesis(
            hypothesis_id="sensor_fault",
            description="Temperature sensor may be faulty or noisy",
            confidence=0.5,
            evidence=[
                "Unstable readings inconsistent with zone behavior",
                "High change rate suggests sensor issues"
            ],
            suggested_tests=[
                "Compare with adjacent zone sensors",
                "Check sensor calibration",
                "Verify sensor wiring and connections"
            ],
            likelihood="medium"
        ))
        
        return hypotheses
    
    def _diagnose_generic(
        self,
        event: DetectionEvent,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generic diagnosis for unknown event types."""
        return [
            Hypothesis(
                hypothesis_id="generic_issue",
                description="General system issue detected",
                confidence=0.3,
                evidence=[event.description],
                suggested_tests=["Review system logs", "Check for related events"],
                likelihood="low"
            )
        ]

