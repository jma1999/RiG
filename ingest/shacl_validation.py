# ingest/shacl_validation.py
"""
SHACL Validation for IFC-LD RDF Graphs.

This module validates RDF graphs against SHACL shapes to ensure IFC-LD compliance.
Uses the pyshacl library for validation.

Reference: IFC2x3 SHACL schema (ingest/ifc2x3.fixed.fm4.ttl)
"""
import os
import sys
import pathlib
import argparse
import json
from typing import Dict, Any, Optional
from rdflib import Graph
import pyshacl


def validate_graph(
    data_graph_path: str,
    shacl_shapes_path: str,
    ont_graph_path: Optional[str] = None,
    inference: str = "none"
) -> Dict[str, Any]:
    """
    Validate an RDF graph against SHACL shapes.
    
    Args:
        data_graph_path: Path to RDF data graph (Turtle file)
        shacl_shapes_path: Path to SHACL shapes file
        ont_graph_path: Optional ontology graph for inference
        inference: Inference type ("none", "rdfs", "owl")
    
    Returns:
        Dictionary with validation results
    """
    data_path = pathlib.Path(data_graph_path)
    shapes_path = pathlib.Path(shacl_shapes_path)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data graph not found: {data_path}")
    
    if not shapes_path.exists():
        raise FileNotFoundError(f"SHACL shapes not found: {shapes_path}")
    
    print(f"🔍 Validating RDF graph against SHACL shapes...")
    print(f"   Data graph:  {data_path}")
    print(f"   SHACL shapes: {shapes_path}")
    
    # Load data graph
    data_graph = Graph()
    data_graph.parse(str(data_path), format='turtle')
    print(f"   Loaded {len(data_graph)} triples from data graph")
    
    # Load SHACL shapes
    shapes_graph = Graph()
    shapes_graph.parse(str(shapes_path), format='turtle')
    print(f"   Loaded {len(shapes_graph)} triples from SHACL shapes")
    
    # Load ontology graph if provided
    ont_graph = None
    if ont_graph_path and pathlib.Path(ont_graph_path).exists():
        ont_graph = Graph()
        ont_graph.parse(str(ont_graph_path), format='turtle')
        print(f"   Loaded {len(ont_graph)} triples from ontology graph")
    
    # Perform validation
    try:
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
            debug=False
        )
        
        # Parse validation results
        validation_results = {
            "conforms": conforms,
            "validation_passed": conforms,
            "triple_count": len(data_graph),
            "shapes_count": len(shapes_graph),
        }
        
        # Extract constraint violations
        violations = []
        if not conforms:
            # Parse results_graph for constraint violations
            for s, p, o in results_graph:
                if "ConstraintViolation" in str(p) or "ValidationResult" in str(p):
                    violations.append({
                        "subject": str(s),
                        "predicate": str(p),
                        "object": str(o)
                    })
        
        validation_results["violations"] = violations
        validation_results["violation_count"] = len(violations)
        validation_results["results_text"] = results_text
        
        if conforms:
            print(f"✅ Validation PASSED!")
            print(f"   No constraint violations found")
        else:
            print(f"❌ Validation FAILED!")
            print(f"   Found {len(violations)} constraint violation(s)")
            if violations:
                print(f"\n   Sample violations:")
                for v in violations[:5]:  # Show first 5
                    print(f"     - {v.get('subject', 'unknown')}: {v.get('predicate', 'unknown')}")
        
        return validation_results
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        raise


def validate_graphdb_repository(
    graphdb_client,
    shacl_shapes_path: str,
    repository: str = "rig-facility-mgmt"
) -> Dict[str, Any]:
    """
    Validate a GraphDB repository against SHACL shapes.
    
    Args:
        graphdb_client: GraphDBClient instance
        shacl_shapes_path: Path to SHACL shapes file
        repository: Repository name
    
    Returns:
        Dictionary with validation results
    """
    from ingest.graphdb_client import GraphDBClient
    
    shapes_path = pathlib.Path(shacl_shapes_path)
    
    if not shapes_path.exists():
        raise FileNotFoundError(f"SHACL shapes not found: {shapes_path}")
    
    print(f"🔍 Validating GraphDB repository against SHACL shapes...")
    print(f"   Repository: {repository}")
    print(f"   SHACL shapes: {shapes_path}")
    
    # Export repository data as Turtle
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Export repository to temporary file
        # Note: This is a simplified version - full implementation would
        # use GraphDB's export functionality
        print(f"   Exporting repository data...")
        
        # Use SPARQL CONSTRUCT to get all triples
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        results = graphdb_client.execute_sparql_query(query, output_format="turtle")
        
        # Write to temporary file
        with open(tmp_path, 'w', encoding='utf-8') as f:
            if isinstance(results, bytes):
                f.write(results.decode('utf-8'))
            else:
                f.write(str(results))
        
        # Validate the exported data
        return validate_graph(tmp_path, str(shapes_path))
        
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Validate RDF graphs against SHACL shapes"
    )
    parser.add_argument("data_graph", help="Path to RDF data graph (Turtle file)")
    parser.add_argument("shacl_shapes", help="Path to SHACL shapes file")
    parser.add_argument("--ontology", default=None,
                       help="Optional ontology graph for inference")
    parser.add_argument("--inference", default="none",
                       choices=["none", "rdfs", "owl"],
                       help="Inference type (default: none)")
    parser.add_argument("--output", default=None,
                       help="Output JSON file for validation results")
    
    args = parser.parse_args()
    
    try:
        results = validate_graph(
            args.data_graph,
            args.shacl_shapes,
            ont_graph_path=args.ontology,
            inference=args.inference
        )
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Validation results saved to: {args.output}")
        else:
            print(f"\n📊 Validation Results:")
            print(json.dumps(results, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if results["conforms"] else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

