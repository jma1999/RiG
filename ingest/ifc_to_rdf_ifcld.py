# ingest/ifc_to_rdf_ifcld.py
"""
IFC to RDF Conversion using IFC-LD Instance Builder (HTTP service).

This module uses the devonsparks/ifcld-service to convert IFC-SPF files to
native IFC-LD RDF format. Unlike the Peter Pauwels IFCtoRDF (ifcOWL) converter,
this produces IFC-LD compliant output.

Reference: https://github.com/devonsparks/ifcld-service

Usage:
    Ensure ifcld-service is running (e.g. docker run -p 5050:5000 ifcld-instance-builder)
    python ingest/ifc_to_rdf_ifcld.py input.ifc --output output.ttl
"""

import os
import sys
import pathlib
import argparse
from typing import Optional, Dict, Any

import requests

DEFAULT_IFCLD_URL = os.getenv("IFCLD_SERVICE_URL", "http://localhost:5050")


def convert_ifc_to_turtle(
    ifc_path: str,
    turtle_path: str,
    base_uri: Optional[str] = None,
    service_url: Optional[str] = None,
    add_bot_profile: bool = False,
    timeout: int = 3600,
) -> Dict[str, Any]:
    ifc_path = pathlib.Path(ifc_path)
    turtle_path = pathlib.Path(turtle_path)

    if not ifc_path.exists():
        raise FileNotFoundError(f"Input IFC file not found: {ifc_path}")

    url = (service_url or DEFAULT_IFCLD_URL).rstrip("/")
    instances_url = f"{url}/instances"

    # Send raw bytes (avoid encoding surprises)
    ifc_bytes = ifc_path.read_bytes()

    headers = {
        "Content-Type": "model/step",     # IFC-SPF / STEP
        "Accept": "text/turtle",
    }

    # NOTE: This may or may not be honored by the service.
    # Keep it as a hint, but don’t assume it changes output IRIs unless verified.
    if base_uri:
        headers["Content-Location"] = base_uri.rstrip("#") + "#"

    if add_bot_profile:
        headers["Accept-Profile"] = "https://w3id.org/bot#"

    print(f"🔄 Converting IFC to IFC-LD Turtle via {instances_url}...")
    print(f"   Input:  {ifc_path}")
    print(f"   Output: {turtle_path}")
    if base_uri:
        print(f"   Base URI hint: {base_uri}")

    try:
        response = requests.post(
            instances_url,
            data=ifc_bytes,
            headers=headers,
            timeout=timeout,
        )

        # Accept any 2xx
        if not (200 <= response.status_code < 300):
            ct = response.headers.get("Content-Type", "")
            body_preview = (response.text or "")[:1000]
            raise RuntimeError(
                f"IFC-LD service returned HTTP {response.status_code} (Content-Type: {ct}).\n"
                f"Response preview:\n{body_preview}"
            )

        # Write Turtle output (use response.text, but could also use response.content)
        turtle_path.parent.mkdir(parents=True, exist_ok=True)
        turtle_path.write_text(response.text, encoding="utf-8")

        ifc_size = ifc_path.stat().st_size
        turtle_size = turtle_path.stat().st_size

        stats = {
            "success": True,
            "input_file": str(ifc_path),
            "output_file": str(turtle_path),
            "input_size_mb": round(ifc_size / (1024 * 1024), 2),
            "output_size_mb": round(turtle_size / (1024 * 1024), 2),
            "base_uri": base_uri,
            "converter": "ifcld-service",
            "service_url": url,
            "http_status": response.status_code,
        }

        print("✅ IFC-LD conversion successful!")
        print(f"   Input size:  {stats['input_size_mb']} MB")
        print(f"   Output size: {stats['output_size_mb']} MB")

        return stats

    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to IFC-LD service at {url}.\n"
            f"Details: {e}\n"
            "If you’re using docker compose, confirm the mapped port matches your URL.\n"
            "Example: docker compose ps  (look at HOST_PORT->5000)\n"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"IFC-LD conversion timed out after {timeout}s.\n"
            "Try increasing --timeout for large models."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Convert IFC-SPF to IFC-LD Turtle via ifcld-service"
    )
    parser.add_argument("input", help="Path to input IFC file")
    parser.add_argument("output", nargs="?", help="Path to output Turtle file")
    parser.add_argument("--base-uri", default=None, help="Base URI for RDF resources (hint)")
    parser.add_argument("--service-url", default=None,
                        help=f"IFC-LD service URL (default: {DEFAULT_IFCLD_URL})")
    parser.add_argument("--bot-profile", action="store_true", help="Add BOT ontology enrichment")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="Request timeout in seconds (default: 3600)")

    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output) if args.output else input_path.with_suffix(".ttl")

    try:
        stats = convert_ifc_to_turtle(
            str(input_path),
            str(output_path),
            base_uri=args.base_uri,
            service_url=args.service_url,
            add_bot_profile=args.bot_profile,
            timeout=args.timeout,
        )
        print(f"\n✅ Done: {stats['output_file']}")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
