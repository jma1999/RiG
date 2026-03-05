"""
Disruptive Technologies REST API client.

Authenticates via JWT-bearer OAuth2 flow (service account key signs a JWT
which is exchanged for an access token).

Required env vars:
    DT_PROJECT_ID               – DT Studio project ID
    DT_SERVICE_ACCOUNT_KEY      – Service Account key ID
    DT_SERVICE_ACCOUNT_SECRET   – Service Account secret (HMAC signing key)
    DT_SERVICE_ACCOUNT_EMAIL    – Service Account email

Create the key/secret/email in DT Studio → Project → Service Accounts.
"""
import os
import pathlib
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Any

import jwt
import requests
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env", override=True)

logger = logging.getLogger("dt_client")

DT_TOKEN_URL = "https://identity.disruptive-technologies.com/oauth2/token"
DT_API_BASE = "https://api.d21s.com/v2"

_cached_token: Optional[str] = None
_token_expires_at: float = 0


def _cfg():
    """Read DT config lazily so dotenv values are always picked up."""
    return {
        "project_id": os.getenv("DT_PROJECT_ID", ""),
        "key_id": os.getenv("DT_SERVICE_ACCOUNT_KEY", ""),
        "secret": os.getenv("DT_SERVICE_ACCOUNT_SECRET", ""),
        "email": os.getenv("DT_SERVICE_ACCOUNT_EMAIL", ""),
    }


def _is_configured() -> bool:
    c = _cfg()
    ok = bool(c["project_id"] and c["key_id"] and c["secret"] and c["email"])
    if not ok:
        missing = [k for k, v in c.items() if not v]
        logger.warning("DT API not configured — missing: %s", ", ".join(missing))
    return ok


def _get_access_token() -> str:
    """Create a JWT signed with the SA secret and exchange it for a Bearer token."""
    global _cached_token, _token_expires_at
    if _cached_token and time.time() < _token_expires_at - 30:
        return _cached_token

    c = _cfg()
    now = int(time.time())

    jwt_headers = {
        "alg": "HS256",
        "kid": c["key_id"],
    }
    jwt_payload = {
        "iat": now,
        "exp": now + 3600,
        "aud": DT_TOKEN_URL,
        "iss": c["email"],
    }

    encoded_jwt = jwt.encode(
        jwt_payload,
        c["secret"],
        algorithm="HS256",
        headers=jwt_headers,
    )

    body = urllib.parse.urlencode({
        "assertion": encoded_jwt,
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
    })

    resp = requests.post(
        DT_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if resp.status_code != 200:
        logger.error("DT token exchange failed (%d): %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"DT OAuth2 token exchange failed: {resp.status_code} {resp.text[:200]}")

    token_data = resp.json()
    _cached_token = token_data["access_token"]
    _token_expires_at = time.time() + token_data.get("expires_in", 3600)
    return _cached_token


def list_devices() -> List[Dict[str, Any]]:
    """Return all devices in the project with their latest reported values."""
    if not _is_configured():
        return []

    c = _cfg()
    token = _get_access_token()
    devices: List[Dict[str, Any]] = []
    next_page_token = ""

    while True:
        url = f"{DT_API_BASE}/projects/{c['project_id']}/devices"
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

    logger.info("DT API returned %d devices", len(devices))
    return devices


def get_sensor_readings() -> Dict[str, Dict[str, Any]]:
    """Return {mark_label: {value, unit, quantity_kind, update_time, device_type}}
    for every device that carries an ``ifcjson`` label.

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
