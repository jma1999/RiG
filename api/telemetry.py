"""
TimescaleDB telemetry API endpoints.
"""
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter()

# TimescaleDB configuration
TIMESCALEDB_HOST = os.getenv("TIMESCALEDB_HOST", "localhost")
TIMESCALEDB_PORT = os.getenv("TIMESCALEDB_PORT", "5432")
TIMESCALEDB_DB = os.getenv("TIMESCALEDB_DB", "rig_timeseries")
TIMESCALEDB_USER = os.getenv("TIMESCALEDB_USER", "rig_user")
TIMESCALEDB_PASSWORD = os.getenv("TIMESCALEDB_PASSWORD", "rig_password")


def get_db_connection():
    """Get TimescaleDB connection."""
    try:
        conn = psycopg2.connect(
            host=TIMESCALEDB_HOST,
            port=TIMESCALEDB_PORT,
            dbname=TIMESCALEDB_DB,
            user=TIMESCALEDB_USER,
            password=TIMESCALEDB_PASSWORD
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


class TelemetryPoint(BaseModel):
    point_id: str
    value: float
    timestamp: str
    quality: Optional[str] = "good"


class TelemetryResponse(BaseModel):
    point_id: str
    data: List[TelemetryPoint]
    unit: Optional[str] = None
    quantity_kind: Optional[str] = None


@router.get("/points")
async def list_telemetry_points():
    """List all available telemetry points."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT DISTINCT point_id, 
               COUNT(*) as data_points,
               MIN(time) as first_reading,
               MAX(time) as last_reading
        FROM telemetry_sample
        GROUP BY point_id
        ORDER BY point_id
        """
        
        cur.execute(query)
        points = cur.fetchall()
        cur.close()
        conn.close()
        
        print(f"[Telemetry API] Found {len(points)} telemetry points in TimescaleDB")
        
        if points:
            return {
                "points": [
                    {
                        "point_id": p["point_id"],
                        "data_points": p["data_points"],
                        "first_reading": p["first_reading"].isoformat() if p["first_reading"] else None,
                        "last_reading": p["last_reading"].isoformat() if p["last_reading"] else None
                    }
                    for p in points
                ]
            }
        else:
            # Table exists but empty - return mock data
            print("[Telemetry API] Table exists but empty, returning mock data")
            return {
                "points": [
                    {
                        "point_id": "ft_136276_sat",
                        "data_points": 60,
                        "first_reading": (datetime.now() - timedelta(hours=1)).isoformat(),
                        "last_reading": datetime.now().isoformat()
                    },
                    {
                        "point_id": "ft_136276_saf",
                        "data_points": 60,
                        "first_reading": (datetime.now() - timedelta(hours=1)).isoformat(),
                        "last_reading": datetime.now().isoformat()
                    }
                ]
            }
    except Exception as e:
        # Return mock data if database is not available
        print(f"[Telemetry API] Error connecting to TimescaleDB: {str(e)}")
        print("[Telemetry API] Returning mock data as fallback")
        return {
            "points": [
                {
                    "point_id": "ft_136276_sat",
                    "data_points": 60,
                    "first_reading": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "last_reading": datetime.now().isoformat()
                },
                {
                    "point_id": "ft_136276_saf",
                    "data_points": 60,
                    "first_reading": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "last_reading": datetime.now().isoformat()
                }
            ]
        }


@router.get("/graph-sensors")
async def get_graph_sensors():
    """Query GraphDB for s223 sensors, then enrich with live readings from
    the DT Cloud API (primary) and TimescaleDB (secondary).

    Priority order for status:
      1. DT REST API (if configured) – most reliable, real-time
      2. TimescaleDB (webhook pipeline)
      3. Default → OFFLINE
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

    # ── 1. Query GraphDB for aligned 223P sensors ────────────────────────
    sensors: dict = {}   # keyed by point_id to deduplicate
    try:
        from api.graphdb import get_graphdb_client
        client = get_graphdb_client()
        query = """
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX qudt: <http://qudt.org/schema/qudt/>

        SELECT DISTINCT ?sensor ?label ?sensorType ?quantityKind
        WHERE {
          ?sensor a ?sensorType .
          FILTER(?sensorType IN (
            s223:Sensor, s223:HumiditySensor,
            s223:TemperatureSensor, s223:OccupantPresenceSensor
          ))
          OPTIONAL { ?sensor rdfs:label ?label }
          OPTIONAL { ?sensor s223:observes ?prop .
                     ?prop qudt:hasQuantityKind ?quantityKind }
        }
        ORDER BY ?label
        """
        raw = client.execute_sparql_query(query, output_format="json")
        bindings = []
        if isinstance(raw, dict):
            inner = raw.get("results", raw)
            bindings = inner.get("bindings", []) if isinstance(inner, dict) else []

        for b in bindings:
            uri = b.get("sensor", {}).get("value", "")
            label = b.get("label", {}).get("value", "")
            s_type = b.get("sensorType", {}).get("value", "").split("#")[-1]
            qk = b.get("quantityKind", {}).get("value", "").split("#")[-1] if b.get("quantityKind") else ""
            short = label or uri.split("/")[-1].split("#")[-1]

            if "sensor" in short.lower():
                num = short.lower().replace("sensor", "").strip().zfill(2)
                point_id = f"dt_sensor_{num}"
            else:
                point_id = f"graph_{short.lower().replace(' ', '_')}"

            if point_id not in sensors:
                sensors[point_id] = {
                    "point_id": point_id,
                    "label": short,
                    "mark": short,
                    "uri": uri,
                    "sensor_type": s_type,
                    "quantity_kind": qk,
                    "source": "223p",
                    "status": "OFFLINE",
                    "data_points": 0,
                    "last_reading": None,
                    "latest_value": None,
                    "unit": "",
                }
    except Exception as e:
        print(f"[graph-sensors] Could not query GraphDB: {e}")

    # ── 2. Enrich from DT Cloud API (primary) ────────────────────────────
    try:
        from api.dt_client import get_sensor_readings
        dt_readings = get_sensor_readings()
        for mark, reading in dt_readings.items():
            num = mark.lower().replace("sensor", "").strip().zfill(2)
            point_id = f"dt_sensor_{num}" if "sensor" in mark.lower() else f"graph_{mark.lower()}"

            if point_id in sensors:
                sensors[point_id]["status"] = "LIVE"
                sensors[point_id]["latest_value"] = reading["value"]
                sensors[point_id]["unit"] = reading.get("unit", "")
                sensors[point_id]["last_reading"] = reading.get("update_time", "")
                if reading.get("quantity_kind"):
                    sensors[point_id]["quantity_kind"] = reading["quantity_kind"]
            else:
                sensors[point_id] = {
                    "point_id": point_id,
                    "label": mark,
                    "mark": mark,
                    "uri": "",
                    "sensor_type": reading.get("device_type", ""),
                    "quantity_kind": reading.get("quantity_kind", ""),
                    "source": "dt_api",
                    "status": "LIVE",
                    "data_points": 1,
                    "last_reading": reading.get("update_time", ""),
                    "latest_value": reading["value"],
                    "unit": reading.get("unit", ""),
                }
        if dt_readings:
            print(f"[graph-sensors] DT API enriched {len(dt_readings)} sensors")
    except Exception as e:
        print(f"[graph-sensors] DT API not available: {e}")

    # ── 3. Enrich from TimescaleDB (secondary / historical) ──────────────
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT point_id, COUNT(*) as cnt,
                   MAX(time) as last_reading
            FROM telemetry_sample
            GROUP BY point_id
        """)
        for row in cur.fetchall():
            pid = row["point_id"]
            cnt = row["cnt"]
            lr = row["last_reading"].isoformat() if row["last_reading"] else None

            if pid in sensors:
                sensors[pid]["data_points"] = cnt
                if sensors[pid]["status"] != "LIVE":
                    sensors[pid]["status"] = "LIVE"
                    sensors[pid]["last_reading"] = lr
            else:
                sensors[pid] = {
                    "point_id": pid,
                    "label": pid,
                    "mark": pid,
                    "uri": "",
                    "sensor_type": "",
                    "quantity_kind": "",
                    "source": "timescaledb",
                    "status": "LIVE",
                    "data_points": cnt,
                    "last_reading": lr,
                    "latest_value": None,
                    "unit": "",
                }
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[graph-sensors] Could not query TimescaleDB: {e}")

    result = sorted(sensors.values(), key=lambda s: s["point_id"])
    print(f"[graph-sensors] Returning {len(result)} sensors "
          f"({sum(1 for s in result if s['status']=='LIVE')} LIVE)")
    return {"sensors": result}


