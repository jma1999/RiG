"""
Enterprise Graph API Endpoints

Exposes cross-domain graph queries with named subgraphs:
- controls/* (BACnet, BMS)
- finance/* (EBS/Kuali billing)
- hr/* (Workday org structure)
- workorders/* (Maximo assets, WOs)
- space/* (Facilities Inventory, IFC-LD)
- net/* (Network topology)
- scheduling/* (Office365 calendars)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.graphdb import get_graphdb_client
from ingest.data_contracts import get_contract, list_contracts, validate_contract_compliance

router = APIRouter(prefix="/enterprise", tags=["enterprise-graph"])


class GraphQueryRequest(BaseModel):
    """Request model for graph queries"""
    query: str
    domain: Optional[str] = None
    context_version: Optional[str] = None


class EntityRequest(BaseModel):
    """Request model for entity retrieval"""
    iri: str
    domain: Optional[str] = None
    include_neighbors: bool = False
    depth: int = 1


@router.get("/domains")
async def list_domains():
    """List all available domain subgraphs"""
    return {
        "domains": list_contracts(),
        "subgraphs": {
            "controls": "BACnet, BMS, points, equipment",
            "finance": "EBS/Kuali billing, meters, cost centers",
            "hr": "Workday org structure, roles, responsibility",
            "workorders": "Maximo assets, work orders, PM schedules",
            "space": "Facilities Inventory, IFC-LD/LBD spaces",
            "net": "Network topology, VLANs, switches",
            "scheduling": "Office365 calendars, occupancy"
        }
    }


@router.get("/contracts/{domain}")
async def get_domain_contract(domain: str):
    """Get data contract for a domain"""
    contract = get_contract(domain)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract not found for domain: {domain}")
    return contract.to_dict()


@router.post("/graph/{iri:path}")
async def get_entity(iri: str, request: Optional[EntityRequest] = None):
    """
    Get compacted JSON-LD for any entity (with context version).
    
    Supports cross-domain queries by following owl:sameAs links.
    """
    # Decode IRI if needed
    if request and request.iri:
        iri = request.iri
    
    # SPARQL query to get entity with context
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    CONSTRUCT {{
        <{iri}> ?p ?o .
        ?o ?p2 ?o2 .
    }}
    WHERE {{
        {{
            <{iri}> ?p ?o .
        }}
        UNION
        {{
            <{iri}> owl:sameAs ?same .
            ?same ?p ?o .
        }}
        OPTIONAL {{
            ?o ?p2 ?o2 .
        }}
    }}
    LIMIT 1000
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "iri": iri,
            "data": result,
            "context_version": "brick:1.3.0, s223:1.0.0, qudt:2.1.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/cross-domain/{entity_type}")
async def cross_domain_query(
    entity_type: str,
    entity_id: str = Query(..., description="Entity identifier"),
    domains: Optional[str] = Query(None, description="Comma-separated list of domains to query")
):
    """
    Cross-domain query: find entity across multiple domains.
    
    Example: "Who is responsible for the AHU serving the conference room that's overheating?"
    Returns: person (Workday) + equipment (controls) + space (IFC-LD) + diagnosis (FDD)
    """
    domain_list = domains.split(",") if domains else list_contracts()
    
    # Build SPARQL query to find entity across domains
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX s223: <http://data.ashrae.org/standard223#>
    
    SELECT DISTINCT ?entity ?type ?domain ?label ?related
    WHERE {{
        {{
            ?entity rdf:type ?type .
            ?entity rdfs:label ?label .
            
            # Identify domain based on properties
            OPTIONAL {{
                ?entity ex:hasWorkdayId ?wd_id .
                BIND("hr" AS ?domain)
            }}
            OPTIONAL {{
                ?entity ex:hasMaximoAssetId ?max_id .
                BIND("workorders" AS ?domain)
            }}
            OPTIONAL {{
                ?entity ex:hasOffice365CalendarId ?cal_id .
                BIND("scheduling" AS ?domain)
            }}
            OPTIONAL {{
                ?entity ex:bacnetDeviceInstance ?bac_id .
                BIND("controls" AS ?domain)
            }}
            OPTIONAL {{
                ?entity ex:hasCostCenter ?cc .
                BIND("finance" AS ?domain)
            }}
            OPTIONAL {{
                ?entity ex:belongsToVLAN ?vlan .
                BIND("net" AS ?domain)
            }}
            
            # Find related entities
            OPTIONAL {{
                ?entity ?rel ?related .
                FILTER(?rel != rdf:type && ?rel != rdfs:label)
            }}
            
            # Filter by entity identifier (simplified - would need more sophisticated matching)
            FILTER(CONTAINS(LCASE(STR(?entity)), LCASE("{entity_id}")) ||
                   CONTAINS(LCASE(STR(?label)), LCASE("{entity_id}")))
        }}
    }}
    LIMIT 100
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "domains_queried": domain_list,
            "results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cross-domain query failed: {str(e)}")


@router.get("/fdd/{building}")
async def get_fdd_faults(building: str):
    """
    Get open faults with root causes & confidence for a building.
    
    Combines data from:
    - controls/* (sensor data, alarms)
    - workorders/* (asset status)
    - net/* (network diagnostics)
    """
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    
    SELECT ?fault ?severity ?root_cause ?confidence ?equipment ?zone
    WHERE {{
        ?fault a ex:Fault ;
               ex:severity ?severity ;
               ex:rootCause ?root_cause ;
               ex:confidence ?confidence ;
               ex:affectsEquipment ?equipment ;
               ex:affectsZone ?zone .
        
        ?equipment brick:locatedIn ?building .
        FILTER(CONTAINS(LCASE(STR(?building)), LCASE("{building}")))
        
        FILTER(?severity IN ("WARNING", "CRITICAL"))
    }}
    ORDER BY DESC(?severity) DESC(?confidence)
    LIMIT 50
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "building": building,
            "faults": result,
            "timestamp": "2024-01-15T10:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FDD query failed: {str(e)}")


@router.get("/finance/meters/{meter_id}/billing")
async def get_meter_billing(meter_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Get billing history and cost allocation for a meter.
    
    Combines:
    - finance/* (billing records)
    - space/* (space allocation)
    """
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?meter ?billing_period ?cost ?cost_center ?space
    WHERE {{
        ?meter a brick:Meter ;
               ex:hasBillingId "{meter_id}" .
        
        ?billing_record ex:forMeter ?meter ;
                        ex:billingPeriod ?billing_period ;
                        ex:cost ?cost ;
                        ex:allocatedToCostCenter ?cost_center ;
                        ex:allocatedToSpace ?space .
        
        {"FILTER(?billing_period >= \"" + start_date + "\"^^xsd:date && ?billing_period <= \"" + end_date + "\"^^xsd:date)" if start_date and end_date else ""}
    }}
    ORDER BY DESC(?billing_period)
    LIMIT 100
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "meter_id": meter_id,
            "billing_history": result,
            "contract": get_contract("finance").to_dict() if get_contract("finance") else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Billing query failed: {str(e)}")


@router.get("/hr/org/{person_id}/responsibility")
async def get_person_responsibility(person_id: str):
    """
    Get responsibility chain and on-call routing for a person.
    
    Combines:
    - hr/* (Workday org structure, roles)
    - controls/* (equipment they're responsible for)
    - space/* (zones/buildings)
    """
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX org: <http://www.w3.org/ns/org#>
    
    SELECT ?person ?name ?role ?organization ?responsible_for ?on_call_for
    WHERE {{
        ?person ex:hasWorkdayId "{person_id}" ;
                foaf:name ?name ;
                ex:hasRole ?role ;
                ex:belongsToOrganization ?organization .
        
        OPTIONAL {{
            ?person ex:responsibleFor ?responsible_for .
        }}
        OPTIONAL {{
            ?person ex:onCallFor ?on_call_for .
        }}
    }}
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "person_id": person_id,
            "responsibility_chain": result,
            "contract": get_contract("hr").to_dict() if get_contract("hr") else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Responsibility query failed: {str(e)}")


@router.get("/workorders/assets/{asset_id}/lifecycle")
async def get_asset_lifecycle(asset_id: str):
    """
    Get asset history, PM schedule, and spares for an asset.
    
    Combines:
    - workorders/* (Maximo asset data, WOs, PM schedules)
    - controls/* (equipment status)
    """
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    
    SELECT ?asset ?status ?install_date ?pm_schedule ?work_order ?spares
    WHERE {{
        ?asset ex:hasMaximoAssetId "{asset_id}" ;
               ex:assetStatus ?status ;
               ex:installDate ?install_date .
        
        OPTIONAL {{
            ?pm_schedule ex:appliesToAsset ?asset ;
                        ex:frequency ?freq ;
                        ex:nextDueDate ?next_due .
        }}
        OPTIONAL {{
            ?work_order ex:relatedToAsset ?asset ;
                        ex:woStatus ?wo_status .
        }}
        OPTIONAL {{
            ?asset ex:hasSpares ?spares .
        }}
    }}
    ORDER BY DESC(?install_date)
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "asset_id": asset_id,
            "lifecycle": result,
            "contract": get_contract("workorders").to_dict() if get_contract("workorders") else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lifecycle query failed: {str(e)}")


@router.get("/scheduling/spaces/{space_id}/occupancy")
async def get_space_occupancy(space_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None):
    """
    Get calendar bookings, occupancy proxy, and setpoint recommendations for a space.
    
    Combines:
    - scheduling/* (Office365 calendars, events)
    - controls/* (setpoint data)
    - space/* (IFC-LD space data)
    """
    query = f"""
    PREFIX ex: <https://example.com/rig#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX s223: <http://data.ashrae.org/standard223#>
    
    SELECT ?space ?calendar ?event ?start_time ?end_time ?occupancy_proxy ?setpoint_recommendation
    WHERE {{
        ?space a s223:Zone ;
               ex:hasOffice365CalendarId ?calendar .
        
        OPTIONAL {{
            ?event ex:forSpace ?space ;
                   ex:startTime ?start_time ;
                   ex:endTime ?end_time .
        }}
        OPTIONAL {{
            ?space ex:hasOccupancyProxy ?occupancy_proxy .
        }}
        OPTIONAL {{
            ?space ex:hasSetpointRecommendation ?setpoint_recommendation .
        }}
        
        FILTER(CONTAINS(LCASE(STR(?space)), LCASE("{space_id}")))
    }}
    ORDER BY ?start_time
    LIMIT 50
    """
    
    try:
        client = get_graphdb_client()
        result = client.execute_sparql_query(query, output_format="json")
        return {
            "space_id": space_id,
            "occupancy": result,
            "contract": get_contract("scheduling").to_dict() if get_contract("scheduling") else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Occupancy query failed: {str(e)}")


@router.get("/audits/validation")
async def get_validation_audits(domain: Optional[str] = None):
    """
    Get latest SHACL validation reports per domain.
    
    Returns validation status for each domain subgraph.
    """
    from ingest.shacl_validation import validate_graphdb_repository
    from ingest.graphdb_client import GraphDBClient
    
    domains = [domain] if domain else list_contracts()
    results = {}
    
    try:
        graphdb_client = GraphDBClient()
        
        for dom in domains:
            contract = get_contract(dom)
            if not contract:
                continue
            
            # Get SHACL shapes for this domain
            shapes_path = contract.shapes[0] if contract.shapes else None
            if shapes_path and os.path.exists(shapes_path):
                try:
                    validation = validate_graphdb_repository(graphdb_client, shapes_path)
                    results[dom] = {
                        "domain": dom,
                        "contract": contract.to_dict(),
                        "validation": validation,
                        "timestamp": "2024-01-15T10:00:00Z"
                    }
                except Exception as e:
                    results[dom] = {
                        "domain": dom,
                        "error": str(e)
                    }
            else:
                results[dom] = {
                    "domain": dom,
                    "error": "SHACL shapes file not found"
                }
        
        return {
            "audits": results,
            "timestamp": "2024-01-15T10:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation audit failed: {str(e)}")

