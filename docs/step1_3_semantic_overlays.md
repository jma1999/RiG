Base data IRI (IFC instances): https://example.com/ifc/
Custom extension namespace:   https://example.com/rig#
Prefix: ex:

Ontologies to import into GraphDB (schema only):
- Brick:      prefix brick:
- SSN/SOSA:   prefix sosa:, ssn:
- QUDT:       prefix qudt:, unit:


Physical geometry         → IFC / ifcOWL
Semantic normalization    → ASHRAE 223P
Operational vocab         → Brick
Sensing & measurements    → SSN/SOSA
Units & quantities        → QUDT
Telemetry storage         → Time-series DB / R2 / S3


point: inst:IfcFlowTerminal_136276