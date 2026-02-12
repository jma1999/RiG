#!/bin/bash
# Run the IFC-to-RDF pipeline on 20231012_CASE Office.ifc
# Uses IFC-LD native converter and optional LLM-based SPARQL
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

INPUT_IFC="data/raw/ifc/20231012_CASE Office.ifc"
OUTPUT_DIR="data/processed/rdf"

if [ ! -f "$INPUT_IFC" ]; then
  echo "Input file not found: $INPUT_IFC"
  exit 1
fi

echo "=== RiG IFC-to-RDF Pipeline ==="
echo "Input: $INPUT_IFC"
echo "Output: $OUTPUT_DIR"
echo ""

# IFC-LD service URL (default to 5050 because macOS Control Center often occupies 5000)
IFCLD_BASE_URL="${IFCLD_SERVICE_URL:-http://localhost:5050}"

# 1. Check IFC-LD service (POST /instances is the main endpoint; GET may 404)
if ! curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "${IFCLD_BASE_URL}/" 2>/dev/null | grep -qE "200|404|405|500"; then
  echo "⚠️  IFC-LD service not reachable at ${IFCLD_BASE_URL}"
  echo "   Start it with: docker compose --profile ifcld up -d ifcld-service"
  echo "   Or: docker build -f Dockerfile.ifcld . && docker run -d -p 5050:5000 rig-ifcld"
  echo ""
fi

# 2. Run pipeline (ifcld converter by default)
echo "Running pipeline..."
PYTHONPATH="$(pwd)" python -m ingest.ifc_to_rdf_pipeline "$INPUT_IFC" \
  --output-dir "$OUTPUT_DIR" \
  --converter ifcld \
  --ifcld-url "$IFCLD_BASE_URL" \
  --export-jsonld \
  --results "$OUTPUT_DIR/pipeline_results.json"

echo ""
echo "=== Done ==="
echo "Turtle output: $OUTPUT_DIR/20231012_CASE Office.ttl"
echo ""
echo "To run GraphRAG with LLM (set OPENAI_API_KEY):"
echo "  python rag/sparql_rag.py 'How many doors are in the building?' --output evidence.json"
echo ""
echo "Or with heuristics only:"
echo "  python rag/sparql_rag.py 'How many doors are in the building?' --no-llm --output evidence.json"
