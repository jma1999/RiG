# ingest/mvd_reduction.py
"""
MVD (Model View Definition) Schema Reduction for Facility Management.

This module applies BuildingSMART Facility Management MVD rules to reduce
and optimize IFC files before RDF conversion. Uses IfcOpenShell to filter
entities based on MVD requirements.

Reference: BuildingSMART Facility Management MVD (IFC2x3.pdf)
"""
import os
import sys
import pathlib
import argparse
from typing import List, Set, Dict, Any, Optional, Iterable
import ifcopenshell

# Facility Management MVD - Core entity types to retain
# These are the essential types for facility management operations
FACILITY_MGMT_TYPES = {
    # Spatial structure
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    
    # Core building elements
    "IfcWall",
    "IfcWallStandardCase",
    "IfcSlab",
    "IfcRoof",
    "IfcDoor",
    "IfcWindow",
    "IfcColumn",
    "IfcBeam",
    "IfcStair",
    "IfcRailing",
    
    # Distribution systems (HVAC, Electrical, Plumbing)
    "IfcDistributionFlowElement",
    "IfcFlowTerminal",  # Diffusers, grilles, outlets
    "IfcFlowController",  # Valves, dampers
    "IfcFlowMovingDevice",  # Pumps, fans
    "IfcFlowStorageDevice",  # Tanks
    "IfcEnergyConversionDevice",  # AHUs, boilers
    "IfcFlowSegment",  # Ducts, pipes
    "IfcDistributionElement",  # Generic distribution
    "IfcDistributionChamberElement",  # Manholes, chambers
    
    # Systems
    "IfcSystem",
    "IfcDistributionSystem",
    
    # Relationships
    "IfcRelContainedInSpatialStructure",
    "IfcRelAggregates",
    "IfcRelServicesBuildings",
    "IfcRelAssignsToGroup",
    "IfcRelConnectsElements",
    "IfcRelConnectsPorts",
    "IfcRelConnectsPortToElement",
    "IfcRelDefinesByProperties",
    "IfcRelDefinesByType",
    
    # Property sets (essential for FM)
    "IfcPropertySet",
    "IfcPropertySingleValue",
    "IfcPropertyBoundedValue",
    "IfcPropertyEnumeratedValue",
    "IfcPropertyListValue",
    
    # Types and classifications
    "IfcTypeObject",
    "IfcPropertySetDefinition",
    
    # Material and quantity information
    "IfcMaterial",
    "IfcMaterialList",
    "IfcMaterialLayer",
    "IfcElementQuantity",
    
    # Geometric representation (for visualization)
    "IfcProductDefinitionShape",
    "IfcShapeRepresentation",
    "IfcGeometricRepresentationItem",
}

def _iter_refs_forward(entity):
    """Yield forward references from entity attributes."""
    try:
        for attr in entity:
            if attr is None:
                continue
            if isinstance(attr, (list, tuple)):
                for item in attr:
                    if hasattr(item, "id"):
                        yield item
            else:
                if hasattr(attr, "id"):
                    yield attr
    except Exception:
        return

def _iter_refs_inverse(ifc_file: ifcopenshell.file, entity):
    """Yield inverse references (things that point to this entity)."""
    try:
        # In IfcOpenShell, get_inverse returns all inverse relationships
        inv = ifc_file.get_inverse(entity)
        for x in inv:
            yield x
    except Exception:
        return

def _bfs_closure(ifc_file: ifcopenshell.file, seeds: Iterable, max_nodes: Optional[int] = None) -> Set[int]:
    """
    Compute transitive closure of reachable entities by forward + inverse refs.
    Returns a set of STEP ids (entity.id()).
    """
    keep_ids: Set[int] = set()
    queue = []

    for s in seeds:
        try:
            sid = s.id()
            if sid and sid not in keep_ids:
                keep_ids.add(sid)
                queue.append(s)
        except Exception:
            continue

    while queue:
        cur = queue.pop()
        # forward refs
        for nxt in _iter_refs_forward(cur):
            try:
                nid = nxt.id()
                if nid and nid not in keep_ids:
                    keep_ids.add(nid)
                    queue.append(nxt)
            except Exception:
                pass

        # inverse refs
        for nxt in _iter_refs_inverse(ifc_file, cur):
            try:
                nid = nxt.id()
                if nid and nid not in keep_ids:
                    keep_ids.add(nid)
                    queue.append(nxt)
            except Exception:
                pass

        if max_nodes is not None and len(keep_ids) >= max_nodes:
            break

    return keep_ids

