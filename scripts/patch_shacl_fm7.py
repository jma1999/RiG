#!/usr/bin/env python3
"""
fm10 SHACL patch:
- Relax node constraints on PropertyShapes with sh:path ifc:unit
- Relax minCount on PropertyShapes with sh:path ifc:dimensions

Usage:
  python scripts/patch_shacl_fm10_unit_dimensions.py \
    --in ingest/ifc2x3.fixed.fm9.ttl \
    --out ingest/ifc2x3.fixed.fm10.ttl
"""

from __future__ import annotations
import argparse
from typing import Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

SH = Namespace("http://www.w3.org/ns/shacl#")
IFC = Namespace("http://ifc-ld.org/schemas/ifc2x3#")


def _is_rdf_list(g: Graph, node) -> bool:
    return (node, RDF.first, None) in g or (node, RDF.rest, None) in g


def _remove_rdf_list(g: Graph, head) -> int:
    removed = 0
    cur = head
    seen = set()
    while cur and cur != RDF.nil and cur not in seen:
        seen.add(cur)
        for t in list(g.triples((cur, RDF.first, None))):
            g.remove(t); removed += 1
        nxt = g.value(cur, RDF.rest)
        for t in list(g.triples((cur, RDF.rest, None))):
            g.remove(t); removed += 1
        cur = nxt
    return removed


def _remove_predicate_objects(g: Graph, subj, pred: URIRef) -> int:
    removed = 0
    for _, _, obj in list(g.triples((subj, pred, None))):
        g.remove((subj, pred, obj)); removed += 1
        if _is_rdf_list(g, obj):
            removed += _remove_rdf_list(g, obj)
    return removed


def relax_propertyshapes_by_path(g: Graph, path_iri: URIRef, drop: Tuple[URIRef, ...]) -> int:
    """
    For every sh:PropertyShape where sh:path == path_iri, remove predicates in 'drop'
    (and any RDF list structures attached to them).
    """
    removed = 0
    for ps in set(g.subjects(RDF.type, SH.PropertyShape)):
        if g.value(ps, SH.path) != path_iri:
            continue
        for pred in drop:
            removed += _remove_predicate_objects(g, ps, pred)
    return removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    args = ap.parse_args()

    g = Graph()
    g.parse(args.in_path, format="turtle")

    # 1) Relax ifc:unit node constraints
    drop_unit = (
        SH.node,
        SH["class"],
        SH["and"],
        SH.xone,
        SH["or"],
        SH.datatype,
        SH["in"],  # sometimes present on unit value shapes
    )
    removed_unit = relax_propertyshapes_by_path(g, IFC.unit, drop_unit)

    # 2) Relax ifc:dimensions minCount
    removed_dimensions = relax_propertyshapes_by_path(g, IFC.dimensions, (SH.minCount,))

    g.serialize(destination=args.out_path, format="turtle")

    print("✅ fm10 patch complete")
    print(f"   Input:  {args.in_path}")
    print(f"   Output: {args.out_path}")
    print(f"   Relaxed ifc:unit (dropped node constraints): {removed_unit}")
    print(f"   Relaxed ifc:dimensions (removed sh:minCount): {removed_dimensions}")


if __name__ == "__main__":
    main()
