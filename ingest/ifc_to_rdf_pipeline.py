# ingest/ifc_to_rdf_pipeline.py
"""
Complete IFC to RDF Pipeline.

This script orchestrates the complete pipeline from IFC-SPF to RDF graph:
1. MVD schema reduction
2. IFC to RDF (Turtle) conversion
3. GraphDB ingestion
4. SHACL validation
5. JSON-LD export (optional)

Usage:
    python ingest/ifc_to_rdf_pipeline.py input.ifc --output-dir data/processed/rdf/
"""
import os
import sys
import pathlib
import argparse
import json
from typing import Optional, Dict, Any

# Import pipeline components
from ingest.mvd_reduction import apply_mvd_reduction
from ingest.ifc_to_rdf import convert_ifc_to_turtle
from ingest.graphdb_client import GraphDBClient
from ingest.shacl_validation import validate_graph


def run_pipeline(
    input_ifc: str,
    output_dir: str,
    base_uri: Optional[str] = None,
    graphdb_url: str = "http://localhost:7200",
    graphdb_repo: str = "rig-facility-mgmt",
    validate: bool = True,
    shacl_shapes: Optional[str] = None,
    export_jsonld: bool = False,
    skip_mvd: bool = False
) -> Dict[str, Any]:
    """
    Run complete IFC to RDF pipeline.
    
    Args:
        input_ifc: Path to input IFC-SPF file
        output_dir: Output directory for processed files
        base_uri: Base URI for RDF resources
        graphdb_url: GraphDB base URL
        graphdb_repo: GraphDB repository name
        validate: Whether to run SHACL validation
        shacl_shapes: Path to SHACL shapes file (defaults to ingest/ifc2x3.ttl)
        export_jsonld: Whether to export as JSON-LD
        skip_mvd: Skip MVD reduction step
    
    Returns:
        Dictionary with pipeline results
    """
    input_path = pathlib.Path(input_ifc)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pipeline_results = {
        "input_file": str(input_path),
        "output_dir": str(output_dir),
        "steps": {},
        "success": False
    }
    
    print("🚀 Starting IFC to RDF Pipeline")
    print("=" * 60)
    
    # Step 1: MVD Reduction
    if not skip_mvd:
        print("\n📋 Step 1: MVD Schema Reduction")
        print("-" * 60)
        reduced_ifc = output_dir / (input_path.stem + "_reduced.ifc")
        
        try:
            mvd_stats = apply_mvd_reduction(
                str(input_path),
                str(reduced_ifc),
                base_uri=base_uri
            )
            pipeline_results["steps"]["mvd_reduction"] = mvd_stats
            current_ifc = reduced_ifc
            print(f"✅ MVD reduction complete")
        except Exception as e:
            print(f"⚠️  MVD reduction failed: {e}")
            print("   Continuing with original file...")
            current_ifc = input_path
            pipeline_results["steps"]["mvd_reduction"] = {"error": str(e)}
    else:
        print("\n⏭️  Skipping MVD reduction (--skip-mvd)")
        current_ifc = input_path
    
    # Step 2: IFC to RDF Conversion
    print("\n🔄 Step 2: IFC to RDF (Turtle) Conversion")
    print("-" * 60)
    turtle_file = output_dir / (pathlib.Path(current_ifc).stem + ".ttl")
    
    try:
        rdf_stats = convert_ifc_to_turtle(
            str(current_ifc),
            str(turtle_file),
            base_uri=base_uri
        )
        pipeline_results["steps"]["rdf_conversion"] = rdf_stats
        print(f"✅ RDF conversion complete")
    except Exception as e:
        print(f"❌ RDF conversion failed: {e}")
        pipeline_results["steps"]["rdf_conversion"] = {"error": str(e)}
        return pipeline_results
    
    # Step 3: GraphDB Ingestion
    print("\n💾 Step 3: GraphDB Ingestion")
    print("-" * 60)
    
    try:
        client = GraphDBClient(
            base_url=graphdb_url,
            repository=graphdb_repo
        )
        
        # Create repository if it doesn't exist
        if not client.repository_exists():
            print(f"   Creating repository '{graphdb_repo}'...")
            client.create_repository()
        
        # Load Turtle file
        load_success = client.load_turtle_file(str(turtle_file))
        
        if load_success:
            stats = client.get_statistics()
            pipeline_results["steps"]["graphdb_ingestion"] = stats
            print(f"✅ GraphDB ingestion complete")
        else:
            pipeline_results["steps"]["graphdb_ingestion"] = {"error": "Failed to load"}
            print(f"⚠️  GraphDB ingestion had issues")
            
    except Exception as e:
        print(f"❌ GraphDB ingestion failed: {e}")
        pipeline_results["steps"]["graphdb_ingestion"] = {"error": str(e)}
        # Continue anyway - validation can work on Turtle file
    
    # Step 4: SHACL Validation
    if validate:
        print("\n✅ Step 4: SHACL Validation")
        print("-" * 60)
        
        if shacl_shapes is None:
            # Default to ingest/ifc2x3.ttl
            shacl_shapes = pathlib.Path(__file__).parent / "ifc2x3.ttl"
        else:
            shacl_shapes = pathlib.Path(shacl_shapes)
        
        if shacl_shapes.exists():
            try:
                validation_results = validate_graph(
                    str(turtle_file),
                    str(shacl_shapes)
                )
                pipeline_results["steps"]["shacl_validation"] = validation_results
                
                if validation_results.get("conforms", False):
                    print(f"✅ SHACL validation PASSED")
                else:
                    print(f"⚠️  SHACL validation found {validation_results.get('violation_count', 0)} violations")
            except Exception as e:
                print(f"⚠️  SHACL validation error: {e}")
                pipeline_results["steps"]["shacl_validation"] = {"error": str(e)}
        else:
            print(f"⚠️  SHACL shapes file not found: {shacl_shapes}")
            pipeline_results["steps"]["shacl_validation"] = {"error": "SHACL shapes file not found"}
    
    # Step 5: JSON-LD Export (optional)
    if export_jsonld:
        print("\n📤 Step 5: JSON-LD Export")
        print("-" * 60)
        
        try:
            jsonld_file = output_dir / (pathlib.Path(current_ifc).stem + ".jsonld")
            export_success = client.export_as_jsonld(str(jsonld_file))
            
            if export_success:
                pipeline_results["steps"]["jsonld_export"] = {
                    "output_file": str(jsonld_file)
                }
                print(f"✅ JSON-LD export complete")
            else:
                pipeline_results["steps"]["jsonld_export"] = {"error": "Export failed"}
        except Exception as e:
            print(f"⚠️  JSON-LD export error: {e}")
            pipeline_results["steps"]["jsonld_export"] = {"error": str(e)}
    
    # Pipeline summary
    print("\n" + "=" * 60)
    print("📊 Pipeline Summary")
    print("=" * 60)
    
    success = (
        "rdf_conversion" in pipeline_results["steps"] and
        "error" not in pipeline_results["steps"]["rdf_conversion"]
    )
    
    pipeline_results["success"] = success
    
    if success:
        print("✅ Pipeline completed successfully!")
    else:
        print("⚠️  Pipeline completed with errors")
    
    print(f"\n📁 Output files:")
    print(f"   Turtle: {turtle_file}")
    if "jsonld_export" in pipeline_results["steps"]:
        jsonld_file = pipeline_results["steps"]["jsonld_export"].get("output_file")
        if jsonld_file:
            print(f"   JSON-LD: {jsonld_file}")
    
    return pipeline_results


