"""
Detection Agent - Always-on agent that monitors telemetry for anomalies.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from tools.timeseries_tools import TimeseriesTools
from tools.graph_tools import GraphTools


@dataclass
class DetectionEvent:
    """Event detected by the detection agent."""
    event_id: str
    timestamp: datetime
    event_type: str  # "comfort_violation", "stability_issue", "energy_anomaly"
    severity: str  # "low", "medium", "high", "critical"
    zone_id: Optional[str]
    equipment_id: Optional[str]
    point_id: str
    description: str
    metrics: Dict[str, Any]


class DetectionAgent:
    """
    Detection agent that continuously monitors telemetry for issues.
    
    Runs on a schedule or stream, creating events when anomalies are detected.
    """
    
    def __init__(self, graph_tools: GraphTools, timeseries_tools: TimeseriesTools):
        self.graph_tools = graph_tools
        self.timeseries_tools = timeseries_tools
        self._events: List[DetectionEvent] = []
    
    def detect_comfort_violations(
        self,
        zone_id: str,
        window: timedelta = timedelta(hours=1)
    ) -> List[DetectionEvent]:
        """
        Detect comfort violations in a zone.
        
        Args:
            zone_id: Zone identifier
            window: Time window to analyze
            
        Returns:
            List of detected comfort violation events
        """
        events = []
        
        # Get zone context to find temperature points
        zone_context = self.graph_tools.get_zone_context(zone_id)
        
        # Check each temperature point
        for point in zone_context.points:
            if "temp" not in point.get("name", "").lower():
                continue
            
            # Get timeseries data
            end = datetime.now()
            start = end - window
            data = self.timeseries_tools.get_timeseries(
                point["id"],
                start,
                end
            )
            
            if not data:
                continue
            
            # Check for comfort violations (e.g., outside 20-26°C)
            comfort_min = 20.0
            comfort_max = 26.0
            
            for ts_data in data:
                if ts_data.value < comfort_min or ts_data.value > comfort_max:
                    events.append(DetectionEvent(
                        event_id=f"comfort_{zone_id}_{ts_data.timestamp.isoformat()}",
                        timestamp=ts_data.timestamp,
                        event_type="comfort_violation",
                        severity="high" if abs(ts_data.value - 23.0) > 3.0 else "medium",
                        zone_id=zone_id,
                        equipment_id=None,
                        point_id=point["id"],
                        description=f"Temperature {ts_data.value:.1f}°C outside comfort band ({comfort_min}-{comfort_max}°C)",
                        metrics={
                            "temperature": ts_data.value,
                            "comfort_min": comfort_min,
                            "comfort_max": comfort_max,
                            "deviation": max(comfort_min - ts_data.value, ts_data.value - comfort_max)
                        }
                    ))
        
        return events
    
    def detect_stability_issues(
        self,
        point_id: str,
        window: timedelta = timedelta(hours=24)
    ) -> List[DetectionEvent]:
        """
        Detect stability issues (short cycling, oscillations, etc.).
        
        Args:
            point_id: Point identifier
            window: Time window to analyze
            
        Returns:
            List of detected stability events
        """
        events = []
        
        end = datetime.now()
        start = end - window
        
        # Detect anomalies
        anomalies = self.timeseries_tools.detect_anomalies(
            point_id,
            start,
            end,
            method="ewma"
        )
        
        # Check for short cycling (rapid on/off)
        data = self.timeseries_tools.get_timeseries(point_id, start, end)
        if len(data) > 10:
            values = [d.value for d in data]
            # Count rapid changes
            changes = sum(1 for i in range(1, len(values)) if abs(values[i] - values[i-1]) > 1.0)
            change_rate = changes / len(values)
            
            if change_rate > 0.3:  # More than 30% of readings show >1°C change
                events.append(DetectionEvent(
                    event_id=f"stability_{point_id}_{datetime.now().isoformat()}",
                    timestamp=datetime.now(),
                    event_type="stability_issue",
                    severity="medium",
                    zone_id=None,
                    equipment_id=None,
                    point_id=point_id,
                    description=f"High variability detected: {change_rate:.1%} of readings show >1°C changes",
                    metrics={
                        "change_rate": change_rate,
                        "anomaly_count": len(anomalies),
                        "data_points": len(data)
                    }
                ))
        
        return events
    
    def run_detection_cycle(self) -> List[DetectionEvent]:
        """
        Run a full detection cycle across all monitored zones/points.
        
        Returns:
            List of all detected events
        """
        all_events = []
        
        # For now, use a mock zone
        # In production, this would query GraphDB for all zones
        mock_zone = "ex:Zone_Main"
        
        # Detect comfort violations
        comfort_events = self.detect_comfort_violations(mock_zone)
        all_events.extend(comfort_events)
        
        # Detect stability issues for key points
        mock_point = "ft_136276_sat"
        stability_events = self.detect_stability_issues(mock_point)
        all_events.extend(stability_events)
        
        # Store events
        self._events.extend(all_events)
        
        return all_events
    
    def get_recent_events(self, limit: int = 10) -> List[DetectionEvent]:
        """Get recent detection events."""
        return sorted(
            self._events,
            key=lambda e: e.timestamp,
            reverse=True
        )[:limit]

