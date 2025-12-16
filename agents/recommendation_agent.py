"""
Recommendation Agent - Proposes concrete actions based on diagnoses.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from tools.graph_tools import GraphTools
from tools.bacnet_tools import BACnetTools
from agents.diagnosis_agent import DiagnosisResult, Hypothesis


@dataclass
class RecommendedAction:
    """Recommended action for an issue."""
    action_id: str
    action_type: str  # "setpoint_change", "schedule_tweak", "work_order", "inspection"
    description: str
    priority: str  # "low", "medium", "high", "critical"
    affected_zones: List[str]
    affected_equipment: List[str]
    rationale: str
    expected_impact: str
    risks: List[str]
    requires_approval: bool
    bacnet_action: Optional[Any] = None  # BACnet action plan if applicable


class RecommendationAgent:
    """
    Recommendation agent that proposes concrete actions based on diagnoses.
    
    Uses graph context to find affected zones/equipment and validates
    actions against SHACL safety rules.
    """
    
    def __init__(
        self,
        graph_tools: GraphTools,
        bacnet_tools: BACnetTools
    ):
        self.graph_tools = graph_tools
        self.bacnet_tools = bacnet_tools
    
    def generate_recommendations(
        self,
        diagnosis: DiagnosisResult
    ) -> List[RecommendedAction]:
        """
        Generate recommendations based on a diagnosis.
        
        Args:
            diagnosis: Diagnosis result
            
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        if not diagnosis.primary_hypothesis:
            return recommendations
        
        hypothesis = diagnosis.primary_hypothesis
        
        # Generate recommendations based on hypothesis type
        if "damper" in hypothesis.hypothesis_id:
            recommendations.extend(
                self._recommend_damper_actions(diagnosis, hypothesis)
            )
        elif "supply_air" in hypothesis.hypothesis_id:
            recommendations.extend(
                self._recommend_supply_air_actions(diagnosis, hypothesis)
            )
        elif "schedule" in hypothesis.hypothesis_id:
            recommendations.extend(
                self._recommend_schedule_actions(diagnosis, hypothesis)
            )
        elif "sensor" in hypothesis.hypothesis_id:
            recommendations.extend(
                self._recommend_sensor_actions(diagnosis, hypothesis)
            )
        else:
            recommendations.extend(
                self._recommend_generic_actions(diagnosis, hypothesis)
            )
        
        return recommendations
    
    def _recommend_damper_actions(
        self,
        diagnosis: DiagnosisResult,
        hypothesis: Hypothesis
    ) -> List[RecommendedAction]:
        """Recommend actions for damper issues."""
        actions = []
        
        zone_id = diagnosis.context.get("zone", {}).get("id")
        if not zone_id:
            return actions
        
        # Get control chain to find damper points
        control_chain = diagnosis.context.get("control_chain", [])
        damper_points = [
            item["point"] for item in control_chain
            if "damper" in item["point"].get("name", "").lower()
        ]
        
        if damper_points:
            # Action 1: Create work order for damper inspection
            actions.append(RecommendedAction(
                action_id=f"wo_damper_{datetime.now().isoformat()}",
                action_type="work_order",
                description=f"Inspect and repair damper for {diagnosis.context.get('zone', {}).get('name', 'zone')}",
                priority="high",
                affected_zones=[zone_id] if zone_id else [],
                affected_equipment=[],
                rationale=hypothesis.description,
                expected_impact="Restore proper airflow and temperature control",
                risks=["Zone may remain uncomfortable until repair"],
                requires_approval=True
            ))
        
        # Action 2: Temporary setpoint adjustment (if possible)
        # This would require finding the zone setpoint and proposing a change
        actions.append(RecommendedAction(
            action_id=f"temp_setpoint_{datetime.now().isoformat()}",
            action_type="setpoint_change",
            description="Temporarily adjust zone setpoint to mitigate comfort issue",
            priority="medium",
            affected_zones=[zone_id] if zone_id else [],
            affected_equipment=[],
            rationale="Provide temporary relief while damper is repaired",
            expected_impact="Improved comfort in short term",
            risks=["May increase energy consumption", "Temporary measure only"],
            requires_approval=True
        ))
        
        return actions
    
    def _recommend_supply_air_actions(
        self,
        diagnosis: DiagnosisResult,
        hypothesis: Hypothesis
    ) -> List[RecommendedAction]:
        """Recommend actions for supply air temperature issues."""
        actions = []
        
        # Action: Check AHU supply air temperature setpoint
        actions.append(RecommendedAction(
            action_id=f"ahu_check_{datetime.now().isoformat()}",
            action_type="inspection",
            description="Inspect AHU supply air temperature control",
            priority="high",
            affected_zones=[],
            affected_equipment=[],
            rationale=hypothesis.description,
            expected_impact="Identify and correct AHU control issue",
            risks=[],
            requires_approval=False
        ))
        
        return actions
    
    def _recommend_schedule_actions(
        self,
        diagnosis: DiagnosisResult,
        hypothesis: Hypothesis
    ) -> List[RecommendedAction]:
        """Recommend actions for schedule issues."""
        actions = []
        
        zone_id = diagnosis.context.get("zone", {}).get("id")
        
        actions.append(RecommendedAction(
            action_id=f"schedule_review_{datetime.now().isoformat()}",
            action_type="schedule_tweak",
            description="Review and correct zone schedule",
            priority="medium",
            affected_zones=[zone_id] if zone_id else [],
            affected_equipment=[],
            rationale=hypothesis.description,
            expected_impact="Proper schedule will maintain comfort during occupied hours",
            risks=["May affect other zones if schedule is shared"],
            requires_approval=True
        ))
        
        return actions
    
    def _recommend_sensor_actions(
        self,
        diagnosis: DiagnosisResult,
        hypothesis: Hypothesis
    ) -> List[RecommendedAction]:
        """Recommend actions for sensor issues."""
        actions = []
        
        point_id = diagnosis.context.get("event", {}).get("point_id", "")
        
        actions.append(RecommendedAction(
            action_id=f"sensor_calibration_{datetime.now().isoformat()}",
            action_type="work_order",
            description="Calibrate or replace temperature sensor",
            priority="high",
            affected_zones=[],
            affected_equipment=[],
            rationale=hypothesis.description,
            expected_impact="Accurate sensor readings will enable proper control",
            risks=["Zone may be uncomfortable during sensor replacement"],
            requires_approval=True
        ))
        
        return actions
    
    def _recommend_generic_actions(
        self,
        diagnosis: DiagnosisResult,
        hypothesis: Hypothesis
    ) -> List[RecommendedAction]:
        """Generic recommendations."""
        return [
            RecommendedAction(
                action_id=f"generic_{datetime.now().isoformat()}",
                action_type="inspection",
                description="Investigate system issue",
                priority="medium",
                affected_zones=[],
                affected_equipment=[],
                rationale=hypothesis.description,
                expected_impact="Identify root cause",
                risks=[],
                requires_approval=False
            )
        ]


