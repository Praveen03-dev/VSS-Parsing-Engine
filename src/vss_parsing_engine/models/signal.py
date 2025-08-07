# model/signal.py

"""
This file defines the SignalNode data class, which serves as the central
data structure for representing a single vehicle signal throughout the
VSS to VHAL mapping and enrichment process.

It holds both the original VSS signal information and the enriched
Android VHAL-like properties derived during processing.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union

@dataclass
class SignalNode:
    """
    Represents a single node (either a signal or a branch) from the VSS hierarchy,
    enriched with VHAL-specific attributes.
    """
    name: str  # The local name of the signal/branch (e.g., "Speed", "Engine")
    path: str  # The full hierarchical path of the signal (e.g., "Vehicle.Speed")
    node_type: str  # Type of the node: "signal", "branch", "attribute", "sensor", "actuator"
    datatype: Optional[str] = None  # VSS data type (e.g., "float", "boolean", "string")
    unit: Optional[str] = None  # VSS unit of measurement (e.g., "km/h", "Celsius")
    description: Optional[str] = None  # Description of the signal/branch

    # --- Original VSS Attributes (added for comprehensive parsing) ---
    vss_min: Optional[Union[int, float]] = None 
    vss_max: Optional[Union[int, float]] = None 
    vss_default: Optional[Any] = None 
    vss_allowed_values: Optional[List[Any]] = None 
    vss_pattern: Optional[str] = None 
    vss_deprecation: Optional[str] = None 
    
    # For VSS instances handling (used internally by parser for expansion)
    vss_instances: Optional[List[Union[str, List[str]]]] = None 
    
    # --- Android VHAL-like properties (enriched by vhal_property_enricher) ---
    aospId: Optional[str] = None  # Generated Android VHAL property ID (e.g., "VehicleProperty::VEHICLE_SPEED")
    aospArea: Optional[str] = None  # Inferred Android VHAL area type (e.g., "VehicleArea::GLOBAL", "VehicleArea::SEAT")
    vhal_type: Optional[str] = None  # Mapped Android VHAL property data type (e.g., "FLOAT", "BOOLEAN")
    access: Optional[str] = None  # Inferred VHAL access mode ("READ", "WRITE", "READ_WRITE")
    change_mode: Optional[str] = None  # Inferred VHAL change mode ("STATIC", "ON_CHANGE", "CONTINUOUS")
    unit_multiplier: Optional[float] = None  # Multiplier for converting VSS unit to VHAL base unit
    unit_offset: Optional[float] = None  # Offset for converting VSS unit to VHAL base unit (e.g., for temperature)
    min_value: Optional[float] = None  # Minimum allowed value for the VHAL property (after unit conversion)
    max_value: Optional[float] = None  # Maximum allowed value for the VHAL property (after unit conversion)

    # Children nodes for maintaining the VSS hierarchy internally.
    # This is a dictionary where keys are child names and values are other SignalNode objects.
    children: Dict[str, 'SignalNode'] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the SignalNode object into a dictionary representation,
        omitting entries where the value is None.
        Children are recursively converted, and the 'children' key is omitted
        if there are no actual children.
        """
        node_dict = {}
        
        # Iterate over all fields of the dataclass
        # Using self.__dict__.items() to get all instance attributes
        for field_name, field_value in self.__dict__.items():
            if field_name == "children":
                # Recursively convert children to dictionaries
                processed_children = {}
                # Only iterate if field_value (self.children) is not None and not empty
                if field_value: 
                    for k, v in field_value.items():
                        if isinstance(v, SignalNode): # Ensure it's a SignalNode before calling to_dict
                            processed_children[k] = v.to_dict()
                        else:
                            # Fallback for unexpected types, though ideally all children are SignalNodes
                            processed_children[k] = v 
                
                # Only include the 'children' key if there are actual processed children
                if processed_children:
                    node_dict[field_name] = processed_children
            else:
                # For all other fields, include only if the value is not None
                if field_value is not None:
                    node_dict[field_name] = field_value
        
        return node_dict