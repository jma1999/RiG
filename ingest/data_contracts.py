"""
Data Contracts for Cross-Domain Integration

Defines contracts for each integration source (BACnet, Workday, Maximo, etc.)
following the pattern from Joel Bender's BACSI work at Cornell.

Each contract specifies:
- Scope & IDs: what entities, primary keys, IRI policy
- Freshness & cadence: push vs. pull, expected latency
- Shapes: SHACL for required fields & relations
- Provenance & security: who writes; which PII fields are excluded or hashed
- SLAs: error budgets, fallbacks
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import pathlib


class FreshnessMode(Enum):
    PUSH = "push"
    PULL = "pull"
    HYBRID = "hybrid"


@dataclass
class DataContract:
    """Data contract for a domain integration source"""
    domain: str
    source: str
    scope: Dict[str, Any]
    freshness: Dict[str, Any]
    shapes: List[str]
    provenance: Dict[str, Any]
    slas: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert contract to dictionary for JSON serialization"""
        return {
            "domain": self.domain,
            "source": self.source,
            "scope": self.scope,
            "freshness": self.freshness,
            "shapes": self.shapes,
            "provenance": self.provenance,
            "slas": self.slas
        }


# Predefined contracts for common integrations

CONTROLS_CONTRACT = DataContract(
    domain="controls",
    source="BACnet/IP",
    scope={
        "entities": ["Devices", "Objects (AI/AO/AV/BI/BO/BV)", "Points"],
        "primary_keys": ["Device Instance", "Object Instance"],
        "iri_policy": "https://rig.example.com/controls/{device}/{object}"
    },
    freshness={
        "mode": FreshnessMode.HYBRID.value,
        "push_latency": "< 5 seconds (COV)",
        "pull_latency": "< 60 seconds (polling)",
        "cadence": "continuous"
    },
    shapes=[
        "shacl/controls/bacnet-point.ttl"
    ],
    provenance={
        "writer": "BACnet Gateway Service",
        "pii_fields": [],
        "security": "VLAN-segmented, VPN for remote access"
    },
    slas={
        "uptime": "99.5%",
        "fallback": "Synthetic last-value if feed fails > 5 min"
    }
)

FINANCE_CONTRACT = DataContract(
    domain="finance",
    source="EBS/Kuali",
    scope={
        "entities": ["Meters", "Billing Records", "Cost Centers", "Spaces"],
        "primary_keys": ["Meter ID", "Billing Period", "Cost Center ID"],
        "iri_policy": "https://rig.example.com/finance/{meter}/{period}"
    },
    freshness={
        "mode": FreshnessMode.PULL.value,
        "latency": "< 24 hours",
        "cadence": "daily"
    },
    shapes=[
        "shacl/finance/meter-billing.ttl"
    ],
    provenance={
        "writer": "Finance Integration Service",
        "pii_fields": [],
        "security": "Encrypted at rest, role-based access"
    },
    slas={
        "uptime": "99.0%",
        "fallback": "Last known billing period if feed fails"
    }
)

HR_CONTRACT = DataContract(
    domain="hr",
    source="Workday",
    scope={
        "entities": ["Persons", "Organizations", "Roles", "Responsibilities"],
        "primary_keys": ["Workday Employee ID", "Workday Org ID"],
        "iri_policy": "https://rig.example.com/hr/{workday_id}"
    },
    freshness={
        "mode": FreshnessMode.PULL.value,
        "latency": "< 1 hour",
        "cadence": "hourly"
    },
    shapes=[
        "shacl/hr/org-role.ttl"
    ],
    provenance={
        "writer": "Workday Integration Service",
        "pii_fields": ["email", "phone"],  # Hashed or excluded
        "security": "OAuth2, encrypted at rest"
    },
    slas={
        "uptime": "99.5%",
        "fallback": "Cached org structure if feed fails"
    }
)

