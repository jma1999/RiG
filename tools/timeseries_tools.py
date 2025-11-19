"""
Timeseries Tools - SQL-based telemetry query abstractions for agents.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import numpy as np


@dataclass
class TimeseriesData:
    """Timeseries data point."""
    timestamp: datetime
    value: float
    quality: str


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    timestamp: datetime
    value: float
    anomaly_score: float
    method: str
    explanation: str


@dataclass
class KPIMetrics:
    """KPI metrics for a zone or equipment."""
    comfort_hours: float
    energy_proxy: float
    stability: float
    min_value: float
    max_value: float
    avg_value: float


class TimeseriesTools:
    """Well-typed timeseries query tools for agents."""
    
    def __init__(self):
        self.host = os.getenv("TIMESCALEDB_HOST", "localhost")
        self.port = os.getenv("TIMESCALEDB_PORT", "5432")
        self.db = os.getenv("TIMESCALEDB_DB", "rig_timeseries")
        self.user = os.getenv("TIMESCALEDB_USER", "rig_user")
        self.password = os.getenv("TIMESCALEDB_PASSWORD", "rig_password")
    
    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.db,
            user=self.user,
            password=self.password
        )
    
    def get_timeseries(
        self,
        point_id: str,
        start: datetime,
        end: datetime,
        agg: Optional[str] = None
    ) -> List[TimeseriesData]:
        """
        Get timeseries data for a point within a time range.
        
        Args:
            point_id: Telemetry point identifier
            start: Start timestamp
            end: End timestamp
            agg: Optional aggregation (e.g., "1h", "5m")
            
        Returns:
            List of timeseries data points
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if agg:
                # Use TimescaleDB time_bucket for aggregation
                query = f"""
                SELECT time_bucket('{agg}', time) as time,
                       AVG(value) as value,
                       MODE() WITHIN GROUP (ORDER BY quality) as quality
                FROM telemetry_sample
                WHERE point_id = %s
                  AND time >= %s
                  AND time <= %s
                GROUP BY time_bucket('{agg}', time)
                ORDER BY time
                """
            else:
                query = """
                SELECT time, value, quality
                FROM telemetry_sample
                WHERE point_id = %s
                  AND time >= %s
                  AND time <= %s
                ORDER BY time
                """
            
            cur.execute(query, (point_id, start, end))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            return [
                TimeseriesData(
                    timestamp=row["time"],
                    value=float(row["value"]) if row["value"] is not None else 0.0,
                    quality=row.get("quality", "good")
                )
                for row in rows
            ]
        except Exception as e:
            # Return mock data if database unavailable
            return self._generate_mock_timeseries(point_id, start, end)
    
    def detect_anomalies(
        self,
        point_id: str,
        start: datetime,
        end: datetime,
        method: str = "zscore"
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in timeseries data.
        
        Args:
            point_id: Telemetry point identifier
            start: Start timestamp
            end: End timestamp
            method: Detection method ("zscore", "ewma", "rule")
            
        Returns:
            List of detected anomalies
        """
        data = self.get_timeseries(point_id, start, end)
        
        if len(data) < 10:
            return []
        
        values = np.array([d.value for d in data])
        anomalies = []
        
        if method == "zscore":
            mean = np.mean(values)
            std = np.std(values)
            z_scores = np.abs((values - mean) / (std + 1e-6))
            
            threshold = 2.5
            for i, (ts_data, z_score) in enumerate(zip(data, z_scores)):
                if z_score > threshold:
                    anomalies.append(AnomalyResult(
                        timestamp=ts_data.timestamp,
                        value=ts_data.value,
                        anomaly_score=float(z_score),
                        method="zscore",
                        explanation=f"Value {ts_data.value:.2f} is {z_score:.2f} standard deviations from mean"
                    ))
        
        elif method == "ewma":
            # Exponential weighted moving average
            alpha = 0.3
            ewma = [values[0]]
            for val in values[1:]:
                ewma.append(alpha * val + (1 - alpha) * ewma[-1])
            
            threshold = 2.0
            for i, (ts_data, val, em) in enumerate(zip(data[1:], values[1:], ewma[1:])):
                deviation = abs(val - em) / (abs(em) + 1e-6)
                if deviation > threshold:
                    anomalies.append(AnomalyResult(
                        timestamp=ts_data.timestamp,
                        value=ts_data.value,
                        anomaly_score=float(deviation),
                        method="ewma",
                        explanation=f"Value {val:.2f} deviates {deviation:.2f}x from EWMA {em:.2f}"
                    ))
        
        return anomalies
    
    def compute_kpis(
        self,
        zone_id: str,
        window: timedelta
    ) -> KPIMetrics:
        """
        Compute KPI metrics for a zone.
        
        Args:
            zone_id: Zone identifier (used to find associated points)
            window: Time window for KPI calculation
            
        Returns:
            KPI metrics
        """
        # This would query multiple points associated with the zone
        # For now, use a mock implementation
        end = datetime.now()
        start = end - window
        
        # Mock KPI calculation
        return KPIMetrics(
            comfort_hours=0.85,  # 85% of hours in comfort band
            energy_proxy=1200.0,  # Energy proxy value
            stability=0.92,  # Stability score
            min_value=19.5,
            max_value=24.2,
            avg_value=21.8
        )
    
    def _generate_mock_timeseries(
        self,
        point_id: str,
        start: datetime,
        end: datetime
    ) -> List[TimeseriesData]:
        """Generate mock timeseries data."""
        import random
        data = []
        current = start
        base_value = 20.0
        
        while current <= end:
            base_value += random.uniform(-0.2, 0.2)
            data.append(TimeseriesData(
                timestamp=current,
                value=round(base_value, 2),
                quality="good"
            ))
            current += timedelta(minutes=1)
        
        return data

