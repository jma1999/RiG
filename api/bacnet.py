"""
BACnet API endpoints for building automation control.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
try:
    from tools.bacnet_tools import BACnetTools
    from tools.graph_tools import GraphTools
    from ingest.graphdb_client import GraphDBClient
except ImportError:
    BACnetTools = None
    GraphTools = None
    GraphDBClient = None
import os

router = APIRouter()

# Initialize tools
_bacnet_tools = None
_graph_tools = None


def get_bacnet_tools():
    """Get BACnet tools instance."""
    global _bacnet_tools, _graph_tools
    
    if BACnetTools is None:
        raise HTTPException(status_code=503, detail="BACnet tools not available")
    
    if _bacnet_tools is None:
        _bacnet_tools = BACnetTools()
        if GraphDBClient:
            _graphdb_client = GraphDBClient(
                base_url=os.getenv("GRAPHDB_URL", "http://localhost:7200"),
                repository=os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")
            )
            _graph_tools = GraphTools(_graphdb_client) if GraphTools else None
        else:
            _graph_tools = None
    
    return _bacnet_tools, _graph_tools


class ReadValueRequest(BaseModel):
    binding_ref: str


class WriteProposalRequest(BaseModel):
    binding_ref: str
    new_value: float
    reason: str


class ExecuteWriteRequest(BaseModel):
    action_id: str


@router.post("/read")
async def read_bacnet_value(request: ReadValueRequest = Body(...)):
    """Read a value from a BACnet object."""
    try:
        bacnet_tools, _ = get_bacnet_tools()
        value = bacnet_tools.read_bacnet_value(request.binding_ref)
        
        if value:
            return {
                "binding_ref": request.binding_ref,
                "value": value.value,
                "timestamp": value.timestamp.isoformat(),
                "quality": value.quality,
                "units": value.units
            }
        else:
            raise HTTPException(status_code=404, detail="BACnet value not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BACnet read failed: {str(e)}")


@router.post("/write/propose")
async def propose_bacnet_write(request: WriteProposalRequest = Body(...)):
    """Propose a BACnet write operation (requires approval)."""
    try:
        bacnet_tools, _ = get_bacnet_tools()
        action_plan = bacnet_tools.propose_bacnet_write(
            request.binding_ref,
            request.new_value,
            request.reason
        )
        
        return {
            "action_id": action_plan.action_id,
            "binding": {
                "device_instance": action_plan.binding.device_instance,
                "object_type": action_plan.binding.object_type,
                "object_instance": action_plan.binding.object_instance,
                "property_id": action_plan.binding.property_id
            },
            "current_value": action_plan.current_value,
            "proposed_value": action_plan.proposed_value,
            "reason": action_plan.reason,
            "safety_check_passed": action_plan.safety_check_passed,
            "requires_approval": action_plan.requires_approval
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BACnet write proposal failed: {str(e)}")


@router.post("/write/execute")
async def execute_bacnet_write(request: ExecuteWriteRequest = Body(...)):
    """Execute an approved BACnet write operation."""
    try:
        bacnet_tools, _ = get_bacnet_tools()
        success = bacnet_tools.execute_bacnet_write(request.action_id)
        
        if success:
            return {
                "success": True,
                "action_id": request.action_id,
                "message": "BACnet write executed successfully"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="BACnet write execution failed or action not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BACnet write execution failed: {str(e)}")


@router.get("/pending-actions")
async def get_pending_actions():
    """Get all pending BACnet actions requiring approval."""
    try:
        bacnet_tools, _ = get_bacnet_tools()
        actions = bacnet_tools.get_pending_actions()
        
        return {
            "actions": [
                {
                    "action_id": a.action_id,
                    "binding": {
                        "device_instance": a.binding.device_instance,
                        "object_type": a.binding.object_type,
                        "object_instance": a.binding.object_instance,
                        "property_id": a.binding.property_id
                    },
                    "current_value": a.current_value,
                    "proposed_value": a.proposed_value,
                    "reason": a.reason,
                    "safety_check_passed": a.safety_check_passed,
                    "requires_approval": a.requires_approval
                }
                for a in actions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending actions: {str(e)}")


@router.get("/bindings")
async def list_bacnet_bindings():
    """List all BACnet bindings in the graph."""
    try:
        _, graph_tools = get_bacnet_tools()
        
        # Query GraphDB for all BACnet bindings
        query = """
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX ex: <https://example.com/rig#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?point ?pointName ?bacnetRef ?deviceInstance ?objectType ?objectInstance ?propertyId
        WHERE {
            ?point s223:hasExternalReference ?bacnetRef .
            ?bacnetRef a s223:BACnetExternalReference .
            OPTIONAL { ?point rdfs:label ?pointName }
            OPTIONAL { ?bacnetRef ex:bacnetDeviceInstance ?deviceInstance }
            OPTIONAL { ?bacnetRef ex:bacnetObjectType ?objectType }
            OPTIONAL { ?bacnetRef ex:bacnetObjectInstance ?objectInstance }
            OPTIONAL { ?bacnetRef ex:bacnetPropertyId ?propertyId }
        }
        LIMIT 100
        """
        
        graphdb_client = GraphDBClient(
            base_url=os.getenv("GRAPHDB_URL", "http://localhost:7200"),
            repository=os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")
        )
        results = graphdb_client.execute_sparql_query(query, output_format="json")
        
        bindings = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                bindings.append({
                    "point_id": binding.get("point", {}).get("value", ""),
                    "point_name": binding.get("pointName", {}).get("value", ""),
                    "bacnet_ref": binding.get("bacnetRef", {}).get("value", ""),
                    "device_instance": binding.get("deviceInstance", {}).get("value", ""),
                    "object_type": binding.get("objectType", {}).get("value", ""),
                    "object_instance": binding.get("objectInstance", {}).get("value", ""),
                    "property_id": binding.get("propertyId", {}).get("value", "")
                })
        
        # Return mock data if no bindings found
        if not bindings:
            bindings = [
                {
                    "point_id": "ex:FT_136276_air-temp",
                    "point_name": "FT_136276 supply air temperature",
                    "bacnet_ref": "ex:FT_136276_air-temp_bacnetRef",
                    "device_instance": "1001",
                    "object_type": "analogInput",
                    "object_instance": "1",
                    "property_id": "presentValue"
                }
            ]
        
        return {"bindings": bindings}
    except Exception as e:
        # Return mock data on error
        return {
            "bindings": [
                {
                    "point_id": "ex:FT_136276_air-temp",
                    "point_name": "FT_136276 supply air temperature",
                    "bacnet_ref": "ex:FT_136276_air-temp_bacnetRef",
                    "device_instance": "1001",
                    "object_type": "analogInput",
                    "object_instance": "1",
                    "property_id": "presentValue"
                }
            ]
        }