def main():
    parser = argparse.ArgumentParser(
        description="Complete IFC to RDF pipeline with MVD reduction, conversion, GraphDB ingestion, and SHACL validation"
    )
    parser.add_argument("input", help="Path to input IFC-SPF file")
    parser.add_argument("--output-dir", default="data/processed/rdf",
                       help="Output directory for processed files")
    parser.add_argument("--base-uri", default=None,
                       help="Base URI for RDF resources (e.g., https://example.com/ifc/)")
    parser.add_argument("--graphdb-url", default="http://localhost:7200",
                       help="GraphDB base URL")
    parser.add_argument("--graphdb-repo", default="rig-facility-mgmt",
                       help="GraphDB repository name")
    parser.add_argument("--skip-validation", action="store_true",
                       help="Skip SHACL validation")
    parser.add_argument("--shacl-shapes", default=None,
                       help="Path to SHACL shapes file (defaults to ingest/ifc2x3.ttl)")
    parser.add_argument("--export-jsonld", action="store_true",
                       help="Export as JSON-LD")
    parser.add_argument("--skip-mvd", action="store_true",
                       help="Skip MVD schema reduction")
    parser.add_argument("--results", default=None,
                       help="Output JSON file for pipeline results")
    
    args = parser.parse_args()
    
    try:
        results = run_pipeline(
            input_ifc=args.input,
            output_dir=args.output_dir,
            base_uri=args.base_uri,
            graphdb_url=args.graphdb_url,
            graphdb_repo=args.graphdb_repo,
            validate=not args.skip_validation,
            shacl_shapes=args.shacl_shapes,
            export_jsonld=args.export_jsonld,
            skip_mvd=args.skip_mvd
        )
        
        # Save results if requested
        if args.results:
            with open(args.results, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Pipeline results saved to: {args.results}")
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

