# ingest/ifc_to_rdf_ifcld.py
"""
IFC to RDF Conversion using IFC-LD Instance Builder (HTTP service).

This module uses the devonsparks/ifcld-service to convert IFC-SPF files to
native IFC-LD RDF format. Unlike the Peter Pauwels IFCtoRDF (ifcOWL) converter,
this produces IFC-LD compliant output.

Reference: https://github.com/devonsparks/ifcld-service

Usage:
    Ensure ifcld-service is running (e.g. docker run -p 5000:5000 ifcld-instance-builder)
    python ingest/ifc_to_rdf_ifcld.py input.ifc --output output.ttl
"""
import os
import sys
import pathlib
import argparse
from typing import Optional, Dict, Any
import requests

# Default ifcld-service URL (run via Docker or locally)
DEFAULT_IFCLD_URL = os.getenv("IFCLD_SERVICE_URL", "http://localhost:5000")


def convert_ifc_to_turtle(
    ifc_path: str,
    turtle_path: str,
    base_uri: Optional[str] = None,
    service_url: Optional[str] = None,
    add_bot_profile: bool = False,
    timeout: int = 3600
) -> Dict[str, Any]:
    """
    Convert IFC-SPF file to RDF Turtle using IFC-LD Instance Builder service.

    Args:
        ifc_path: Path to input IFC-SPF file
        turtle_path: Path to output Turtle (.ttl) file
        base_uri: Base URI for RDF resources (e.g., https://example.com/ifc/)
        service_url: IFC-LD service URL (default: http://localhost:5000)
        add_bot_profile: If True, request BOT enrichment via Accept-Profile
        timeout: Request timeout in seconds (default: 3600 for large models)

    Returns:
        Dictionary with conversion statistics
    """
    ifc_path = pathlib.Path(ifc_path)
    turtle_path = pathlib.Path(turtle_path)

    if not ifc_path.exists():
        raise FileNotFoundError(f"Input IFC file not found: {ifc_path}")

    url = (service_url or DEFAULT_IFCLD_URL).rstrip("/")
    instances_url = f"{url}/instances"

    # Read IFC file (ISO 10303-21 format)
    with open(ifc_path, "r", encoding="utf-8", errors="replace") as f:
        ifc_content = f.read()

    headers = {
        "Content-Type": "model/step",
        "Accept": "text/turtle",
    }

    if base_uri:
        headers["Content-Location"] = base_uri.rstrip("#") + "#"

    if add_bot_profile:
        headers["Accept-Profile"] = "https://w3id.org/bot#"

    print(f"🔄 Converting IFC to IFC-LD Turtle via {instances_url}...")
    print(f"   Input:  {ifc_path}")
    print(f"   Output: {turtle_path}")
    if base_uri:
        print(f"   Base URI: {base_uri}")

    try:
        response = requests.post(
            instances_url,
            data=ifc_content.encode("utf-8"),
            headers=headers,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"IFC-LD service returned {response.status_code}: {response.text[:500]}"
            )

        # Write Turtle output
        turtle_path.parent.mkdir(parents=True, exist_ok=True)
        with open(turtle_path, "w", encoding="utf-8") as f:
            f.write(response.text)

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
        }

        print(f"✅ IFC-LD conversion successful!")
        print(f"   Input size:  {stats['input_size_mb']} MB")
        print(f"   Output size: {stats['output_size_mb']} MB")

        return stats

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to IFC-LD service at {url}. "
            "Ensure the service is running: docker run -d -p 5000:5000 ifcld-instance-builder"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"IFC-LD conversion timed out after {timeout}s. "
            "Try increasing --timeout for large models."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Convert IFC-SPF to IFC-LD Turtle via ifcld-service"
    )
    parser.add_argument("input", help="Path to input IFC file")
    parser.add_argument("output", nargs="?", help="Path to output Turtle file")
    parser.add_argument("--base-uri", default=None,
                        help="Base URI for RDF resources")
    parser.add_argument("--service-url", default=None,
                        help=f"IFC-LD service URL (default: {DEFAULT_IFCLD_URL})")
    parser.add_argument("--bot-profile", action="store_true",
                        help="Add BOT ontology enrichment")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="Request timeout in seconds (default: 3600)")

    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output) if args.output else input_path.parent / (input_path.stem + ".ttl")

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
