"""
Disruptive Technologies (DT) Data Connector webhook endpoint.

Receives sensor events POSTed by DT Cloud, maps device labels (ifcjson=SensorXX)
to the graph sensor marks in the 223P/overlay graph, and writes readings to
TimescaleDB so the frontend can display live telemetry.

DT Payload shape (Data Connector v2):
{
  "event": {
    "eventId": "...",
    "targetName": "projects/cio6cburc3pjoj50ske0/devices/DEVICE_ID",
    "eventType": "temperature" | "humidity" | "objectPresent" | "touch" | ...,
    "data": {
      "temperature": { "value": 23.4, "updateTime": "2026-01-27T10:00:00Z" },
      ...
    },
    "timestamp": "2026-01-27T10:00:00Z",
    "labels": {
      "ifcjson": "Sensor01"
    }
  }
}
"""
import hashlib
import hmac
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("dt_webhook")

DT_SIGNATURE_SECRET = os.getenv("DT_SIGNATURE_SECRET", "")

SENSOR_MARK_TO_POINT_ID: Dict[str, str] = {}


def _build_mark_map():
    """Lazy-build a mapping from mark labels to TimescaleDB point IDs."""
    if SENSOR_MARK_TO_POINT_ID:
        return
    for i in range(1, 50):
        mark = f"Sensor{i:02d}"
        point_id = f"dt_sensor_{i:02d}"
        SENSOR_MARK_TO_POINT_ID[mark] = point_id


def _verify_signature(body: bytes, signature: Optional[str]) -> bool:
    if not DT_SIGNATURE_SECRET:
        return True
    if not signature:
        return False
    expected = hmac.new(
        DT_SIGNATURE_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _extract_reading(event_data: dict, event_type: str) -> Optional[Dict[str, Any]]:
    """Extract a numeric value + unit from a DT event data block."""
    if event_type == "temperature" and "temperature" in event_data:
        return {
            "value": event_data["temperature"].get("value"),
            "unit": "DEG_C",
            "quantity_kind": "Temperature",
        }
    if event_type == "humidity" and "humidity" in event_data:
        return {
            "value": event_data["humidity"].get("temperature"),
            "unit": "PERCENT",
            "quantity_kind": "RelativeHumidity",
        }
    if event_type == "objectPresent" and "objectPresent" in event_data:
        state = event_data["objectPresent"].get("state", "NOT_PRESENT")
        return {
            "value": 1.0 if state == "PRESENT" else 0.0,
            "unit": "BOOL",
            "quantity_kind": "Presence",
        }
    if event_type == "touch" and "touch" in event_data:
        return {"value": 1.0, "unit": "EVENT", "quantity_kind": "Touch"}

    for key, block in event_data.items():
        if isinstance(block, dict) and "value" in block:
            return {"value": block["value"], "unit": "", "quantity_kind": key}
    return None


def _write_to_timescaledb(point_id: str, value: float, ts: datetime, quality: str = "GOOD"):
    """Insert a single reading into TimescaleDB."""
    import psycopg2

    host = os.getenv("TIMESCALEDB_HOST", "localhost")
    port = os.getenv("TIMESCALEDB_PORT", "5432")
    db = os.getenv("TIMESCALEDB_DB", "rig_timeseries")
    user = os.getenv("TIMESCALEDB_USER", "rig_user")
    pw = os.getenv("TIMESCALEDB_PASSWORD", "rig_password")

    conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pw)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_sample (
            time TIMESTAMPTZ NOT NULL,
            point_id TEXT NOT NULL,
            value DOUBLE PRECISION,
            quality TEXT
        );
        """,
    )
    try:
        cur.execute(
            """
            INSERT INTO telemetry_sample (time, point_id, value, quality)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (time, point_id) DO UPDATE
              SET value = EXCLUDED.value, quality = EXCLUDED.quality
            """,
            (ts, point_id, value, quality),
        )
    except Exception:
        cur.execute(
            "INSERT INTO telemetry_sample (time, point_id, value, quality) VALUES (%s, %s, %s, %s)",
            (ts, point_id, value, quality),
        )
    conn.commit()
    cur.close()
    conn.close()


@router.post("/dt/webhook")
async def dt_webhook(request: Request, x_dt_signature: Optional[str] = Header(None)):
    """
    Receive a DT Data Connector event, map it to a graph sensor mark,
    and persist the reading in TimescaleDB.
    """
    body = await request.body()

    if not _verify_signature(body, x_dt_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event", payload)

    labels = event.get("labels", {})
    mark_label = labels.get("ifcjson")
    if not mark_label:
        logger.warning("DT event has no ifcjson label, ignoring: %s", event.get("targetName", ""))
        return {"status": "ignored", "reason": "no ifcjson label"}

    _build_mark_map()
    point_id = SENSOR_MARK_TO_POINT_ID.get(mark_label)
    if not point_id:
        logger.warning("Unknown sensor mark '%s', ignoring", mark_label)
        return {"status": "ignored", "reason": f"unknown mark {mark_label}"}

    event_type = event.get("eventType", "")
    event_data = event.get("data", {})
    reading = _extract_reading(event_data, event_type)

    if reading is None or reading["value"] is None:
        return {"status": "ignored", "reason": "no extractable value"}

    ts_str = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        ts = datetime.now(timezone.utc)

    try:
        _write_to_timescaledb(point_id, float(reading["value"]), ts)
        logger.info("Wrote DT reading: %s = %s @ %s", point_id, reading["value"], ts)
    except Exception as exc:
        logger.error("Failed to write DT reading to TimescaleDB: %s", exc)
        raise HTTPException(status_code=500, detail=f"DB write failed: {exc}")

    return {
        "status": "ok",
        "point_id": point_id,
        "mark": mark_label,
        "value": reading["value"],
        "timestamp": ts.isoformat(),
    }


@router.get("/dt/sensors")
async def list_dt_sensors():
    """List all mapped DT sensor marks and their TimescaleDB point IDs."""
    _build_mark_map()
    return {"sensors": SENSOR_MARK_TO_POINT_ID}