@router.get("/points/{point_id}", response_model=TelemetryResponse)
async def get_telemetry_data(
    point_id: str,
    hours: int = Query(1, ge=1, le=168),  # 1 hour to 1 week
    limit: int = Query(1000, ge=1, le=10000)
):
    """Get telemetry data for a specific point."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get data from last N hours, ordered by time ASC to get chronological order
        query = """
        SELECT time, point_id, value, quality
        FROM telemetry_sample
        WHERE point_id = %s
          AND time >= NOW() - INTERVAL '%s hours'
        ORDER BY time ASC
        LIMIT %s
        """
        
        cur.execute(query, (point_id, hours, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        print(f"[Telemetry API] Retrieved {len(rows)} data points for {point_id}")
        
        data = [
            TelemetryPoint(
                point_id=row["point_id"],
                value=float(row["value"]) if row["value"] is not None else 0.0,
                timestamp=row["time"].isoformat(),
                quality=row.get("quality", "GOOD").upper()  # Normalize to uppercase
            )
            for row in rows
        ]
        
        print(f"📊 Retrieved {len(data)} rows from database for {point_id}")
        if len(data) > 0:
            print(f"📊 First row: {data[0].dict()}")
            print(f"📊 Last row: {data[-1].dict()}")
        
        # Get unit and quantity kind from GraphDB (mock for now)
        unit = "DEG_C" if "temp" in point_id.lower() or "sat" in point_id.lower() else "FT3-PER-MIN" if "flow" in point_id.lower() or "saf" in point_id.lower() else None
        quantity_kind = "Temperature" if "temp" in point_id.lower() or "sat" in point_id.lower() else "VolumeFlowRate" if "flow" in point_id.lower() or "saf" in point_id.lower() else None
        
        response = TelemetryResponse(
            point_id=point_id,
            data=data,
            unit=unit,
            quantity_kind=quantity_kind
        )
        
        print(f"📊 Returning response with {len(response.data)} data points")
        return response
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error fetching telemetry data for {point_id}: {e}")
        print(f"❌ Traceback: {error_details}")
        
        # Return mock data if database is not available or empty
        import random
        from datetime import timezone
        now = datetime.now(timezone.utc)
        mock_data = []
        
        # Different base values for different point types
        if "sat" in point_id.lower() or "temp" in point_id.lower():
            base_value = 20.0
            unit = "DEG_C"
            quantity_kind = "Temperature"
        elif "flow" in point_id.lower() or "saf" in point_id.lower():
            base_value = 150.0
            unit = "FT3-PER-MIN"
            quantity_kind = "VolumeFlowRate"
        else:
            base_value = 50.0
            unit = None
            quantity_kind = None
        
        print(f"📊 Generating {60} mock datapoints for {point_id}")
        for i in range(60):
            ts = now - timedelta(minutes=(60 - i))
            base_value += random.uniform(-0.1, 0.1)
            mock_data.append(
                TelemetryPoint(
                    point_id=point_id,
                    value=round(base_value, 2),
                    timestamp=ts.isoformat(),
                    quality="GOOD"
                )
            )
        
        print(f"📊 Returning {len(mock_data)} mock datapoints")
        response = TelemetryResponse(
            point_id=point_id,
            data=mock_data,
            unit=unit,
            quantity_kind=quantity_kind
        )
        print(f"📊 Response structure: point_id={response.point_id}, data_length={len(response.data)}")
        return response


@router.get("/points/{point_id}/latest")
async def get_latest_value(point_id: str):
    """Get the latest telemetry value for a point."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT time, point_id, value, quality
        FROM telemetry_sample
        WHERE point_id = %s
        ORDER BY time DESC
        LIMIT 1
        """
        
        cur.execute(query, (point_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return {
                "point_id": row["point_id"],
                "value": float(row["value"]) if row["value"] is not None else 0.0,
                "timestamp": row["time"].isoformat(),
                "quality": row.get("quality", "good")
            }
        else:
            raise HTTPException(status_code=404, detail=f"No data found for point {point_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        # Return mock data
        return {
            "point_id": point_id,
            "value": 20.5,
            "timestamp": datetime.now().isoformat(),
            "quality": "good"
        }


@router.get("/debug/{point_id}")
async def debug_telemetry_data(point_id: str):
    """Debug endpoint to check telemetry data status."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'telemetry_sample'
            );
        """)
        table_exists = cur.fetchone()[0]
        
        # Count rows for this point
        if table_exists:
            cur.execute("SELECT COUNT(*) as count FROM telemetry_sample WHERE point_id = %s", (point_id,))
            count = cur.fetchone()["count"]
        else:
            count = 0
        
        cur.close()
        conn.close()
        
        return {
            "point_id": point_id,
            "table_exists": table_exists,
            "row_count": count,
            "status": "ok"
        }
    except Exception as e:
        return {
            "point_id": point_id,
            "table_exists": False,
            "row_count": 0,
            "status": "error",
            "error": str(e)
        }


@router.post("/seed/{point_id}")
async def seed_telemetry_data(point_id: str, count: int = Query(60, ge=1, le=1000)):
    """Seed mock telemetry data for a specific point."""
    try:
        print(f"🌱 Starting seed for {point_id} with {count} datapoints")
        import random
        from datetime import datetime, timedelta, timezone
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Ensure table exists (safe even if already hypertable)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_sample (
                time TIMESTAMPTZ NOT NULL,
                point_id TEXT NOT NULL,
                value DOUBLE PRECISION,
                quality TEXT
            );
        """)
        conn.commit()
        
        # Clear existing data for this point in the last hour (to avoid duplicates)
        try:
            cur.execute(
                "DELETE FROM telemetry_sample WHERE point_id = %s AND time >= NOW() - INTERVAL '1 hour'",
                (point_id,)
            )
            conn.commit()
        except Exception as e:
            print(f"Note: Could not delete existing data: {e}")
            conn.rollback()
        
        # Generate data - `count` minutes of data at 1-min resolution
        now = datetime.now(timezone.utc)
        
        if "sat" in point_id.lower() or "temp" in point_id.lower():
            base_value = 20.0
        elif "flow" in point_id.lower() or "saf" in point_id.lower():
            base_value = 150.0
        else:
            base_value = 50.0
        
        rows = []
        for i in range(count):
            ts = now - timedelta(minutes=(count - i))
            base_value += random.uniform(-0.1, 0.1)
            rows.append((ts, point_id, round(base_value, 2), "GOOD"))
        
        inserted_count = 0
        for row in rows:
            try:
                # If PK exists on (time, point_id), this will upsert
                try:
                    cur.execute(
                        """
                        INSERT INTO telemetry_sample (time, point_id, value, quality)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (time, point_id) DO UPDATE
                        SET value = EXCLUDED.value, quality = EXCLUDED.quality
                        """,
                        row,
                    )
                except Exception:
                    # If no PK, just plain insert
                    cur.execute(
                        """
                        INSERT INTO telemetry_sample (time, point_id, value, quality)
                        VALUES (%s, %s, %s, %s)
                        """,
                        row,
                    )
                inserted_count += 1
            except Exception as e:
                print(f"Warning: Could not insert row {row[0]}: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Successfully seeded {inserted_count} rows for {point_id}")
        return {
            "success": True,
            "point_id": point_id,
            "rows_inserted": inserted_count,
            "rows_requested": count,
            "message": f"Inserted {inserted_count} rows for {point_id}"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error seeding telemetry data: {error_details}")
        return {
            "success": False,
            "point_id": point_id,
            "rows_inserted": 0,
            "rows_requested": count,
            "error": str(e),
            "message": f"Failed to seed telemetry data: {str(e)}"
        }

@router.get("/dashboard")
async def get_telemetry_dashboard():
    """Get dashboard summary of all telemetry points."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get latest values for all points
        query = """
        SELECT DISTINCT ON (point_id)
               point_id, time, value, quality
        FROM telemetry_sample
        ORDER BY point_id, time DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        points = []
        for row in rows:
            points.append({
                "point_id": row["point_id"],
                "value": float(row["value"]) if row["value"] is not None else 0.0,
                "timestamp": row["time"].isoformat(),
                "quality": row.get("quality", "good")
            })
        
        return {"points": points}
        
    except Exception as e:
        # Return mock dashboard data
        return {
            "points": [
                {
                    "point_id": "ft_136276_sat",
                    "value": 20.5,
                    "timestamp": datetime.now().isoformat(),
                    "quality": "good"
                },
                {
                    "point_id": "ft_136276_saf",
                    "value": 150.0,
                    "timestamp": datetime.now().isoformat(),
                    "quality": "good"
                }
            ]
        }

