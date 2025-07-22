# Data classes for SignalNode and VHAL-enriched properties
# model/signal.py

"""
This file defines the SignalNode data class, which serves as the central
data structure for representing a single vehicle signal throughout the
VSS to VHAL mapping and enrichment process.

It holds both the original VSS signal information and the enriched
Android VHAL-like properties derived during processing.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class SignalNode:
    """
    Represents a single node (either a signal or a branch) from the VSS hierarchy,
    enriched with VHAL-specific attributes.
    """
    name: str  # The local name of the signal/branch (e.g., "Speed", "Engine")
    path: str  # The full hierarchical path of the signal (e.g., "Vehicle.Speed")
    node_type: str  # Type of the node: "signal" or "branch"
    datatype: Optional[str] = None  # VSS data type (e.g., "float", "boolean", "string")
    unit: Optional[str] = None  # VSS unit of measurement (e.g., "km/h", "Celsius")
    description: Optional[str] = None  # Description of the signal/branch

    # --- Android VHAL-like properties (enriched by vhal_property_enricher) ---
    aospId: Optional[str] = None  # Generated Android VHAL property ID (e.g., "VehicleProperty::VEHICLE_SPEED")
    aospArea: Optional[str] = None  # Inferred Android VHAL area type (e.g., "VehicleArea::GLOBAL", "VehicleArea::SEAT")
    vhal_type: Optional[str] = None  # Mapped Android VHAL property data type (e.g., "FLOAT", "BOOLEAN")
    access: Optional[str] = None  # Inferred VHAL access mode ("READ", "WRITE", "READ_WRITE")
    change_mode: Optional[str] = None  # Inferred VHAL change mode ("STATIC", "ON_CHANGE", "CONTINUOUS")
    unit_multiplier: Optional[float] = None  # Multiplier for converting VSS unit to VHAL base unit
    unit_offset: Optional[float] = None  # Offset for converting VSS unit to VHAL base unit (e.g., for temperature)
    min_value: Optional[float] = None  # Minimum allowed value for the VHAL property
    max_value: Optional[float] = None  # Maximum allowed value for the VHAL property

    # Children nodes for maintaining the VSS hierarchy internally.
    # This is a dictionary where keys are child names and values are other SignalNode objects.
    children: Dict[str, 'SignalNode'] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the SignalNode object and its children into a dictionary representation.
        This method is used to prepare the data for JSON serialization.
        """
        # Create a dictionary for the current node's properties
        node_dict = {
            "name": self.name,
            "path": self.path,
            "type": self.node_type,
            "datatype": self.datatype,
            "unit": self.unit,
            "description": self.description,
            "aospId": self.aospId,
            "aospArea": self.aospArea,
            "vhal_type": self.vhal_type,
            "access": self.access,
            "change_mode": self.change_mode,
            "unit_multiplier": self.unit_multiplier,
            "unit_offset": self.unit_offset,
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

        # Recursively convert children to dictionaries
        node_dict["children"] = {
            k: v.to_dict() for k, v in self.children.items()
        }

        return node_dict