WORKORDERS_CONTRACT = DataContract(
    domain="workorders",
    source="Maximo",
    scope={
        "entities": ["Assets", "Work Orders", "PM Schedules", "Spares"],
        "primary_keys": ["Maximo Asset ID", "Maximo WO ID"],
        "iri_policy": "https://rig.example.com/workorders/{maximo_id}"
    },
    freshness={
        "mode": FreshnessMode.HYBRID.value,
        "push_latency": "< 30 seconds (events)",
        "pull_latency": "< 5 minutes (sync)",
        "cadence": "continuous"
    },
    shapes=[
        "shacl/workorders/asset-lifecycle.ttl"
    ],
    provenance={
        "writer": "Maximo Integration Service",
        "pii_fields": [],
        "security": "API key, encrypted at rest"
    },
    slas={
        "uptime": "99.5%",
        "fallback": "Cached asset data if feed fails"
    }
)

SCHEDULING_CONTRACT = DataContract(
    domain="scheduling",
    source="Office365",
    scope={
        "entities": ["Calendars", "Events", "Spaces"],
        "primary_keys": ["Office365 Calendar ID", "Office365 Event ID"],
        "iri_policy": "https://rig.example.com/scheduling/{calendar_id}/{event_id}"
    },
    freshness={
        "mode": FreshnessMode.PUSH.value,
        "latency": "< 1 minute (webhook)",
        "cadence": "real-time"
    },
    shapes=[
        "shacl/scheduling/calendar-space.ttl"
    ],
    provenance={
        "writer": "Office365 Integration Service",
        "pii_fields": ["attendee_email"],  # Hashed
        "security": "OAuth2, encrypted at rest"
    },
    slas={
        "uptime": "99.0%",
        "fallback": "Cached calendar if feed fails"
    }
)

NETWORK_CONTRACT = DataContract(
    domain="net",
    source="Network Engineering",
    scope={
        "entities": ["Devices", "VLANs", "Switches", "Ports"],
        "primary_keys": ["IP Address", "VLAN ID", "Switch/Port"],
        "iri_policy": "https://rig.example.com/net/{vlan}/{device}"
    },
    freshness={
        "mode": FreshnessMode.PULL.value,
        "latency": "< 15 minutes",
        "cadence": "every 15 minutes"
    },
    shapes=[
        "shacl/net/network-topology.ttl"
    ],
    provenance={
        "writer": "Network Topology Service",
        "pii_fields": [],
        "security": "VPN-only access, encrypted at rest"
    },
    slas={
        "uptime": "99.0%",
        "fallback": "Cached topology if feed fails"
    }
)


# Registry of all contracts
CONTRACTS_REGISTRY = {
    "controls": CONTROLS_CONTRACT,
    "finance": FINANCE_CONTRACT,
    "hr": HR_CONTRACT,
    "workorders": WORKORDERS_CONTRACT,
    "scheduling": SCHEDULING_CONTRACT,
    "net": NETWORK_CONTRACT
}


def get_contract(domain: str) -> Optional[DataContract]:
    """Get data contract for a domain"""
    return CONTRACTS_REGISTRY.get(domain)


def list_contracts() -> List[str]:
    """List all available contract domains"""
    return list(CONTRACTS_REGISTRY.keys())


def validate_contract_compliance(domain: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that data conforms to the contract for a domain.
    
    Args:
        domain: Domain name (e.g., "controls", "finance")
        data: Data to validate
    
    Returns:
        Validation results with compliance status
    """
    contract = get_contract(domain)
    if not contract:
        return {
            "valid": False,
            "error": f"No contract found for domain: {domain}"
        }
    
    # Basic validation - check required scope fields
    required_fields = contract.scope.get("primary_keys", [])
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return {
            "valid": False,
            "missing_fields": missing_fields,
            "contract": contract.to_dict()
        }
    
    return {
        "valid": True,
        "contract": contract.to_dict()
    }


