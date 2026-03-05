"""
Disruptive Technologies REST API client.

Authenticates via OAuth2 client-credentials (service account key) and
fetches device metadata + latest reported readings directly from the
DT Cloud API, bypassing the webhook → TimescaleDB pipeline.

Required env vars:
    DT_PROJECT_ID             – DT Studio project ID
    DT_SERVICE_ACCOUNT_KEY    – Service Account key ID
    DT_SERVICE_ACCOUNT_SECRET – Service Account secret

The key/secret pair is created in DT Studio → Project → Service Accounts.
"""
import os
import pathlib
import time
import logging
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("dt_client")

DT_TOKEN_URL = "https://identity.disruptive-technologies.com/oauth2/token"
DT_API_BASE = "https://api.d21s.com/v2"

_cached_token: Optional[str] = None
_token_expires_at: float = 0


def _cfg():
    """Read DT config lazily so dotenv values are always picked up."""
    return (
        os.getenv("DT_PROJECT_ID", ""),
        os.getenv("DT_SERVICE_ACCOUNT_KEY", ""),
        os.getenv("DT_SERVICE_ACCOUNT_SECRET", ""),
    )


def _is_configured() -> bool:
    pid, key, secret = _cfg()
    return bool(pid and key and secret)


def _get_access_token() -> str:
    """Exchange service-account credentials for a short-lived Bearer token."""
    global _cached_token, _token_expires_at
    if _cached_token and time.time() < _token_expires_at - 30:
        return _cached_token

    _, key, secret = _cfg()
    logger.info("DT OAuth2 token request with key=%s...", key[:8] if key else "EMPTY")
    resp = requests.post(
        DT_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(key, secret),
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    _cached_token = body["access_token"]
    _token_expires_at = time.time() + body.get("expires_in", 3600)
    return _cached_token


def list_devices() -> List[Dict[str, Any]]:
    """Return all devices in the project with their latest reported values."""
    if not _is_configured():
        pid, key, secret = _cfg()
        logger.warning(
            "DT API not configured — DT_PROJECT_ID=%s, KEY=%s, SECRET=%s",
            bool(pid), bool(key), bool(secret),
        )
        return []

    pid, _, _ = _cfg()
    token = _get_access_token()
    devices: List[Dict[str, Any]] = []
    next_page_token = ""

    while True:
        url = f"{DT_API_BASE}/projects/{pid}/devices"
        params: Dict[str, Any] = {"page_size": 100}
        if next_page_token:
            params["page_token"] = next_page_token

        resp = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
        devices.extend(body.get("devices", []))

        next_page_token = body.get("nextPageToken", "")
        if not next_page_token:
            break

    return devices


def get_sensor_readings() -> Dict[str, Dict[str, Any]]:
    """Return {mark_label: {value, unit, quantity_kind, updateTime, deviceType}} for
    every device that carries an ``ifcjson`` label.

    Returns an empty dict when the DT API is not configured.
    """
    if not _is_configured():
        return {}

    try:
        devices = list_devices()
    except Exception as exc:
        logger.error("DT API call failed: %s", exc)
        return {}

    readings: Dict[str, Dict[str, Any]] = {}
    for dev in devices:
        labels = dev.get("labels", {})
        mark = labels.get("ifcjson")
        if not mark:
            continue

        reported = dev.get("reported", {})
        device_type = dev.get("type", "")

        value = None
        unit = ""
        qk = ""
        update_time = ""

        if "temperature" in reported:
            block = reported["temperature"]
            value = block.get("value")
            unit = "DEG_C"
            qk = "Temperature"
            update_time = block.get("updateTime", "")
        elif "humidity" in reported:
            block = reported["humidity"]
            value = block.get("relativeHumidity", block.get("temperature"))
            unit = "PERCENT"
            qk = "RelativeHumidity"
            update_time = block.get("updateTime", "")
        elif "objectPresent" in reported:
            block = reported["objectPresent"]
            state = block.get("state", "NOT_PRESENT")
            value = 1.0 if state == "PRESENT" else 0.0
            unit = "BOOL"
            qk = "Presence"
            update_time = block.get("updateTime", "")
        elif "touch" in reported:
            block = reported["touch"]
            value = 1.0
            unit = "EVENT"
            qk = "Touch"
            update_time = block.get("updateTime", "")
        else:
            for key, block in reported.items():
                if isinstance(block, dict) and "value" in block:
                    value = block["value"]
                    qk = key
                    update_time = block.get("updateTime", "")
                    break

        if value is not None:
            readings[mark] = {
                "value": value,
                "unit": unit,
                "quantity_kind": qk,
                "update_time": update_time,
                "device_type": device_type,
            }

    logger.info("DT API returned %d sensor readings", len(readings))
    return readings