def _count_step_entities(path: pathlib.Path) -> int:
    n = 0
    with open(path, "r", errors="ignore") as f:
        for line in f:
            if line.lstrip().startswith("#") and "=" in line:
                n += 1
    return n

def apply_mvd_reduction(input_path: str, output_path: str, base_uri: Optional[str] = None) -> Dict[str, Any]:
    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"📖 Loading IFC file: {input_path}")
    ifc_file = ifcopenshell.open(str(input_path))

    initial_step_count = _count_step_entities(input_path)
    print(f"📊 Initial STEP entity count: {initial_step_count}")

    # 1) Seed selection (FM types)
    seeds = []
    type_counts: Dict[str, int] = {}
    for t in FACILITY_MGMT_TYPES:
        try:
            ents = ifc_file.by_type(t)
            if ents:
                type_counts[t] = len(ents)
                seeds.extend(ents)
        except Exception:
            continue

    print(f"🌱 Seed entities collected: {len(seeds)} (across {len(type_counts)} types)")
    print("🔗 Building referential closure (forward + inverse refs)...")

    keep_ids = _bfs_closure(ifc_file, seeds)
    print(f"✅ Closure size (unique STEP ids): {len(keep_ids)}")

    # 2) Copy subset to new file
    # IfcOpenShell 0.8.x includes util.file for copying; API differs slightly across versions.
    # We'll use a robust pattern: create target file and add entities by "add()" which deep-copies dependencies.
    schema_version = ifc_file.schema
    reduced = ifcopenshell.file(schema=schema_version)

    # Copy header (minimal)
    try:
        reduced.wrapped_data.header = ifc_file.wrapped_data.header
    except Exception:
        pass

    # IMPORTANT:
    # reduced.add(entity) in IfcOpenShell will clone the entity and referenced entities,
    # but we only want those in keep_ids. So we add in a stable order and skip others.
    # We'll first map id->entity from original.
    id_map = {}
    for e in ifc_file:
        try:
            id_map[e.id()] = e
        except Exception:
            continue

    # Add entities in ascending STEP id order to preserve stability
    added = 0
    for sid in sorted(keep_ids):
        ent = id_map.get(sid)
        if ent is None:
            continue
        try:
            reduced.add(ent)
            added += 1
        except Exception:
            # Some entities may fail to add individually; ignore and continue
            pass

    print(f"✂️  Added to reduced file (attempted): {added}")

    print(f"💾 Saving reduced IFC file: {output_path}")
    reduced.write(str(output_path))

    final_step_count = _count_step_entities(output_path)
    reduction_pct = (1 - (final_step_count / initial_step_count)) * 100 if initial_step_count else 0.0

    stats = {
        "initial_step_entities": initial_step_count,
        "final_step_entities": final_step_count,
        "selected_closure_ids": len(keep_ids),
        "seed_count": len(seeds),
        "reduction_percentage": round(reduction_pct, 2),
        "type_counts": type_counts,
    }

    print("✅ MVD reduction complete!")
    print(f"   Initial STEP entities: {initial_step_count}")
    print(f"   Final   STEP entities: {final_step_count}")
    print(f"   Reduction: {reduction_pct:.2f}%")
    print(f"   Seed types used: {len(type_counts)}")

    return stats



def main():
    parser = argparse.ArgumentParser(
        description="Apply Facility Management MVD reduction to IFC files"
    )
    parser.add_argument("input", help="Path to input IFC-SPF file")
    parser.add_argument("output", help="Path to output reduced IFC-SPF file")
    parser.add_argument("--base-uri", default=None, 
                       help="Base URI for RDF conversion (optional)")
    
    args = parser.parse_args()
    
    try:
        stats = apply_mvd_reduction(args.input, args.output, args.base_uri)
        print(f"\n📈 Reduction Statistics:")
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for k, v in value.items():
                    print(f"     {k}: {v}")
            else:
                print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

