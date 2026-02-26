# ingest/shacl_validation.py
"""
SHACL Validation for IFC-LD RDF Graphs.

Validates RDF graphs against SHACL shapes using pyshacl + rdflib.

- Extracts sh:ValidationResult nodes (focus node, path, message, etc.)
- Prints compact summary of most common violation signatures
- Avoids storing massive violation lists by default (--max-violations)
"""

import os
import sys
import pathlib
import argparse
import json
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter

from rdflib import Graph, Namespace
from rdflib.namespace import RDF
import pyshacl

SH = Namespace("http://www.w3.org/ns/shacl#")


def _load_graph(path: pathlib.Path, fmt: str = "turtle") -> Graph:
    g = Graph()
    g.parse(str(path), format=fmt)
    return g


def _extract_validation_results(
    results_graph: Graph,
    max_results: int = 200,
    top_signatures: int = 20,
) -> Tuple[int, List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Extract sh:ValidationResult nodes from results_graph.

    Returns:
      - total_result_nodes
      - sampled_results (<= max_results)
      - top_signature_summary (list of dicts)
    """
    sampled: List[Dict[str, str]] = []

    # Prefer a stable signature key; messages can vary and fragment counts.
    sig_counter: Counter = Counter()
    sig_message: Dict[Tuple[str, str, str], str] = {}

    total = 0
    for r in results_graph.subjects(RDF.type, SH.ValidationResult):
        total += 1

        path = str(results_graph.value(r, SH.resultPath) or "")
        shape = str(results_graph.value(r, SH.sourceShape) or "")
        comp = str(results_graph.value(r, SH.sourceConstraintComponent) or "")
        msg = str(results_graph.value(r, SH.resultMessage) or "")

        key = (comp, path, shape)
        sig_counter[key] += 1
        if key not in sig_message and msg:
            sig_message[key] = msg

        if len(sampled) < max_results:
            sampled.append(
                {
                    "focusNode": str(results_graph.value(r, SH.focusNode) or ""),
                    "resultPath": path,
                    "sourceShape": shape,
                    "sourceConstraintComponent": comp,
                    "value": str(results_graph.value(r, SH.value) or ""),
                    "message": msg,
                    "severity": str(results_graph.value(r, SH.resultSeverity) or ""),
                }
            )

    top = sig_counter.most_common(top_signatures)
    top_summary: List[Dict[str, str]] = []
    for (comp, path, shape), n in top:
        top_summary.append(
            {
                "count": n,
                "sourceConstraintComponent": comp,
                "resultPath": path,
                "sourceShape": shape,
                "message": sig_message.get((comp, path, shape), ""),
            }
        )

    return total, sampled, top_summary


def validate_graph(
    data_graph_path: str,
    shacl_shapes_path: str,
    ont_graph_path: Optional[str] = None,
    inference: str = "none",
    max_violations: int = 200,
    top_signatures: int = 20,
    print_results_text: bool = False,
    include_results_text: bool = False,  # NEW: controls whether results_text is returned
) -> Dict[str, Any]:
    data_path = pathlib.Path(data_graph_path)
    shapes_path = pathlib.Path(shacl_shapes_path)

    if not data_path.exists():
        raise FileNotFoundError(f"Data graph not found: {data_path}")
    if not shapes_path.exists():
        raise FileNotFoundError(f"SHACL shapes not found: {shapes_path}")

    print("🔍 Validating RDF graph against SHACL shapes...")
    print(f"   Data graph:   {data_path}")
    print(f"   SHACL shapes: {shapes_path}")

    data_graph = _load_graph(data_path, "turtle")
    print(f"   Loaded {len(data_graph)} triples from data graph")

    shapes_graph = _load_graph(shapes_path, "turtle")
    print(f"   Loaded {len(shapes_graph)} triples from SHACL shapes")

    ont_graph = None
    if ont_graph_path:
        ont_path = pathlib.Path(ont_graph_path)
        if ont_path.exists():
            ont_graph = _load_graph(ont_path, "turtle")
            print(f"   Loaded {len(ont_graph)} triples from ontology graph")

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ont_graph,
        inference=inference,
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False,
    )

    total_results, sampled_results, top_summary = _extract_validation_results(
        results_graph,
        max_results=max_violations,
        top_signatures=top_signatures,
    )

    validation_results: Dict[str, Any] = {
        "conforms": conforms,
        "validation_passed": conforms,
        "triple_count": len(data_graph),
        "shapes_triple_count": len(shapes_graph),
        "validation_result_nodes": total_results,
        "violations_sample": sampled_results,
        "top_violation_signatures": top_summary,
    }

    if include_results_text:
        validation_results["results_text"] = results_text

    if conforms:
        print("✅ Validation PASSED!")
        print("   No constraint violations found")
    else:
        print("❌ Validation FAILED!")
        print(f"   sh:ValidationResult nodes: {total_results}")

        if top_summary:
            print("\n   Top violation signatures:")
            for row in top_summary[:10]:
                print(
                    f"     - {row['count']:>8}  {row['sourceConstraintComponent']}  "
                    f"path={row['resultPath']}"
                )

        if print_results_text:
            print("\n--- pySHACL results_text (truncated) ---")
            print(results_text[:4000])
            print("--- end ---\n")

    return validation_results


def validate_graphdb_repository(
    graphdb_client,
    shacl_shapes_path: str,
    repository: str = "rig-facility-mgmt",
    max_violations: int = 200,
    top_signatures: int = 20,
    print_results_text: bool = False,
    include_results_text: bool = False,
) -> Dict[str, Any]:
    shapes_path = pathlib.Path(shacl_shapes_path)
    if not shapes_path.exists():
        raise FileNotFoundError(f"SHACL shapes not found: {shapes_path}")

    print("🔍 Validating GraphDB repository against SHACL shapes...")
    print(f"   Repository:   {repository}")
    print(f"   SHACL shapes: {shapes_path}")

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        print("   Exporting repository data (CONSTRUCT all triples)...")
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        results = graphdb_client.execute_sparql_query(query, output_format="turtle")

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(results.decode("utf-8") if isinstance(results, bytes) else str(results))

        return validate_graph(
            tmp_path,
            str(shapes_path),
            max_violations=max_violations,
            top_signatures=top_signatures,
            print_results_text=print_results_text,
            include_results_text=include_results_text,
        )

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(description="Validate RDF graphs against SHACL shapes")
    parser.add_argument("data_graph", help="Path to RDF data graph (Turtle file)")
    parser.add_argument("shacl_shapes", help="Path to SHACL shapes file")
    parser.add_argument("--ontology", default=None, help="Optional ontology graph for inference")
    parser.add_argument("--inference", default="none", choices=["none", "rdfs", "owl"],
                        help="Inference type (default: none)")
    parser.add_argument("--output", default=None, help="Output JSON file for validation results")

    parser.add_argument("--max-violations", type=int, default=200,
                        help="Max number of individual violations to store (default: 200)")
    parser.add_argument("--top-signatures", type=int, default=20,
                        help="How many top violation signatures to summarize (default: 20)")
    parser.add_argument("--print-results-text", action="store_true",
                        help="Print pySHACL results_text (truncated) when validation fails")
    parser.add_argument("--include-results-text", action="store_true",
                        help="Include full pySHACL results_text in JSON output (can be huge)")

    args = parser.parse_args()

    try:
        results = validate_graph(
            args.data_graph,
            args.shacl_shapes,
            ont_graph_path=args.ontology,
            inference=args.inference,
            max_violations=args.max_violations,
            top_signatures=args.top_signatures,
            print_results_text=args.print_results_text,
            include_results_text=args.include_results_text,
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Validation results saved to: {args.output}")
        else:
            print("\n📊 Validation Results (compact):")
            print(json.dumps(results, indent=2))

        sys.exit(0 if results["conforms"] else 1)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
