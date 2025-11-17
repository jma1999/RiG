IFC → RDF → GraphDB (Sample House – 20210125Prova)

Source IFC file

Path: data/raw/ifc/sample_house/20210125Prova.ifc

Schema: IFC2x3 (matching ifc2x3.ttl SHACL shapes)

MVD reduction

Reduced IFC: data/processed/rdf/20210125Prova_reduced.ifc

Notes: Custom MVD reduction script; 35 entity types kept (actual counts in pipeline log).

IFC → RDF conversion

Tool: IFCtoRDF-0.4-SNAPSHOT-shaded.jar

Command wrapper: python -m ingest.ifc_to_rdf_pipeline

Output TTL: data/processed/rdf/20210125Prova_reduced.ttl

Base URI: https://example.com/ifc/

Output size: ~103 MB

GraphDB repository

ID: rig-facility-mgmt

Role: Published IFC graph for this test building

Graphs:

Main graph: contains ~1,383,248 triples (IFC/ifcOWL instances)

Ontology graphs: (to be added in later steps – Brick, 223, SSN/SOSA, QUDT)

SHACL validation

Shapes file: ingest/ifc2x3.ttl

Triples in data graph: 1,383,248

Triples in shapes graph: 20,773

Result: Validation PASSED – no constraint violations

Interpretation: RDF is conformant to the IFC2x3 IFC-LD SHACL profile for this MVD.

JSON-LD export

File: data/processed/rdf/20210125Prova_reduced.jsonld

Description: SHACL-validated JSON-LD serialization of the IFC graph in rig-facility-mgmt.

Intended role: portable digital twin snapshot for downstream GraphRAG / client apps.



hierarchy for my own reference:

IfcProject_7
   └── IfcRelAggregates_141429
         └── IfcSite_134948
               └── IfcRelAggregates_141428
                     └── IfcBuilding_134953   ← ✔ FOUND
