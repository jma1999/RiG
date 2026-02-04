# Evaluation Metrics (Generated)

- Timestamp: `2026-02-04T17:50:02.718068+00:00`
- RDF triples (combined): `1383356`
- Queries executed: `20`
- Non-empty query results: `17`
- Correctness proxy (non-empty %): `85.0%`
- Avg. 2-hop neighborhood triples: `1508.8`

## Coverage by Category

| Category | Non-empty / Total |
|---|---|
| Spatial | 3 / 5 |
| System | 4 / 5 |
| Cross-domain | 5 / 5 |
| Temporal | 5 / 5 |

## TimescaleDB Availability

- Available: `True`
- Rows for `ft_136276_sat`: `241`

## Per-Query Summary

| Type | Query | Rows | Count/Value | Non-empty | 2-hop Triples | Schemas |
|---|---|---:|---:|:---:|---:|---|
| Spatial | Count IfcSpace | 1 | 0 | No | 0 | IFC |
| Spatial | Count IfcBuildingStorey | 1 | 3 | Yes | 3260 | IFC |
| Spatial | Count IfcDoor | 1 | 1 | Yes | 2994 | IFC |
| Spatial | Count IfcWindow | 1 | 4 | Yes | 3366 | IFC |
| Spatial | List IfcSpace (sample) | 0 | - | No | 0 | IFC |
| System | Count IfcFlowTerminal | 1 | 10 | Yes | 3307 | IFC |
| System | Count IfcEnergyConversionDevice | 1 | 1 | Yes | 3103 | IFC |
| System | Count IfcFlowSegment | 1 | 42 | Yes | 3505 | IFC |
| System | Count IfcDistributionElement | 1 | 0 | No | 0 | IFC |
| System | Count IfcSystem | 1 | 3 | Yes | 2723 | IFC |
| Cross-domain | Brick+223P points | 5 | - | Yes | 79 | Brick, ASHRAE223P |
| Cross-domain | SOSA observable properties | 4 | - | Yes | 76 | SOSA |
| Cross-domain | QUDT unit bindings | 4 | - | Yes | 74 | QUDT |
| Cross-domain | Brick sensors (SAT) | 1 | - | Yes | 61 | Brick |
| Cross-domain | 223P equipment | 1 | - | Yes | 84 | ASHRAE223P |
| Temporal | Count SAT rows (last 60 min) | 1 | 57 | Yes | 0 | TimescaleDB |
| Temporal | Latest SAT value | 1 | 19.49 | Yes | 0 | TimescaleDB |
| Temporal | Avg SAT value (last 60 min) | 1 | 19.89771929824561 | Yes | 0 | TimescaleDB |
| Temporal | Min/Max SAT value (last 60 min) | 1 | (19.49, 20.21) | Yes | 0 | TimescaleDB |
| Temporal | 15-min buckets SAT (last 60 min) | 5 | 5 | Yes | 0 | TimescaleDB |
