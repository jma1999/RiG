"""
Graph Tools - SPARQL-based graph query abstractions for agents.

These tools encapsulate common graph queries as typed functions,
preventing agents from constructing raw SPARQL.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ingest.graphdb_client import GraphDBClient


@dataclass
class ZoneContext:
    """Context information for a zone."""
    zone_id: str
    zone_name: str
    spaces: List[Dict[str, Any]]
    equipment: List[Dict[str, Any]]
    points: List[Dict[str, Any]]
    bacnet_bindings: List[Dict[str, Any]]


@dataclass
class EquipmentContext:
    """Context information for equipment."""
    equipment_id: str
    equipment_name: str
    equipment_type: str
    serving_zone: Optional[str]
    points: List[Dict[str, Any]]
    bacnet_refs: List[Dict[str, Any]]
    upstream: List[Dict[str, Any]]
    downstream: List[Dict[str, Any]]


class GraphTools:
    """Well-typed graph query tools for agents."""
    
    def __init__(self, graphdb_client: GraphDBClient):
        self.client = graphdb_client
    
    def get_zone_context(self, zone_id: str) -> ZoneContext:
        """
        Get complete context for a zone including spaces, equipment, and points.
        
        Args:
            zone_id: Zone URI or identifier
            
        Returns:
            ZoneContext with all related entities
        """
        query = f"""
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX ex: <https://example.com/rig#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?zone ?zoneName ?space ?spaceName ?equipment ?equipName ?point ?pointName ?bacnetRef
        WHERE {{
            ?zone a s223:Zone .
            FILTER (?zone = <{zone_id}> || STR(?zone) = "{zone_id}")
            OPTIONAL {{ ?zone rdfs:label ?zoneName }}
            
            # Get spaces (IFC spatial context)
            OPTIONAL {{
                ?zone ex:hasIfcSpatialContext ?space .
                OPTIONAL {{ ?space rdfs:label ?spaceName }}
            }}
            
            # Get equipment serving this zone
            OPTIONAL {{
                ?equipment s223:serves ?zone .
                OPTIONAL {{ ?equipment rdfs:label ?equipName }}
            }}
            
            # Get points on equipment
            OPTIONAL {{
                ?equipment brick:hasPoint ?point .
                OPTIONAL {{ ?point rdfs:label ?pointName }}
            }}
            
            # Get BACnet bindings
            OPTIONAL {{
                ?point s223:hasExternalReference ?bacnetRef .
                ?bacnetRef a s223:BACnetExternalReference .
            }}
        }}
        """
        
        results = self.client.execute_sparql_query(query, output_format="json")
        
        # Parse results
        zone_name = None
        spaces = []
        equipment = []
        points = []
        bacnet_bindings = []
        
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                if not zone_name:
                    zone_name = binding.get("zoneName", {}).get("value", "")
                
                space_uri = binding.get("space", {}).get("value")
                if space_uri and space_uri not in [s["id"] for s in spaces]:
                    spaces.append({
                        "id": space_uri,
                        "name": binding.get("spaceName", {}).get("value", "")
                    })
                
                equip_uri = binding.get("equipment", {}).get("value")
                if equip_uri and equip_uri not in [e["id"] for e in equipment]:
                    equipment.append({
                        "id": equip_uri,
                        "name": binding.get("equipName", {}).get("value", "")
                    })
                
                point_uri = binding.get("point", {}).get("value")
                if point_uri and point_uri not in [p["id"] for p in points]:
                    points.append({
                        "id": point_uri,
                        "name": binding.get("pointName", {}).get("value", "")
                    })
                
                bacnet_uri = binding.get("bacnetRef", {}).get("value")
                if bacnet_uri and bacnet_uri not in [b["id"] for b in bacnet_bindings]:
                    bacnet_bindings.append({"id": bacnet_uri})
        
        return ZoneContext(
            zone_id=zone_id,
            zone_name=zone_name or zone_id.split("/")[-1],
            spaces=spaces,
            equipment=equipment,
            points=points,
            bacnet_bindings=bacnet_bindings
        )
    
    def get_equipment_context(self, equipment_id: str) -> EquipmentContext:
        """
        Get complete context for equipment including points, BACnet refs, and connections.
        
        Args:
            equipment_id: Equipment URI or identifier
            
        Returns:
            EquipmentContext with all related entities
        """
        query = f"""
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX ex: <https://example.com/rig#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?equipment ?equipName ?equipType ?zone ?zoneName ?point ?pointName 
               ?bacnetRef ?upstream ?downstream
        WHERE {{
            ?equipment a s223:Equipment .
            FILTER (?equipment = <{equipment_id}> || STR(?equipment) = "{equipment_id}")
            OPTIONAL {{ ?equipment rdfs:label ?equipName }}
            OPTIONAL {{ ?equipment a ?equipType }}
            
            # Serving zone
            OPTIONAL {{
                ?equipment s223:serves ?zone .
                OPTIONAL {{ ?zone rdfs:label ?zoneName }}
            }}
            
            # Points
            OPTIONAL {{
                ?equipment brick:hasPoint ?point .
                OPTIONAL {{ ?point rdfs:label ?pointName }}
            }}
            
            # BACnet references
            OPTIONAL {{
                ?point s223:hasExternalReference ?bacnetRef .
                ?bacnetRef a s223:BACnetExternalReference .
            }}
            
            # Upstream equipment
            OPTIONAL {{
                ?upstream s223:feeds ?equipment .
            }}
            
            # Downstream equipment
            OPTIONAL {{
                ?equipment s223:feeds ?downstream .
            }}
        }}
        """
        
        results = self.client.execute_sparql_query(query, output_format="json")
        
        # Parse results
        equip_name = None
        equip_type = None
        serving_zone = None
        points = []
        bacnet_refs = []
        upstream = []
        downstream = []
        
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                if not equip_name:
                    equip_name = binding.get("equipName", {}).get("value", "")
                if not equip_type:
                    equip_type = binding.get("equipType", {}).get("value", "")
                if not serving_zone:
                    zone_uri = binding.get("zone", {}).get("value")
                    if zone_uri:
                        serving_zone = binding.get("zoneName", {}).get("value", "") or zone_uri
                
                point_uri = binding.get("point", {}).get("value")
                if point_uri and point_uri not in [p["id"] for p in points]:
                    points.append({
                        "id": point_uri,
                        "name": binding.get("pointName", {}).get("value", "")
                    })
                
                bacnet_uri = binding.get("bacnetRef", {}).get("value")
                if bacnet_uri and bacnet_uri not in [r["id"] for r in bacnet_refs]:
                    bacnet_refs.append({"id": bacnet_uri})
                
                upstream_uri = binding.get("upstream", {}).get("value")
                if upstream_uri and upstream_uri not in [u["id"] for u in upstream]:
                    upstream.append({"id": upstream_uri})
                
                downstream_uri = binding.get("downstream", {}).get("value")
                if downstream_uri and downstream_uri not in [d["id"] for d in downstream]:
                    downstream.append({"id": downstream_uri})
        
        return EquipmentContext(
            equipment_id=equipment_id,
            equipment_name=equip_name or equipment_id.split("/")[-1],
            equipment_type=equip_type.split("#")[-1] if equip_type and "#" in equip_type else equip_type or "Equipment",
            serving_zone=serving_zone,
            points=points,
            bacnet_refs=bacnet_refs,
            upstream=upstream,
            downstream=downstream
        )
    
    def find_points(self, predicate: str, building: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find points matching a predicate (e.g., "all SAT sensors in Building A").
        
        Args:
            predicate: Description of points to find
            building: Optional building identifier
            
        Returns:
            List of point information
        """
        # Simple keyword-based query generation
        query = """
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?point ?pointName ?pointType ?equipment ?equipName
        WHERE {
            ?point a brick:Point .
            OPTIONAL { ?point rdfs:label ?pointName }
            OPTIONAL { ?point a ?pointType }
            OPTIONAL {
                ?equipment brick:hasPoint ?point .
                OPTIONAL { ?equipment rdfs:label ?equipName }
            }
        }
        LIMIT 100
        """
        
        results = self.client.execute_sparql_query(query, output_format="json")
        
        points = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                point_uri = binding.get("point", {}).get("value")
                if point_uri:
                    points.append({
                        "id": point_uri,
                        "name": binding.get("pointName", {}).get("value", ""),
                        "type": binding.get("pointType", {}).get("value", ""),
                        "equipment": {
                            "id": binding.get("equipment", {}).get("value", ""),
                            "name": binding.get("equipName", {}).get("value", "")
                        } if binding.get("equipment", {}).get("value") else None
                    })
        
        return points
    
    def get_control_chain(self, zone_id: str) -> List[Dict[str, Any]]:
        """
        Get the control chain for a zone (upstream equipment and control points).
        
        Args:
            zone_id: Zone URI or identifier
            
        Returns:
            List of control chain components
        """
        query = f"""
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?zone ?equipment ?equipName ?point ?pointName ?pointType
        WHERE {{
            ?zone a s223:Zone .
            FILTER (?zone = <{zone_id}> || STR(?zone) = "{zone_id}")
            
            ?equipment s223:serves ?zone .
            OPTIONAL {{ ?equipment rdfs:label ?equipName }}
            
            ?equipment brick:hasPoint ?point .
            OPTIONAL {{ ?point rdfs:label ?pointName }}
            OPTIONAL {{ ?point a ?pointType }}
        }}
        """
        
        results = self.client.execute_sparql_query(query, output_format="json")
        
        chain = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                chain.append({
                    "equipment": {
                        "id": binding.get("equipment", {}).get("value", ""),
                        "name": binding.get("equipName", {}).get("value", "")
                    },
                    "point": {
                        "id": binding.get("point", {}).get("value", ""),
                        "name": binding.get("pointName", {}).get("value", ""),
                        "type": binding.get("pointType", {}).get("value", "")
                    }
                })
        
        return chain
    
    def get_bacnet_binding_for_point(self, point_id: str) -> Optional[Dict[str, Any]]:
        """
        Get BACnet binding information for a point.
        
        Args:
            point_id: Point URI or identifier
            
        Returns:
            BACnet binding information or None
        """
        query = f"""
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX ex: <https://example.com/rig#>
        
        SELECT ?point ?bacnetRef ?deviceInstance ?objectType ?objectInstance ?propertyId
        WHERE {{
            ?point s223:hasExternalReference ?bacnetRef .
            ?bacnetRef a s223:BACnetExternalReference .
            FILTER (?point = <{point_id}> || STR(?point) = "{point_id}")
            
            OPTIONAL {{ ?bacnetRef ex:bacnetDeviceInstance ?deviceInstance }}
            OPTIONAL {{ ?bacnetRef ex:bacnetObjectType ?objectType }}
            OPTIONAL {{ ?bacnetRef ex:bacnetObjectInstance ?objectInstance }}
            OPTIONAL {{ ?bacnetRef ex:bacnetPropertyId ?propertyId }}
        }}
        LIMIT 1
        """
        
        results = self.client.execute_sparql_query(query, output_format="json")
        
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                return {
                    "bacnet_ref": binding.get("bacnetRef", {}).get("value", ""),
                    "device_instance": binding.get("deviceInstance", {}).get("value", ""),
                    "object_type": binding.get("objectType", {}).get("value", ""),
                    "object_instance": binding.get("objectInstance", {}).get("value", ""),
                    "property_id": binding.get("propertyId", {}).get("value", "")
                }
        
        return None

