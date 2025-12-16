"""
BACnet Tools - Building automation control abstractions for agents.

These tools provide secure, gated access to BACnet systems.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class BACnetBinding:
    """BACnet object binding information."""
    device_instance: int
    object_type: str
    object_instance: int
    property_id: str


@dataclass
class BACnetValue:
    """BACnet value read result."""
    value: float
    timestamp: datetime
    quality: str
    units: Optional[str] = None


@dataclass
class ActionPlan:
    """Proposed BACnet write action plan."""
    action_id: str
    binding: BACnetBinding
    current_value: float
    proposed_value: float
    reason: str
    safety_check_passed: bool
    requires_approval: bool


class BACnetTools:
    """
    Well-typed BACnet control tools for agents.
    
    All control operations are gated and require approval.
    """
    
    def __init__(self):
        # In production, this would connect to a BACnet gateway
        # For now, we simulate BACnet operations
        self._pending_actions: Dict[str, ActionPlan] = {}
    
    def read_bacnet_value(self, binding_ref: str) -> Optional[BACnetValue]:
        """
        Read a value from a BACnet object.
        
        Args:
            binding_ref: BACnet binding reference URI from GraphDB
            
        Returns:
            BACnet value or None if unavailable
        """
        # In production, this would:
        # 1. Look up binding_ref in GraphDB to get BACnet address
        # 2. Connect to BACnet gateway
        # 3. Read presentValue property
        # 4. Return value with timestamp
        
        # Mock implementation
        import random
        return BACnetValue(
            value=round(20.0 + random.uniform(-1, 1), 2),
            timestamp=datetime.now(),
            quality="good",
            units="DEG_C"
        )
    
    def propose_bacnet_write(
        self,
        binding_ref: str,
        new_value: float,
        reason: str
    ) -> ActionPlan:
        """
        Propose a BACnet write operation (requires approval).
        
        Args:
            binding_ref: BACnet binding reference URI
            new_value: Proposed new value
            reason: Reason for the change
            
        Returns:
            Action plan requiring approval
        """
        # Read current value
        current = self.read_bacnet_value(binding_ref)
        current_value = current.value if current else 0.0
        
        # Perform safety check
        safety_passed = self._safety_check(binding_ref, current_value, new_value)
        
        action_id = str(uuid.uuid4())
        
        # Parse binding from GraphDB (mock for now)
        binding = BACnetBinding(
            device_instance=1001,
            object_type="analogOutput",
            object_instance=1,
            property_id="presentValue"
        )
        
        action_plan = ActionPlan(
            action_id=action_id,
            binding=binding,
            current_value=current_value,
            proposed_value=new_value,
            reason=reason,
            safety_check_passed=safety_passed,
            requires_approval=True
        )
        
        self._pending_actions[action_id] = action_plan
        return action_plan
    
    def execute_bacnet_write(self, action_id: str) -> bool:
        """
        Execute an approved BACnet write operation.
        
        Args:
            action_id: Action plan ID
            
        Returns:
            True if successful
        """
        if action_id not in self._pending_actions:
            return False
        
        action = self._pending_actions[action_id]
        
        if not action.safety_check_passed:
            return False
        
        # In production, this would:
        # 1. Validate action is approved
        # 2. Connect to BACnet gateway
        # 3. Write presentValue property
        # 4. Verify write succeeded
        # 5. Log operation
        
        # Mock implementation
        del self._pending_actions[action_id]
        return True
    
    def _safety_check(
        self,
        binding_ref: str,
        current_value: float,
        new_value: float
    ) -> bool:
        """
        Perform safety check on proposed write.
        
        Args:
            binding_ref: BACnet binding reference
            current_value: Current value
            new_value: Proposed new value
            
        Returns:
            True if safe to write
        """
        # Basic safety checks
        # In production, this would query SHACL shapes for allowed ranges
        
        # Example: temperature setpoints should be in reasonable range
        if "temp" in binding_ref.lower() or "temperature" in binding_ref.lower():
            if new_value < 10.0 or new_value > 35.0:
                return False
        
        # Example: flow setpoints should be non-negative
        if "flow" in binding_ref.lower():
            if new_value < 0:
                return False
        
        # Example: percentage values should be 0-100
        if "percent" in binding_ref.lower() or "damper" in binding_ref.lower():
            if new_value < 0 or new_value > 100:
                return False
        
        return True
    
    def get_pending_actions(self) -> List[ActionPlan]:
        """Get all pending action plans requiring approval."""
        return list(self._pending_actions.values())


