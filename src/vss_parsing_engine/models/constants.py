# Constants for types, areas, modes
# model/constants.py

"""
This file defines constants and enum-like structures for VSS and Android VHAL
property types, areas, access modes, and change modes.

These constants are used throughout the vss_to_vhal_mapper project to ensure
consistency and provide clear, readable references to VSS and VHAL specifications.
"""

# --- VSS Data Types ---
# A set of all supported VSS data types for quick membership checks.
VSS_DATA_TYPES = {
    "boolean", "uint8", "int8", "uint16", "int16", "uint32", "int32",
    "uint64", "int64", "float", "double", "string", "string[]",
    # Add other VSS types if your vss_parser supports them, e.g.,
    # "int8[]", "float[]", "uint8[]", etc.
}

# Enum-like class for VSS Data Types for explicit referencing.
class VssDataType:
    """Represents standard VSS data types."""
    BOOLEAN = "boolean"
    UINT8 = "uint8"
    INT8 = "int8"
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    UINT64 = "uint64"
    INT64 = "int64"
    FLOAT = "float"
    DOUBLE = "double"
    STRING = "string"
    STRING_ARRAY = "string[]"
    # Add other array types if needed for VSS
    INT32_ARRAY = "int32[]"
    FLOAT_ARRAY = "float[]"
    # ... and so on for other VSS array types


# --- Android VHAL Property Types (VehiclePropertyType) ---
# These correspond to the values defined in VehicleProperty.aidl (or VehicleProperty.txt)
# and are used in the bitwise construction of property IDs.
# The string values here are what would be used in the 'vhal_type' field of SignalNode.
class VhalPropertyType:
    """Represents Android VHAL VehiclePropertyType enums."""
    INVALID = "INVALID"
    STRING = "STRING" # 0x00100000
    BOOLEAN = "BOOLEAN" # 0x00200000
    INT32 = "INT32" # 0x00400000
    INT32_VEC = "INT32_VEC" # 0x00410000
    INT64 = "INT64" # 0x00500000
    INT64_VEC = "INT64_VEC" # 0x00510000
    FLOAT = "FLOAT" # 0x00600000
    FLOAT_VEC = "FLOAT_VEC" # 0x00610000
    BYTES = "BYTES" # 0x00700000
    MIXED = "MIXED" # 0x00e00000

# A set of all supported VHAL property types for quick membership checks.
VHAL_PROPERTY_TYPES = {
    VhalPropertyType.STRING, VhalPropertyType.BOOLEAN, VhalPropertyType.INT32,
    VhalPropertyType.INT32_VEC, VhalPropertyType.INT64, VhalPropertyType.INT64_VEC,
    VhalPropertyType.FLOAT, VhalPropertyType.FLOAT_VEC, VhalPropertyType.BYTES,
    VhalPropertyType.MIXED
}


# --- Android VHAL Area Types (VehicleArea) ---
# These correspond to the values defined in VehicleArea.aidl
# The string values here are what would be used in the 'aospArea' field of SignalNode.
class VhalAreaType:
    """Represents Android VHAL VehicleArea enums."""
    GLOBAL = "GLOBAL" # 0x01000000
    WINDOW = "WINDOW" # 0x03000000
    MIRROR = "MIRROR" # 0x04000000
    SEAT = "SEAT" # 0x05000000
    DOOR = "DOOR" # 0x06000000
    WHEEL = "WHEEL" # 0x07000000
    # Add other specific area types if needed, e.g.,
    # HEADLIGHT = "HEADLIGHT"
    # VENDOR = "VENDOR" # Used for vendor-specific area IDs, if applicable

# A set of all supported VHAL area types for quick membership checks.
VHAL_AREA_TYPES = {
    VhalAreaType.GLOBAL, VhalAreaType.WINDOW, VhalAreaType.MIRROR,
    VhalAreaType.SEAT, VhalAreaType.DOOR, VhalAreaType.WHEEL
}


# --- Android VHAL Property Groups (VehiclePropertyGroup) ---
# Used in the bitwise construction of property IDs.
class VhalPropertyGroup:
    """Represents Android VHAL VehiclePropertyGroup enums."""
    SYSTEM = "SYSTEM" # 0x10000000
    VENDOR = "VENDOR" # 0x20000000


# --- Android VHAL Access Modes (VehiclePropertyAccess) ---
# These define how a property can be interacted with.
class VhalAccessMode:
    """Represents Android VHAL VehiclePropertyAccess enums."""
    NONE = "NONE" # Not explicitly defined, but useful as a default/unknown
    READ = "READ"
    WRITE = "WRITE"
    READ_WRITE = "READ_WRITE"


# --- Android VHAL Change Modes (VehiclePropertyChangeMode) ---
# These define how frequently a property's value changes.
class VhalChangeMode:
    """Represents Android VHAL VehiclePropertyChangeMode enums."""
    INVALID = "INVALID"
    STATIC = "STATIC" # Value never changes after boot
    ON_CHANGE = "ON_CHANGE" # Value changes only when it actually differs
    CONTINUOUS = "CONTINUOUS" # Value changes continuously and is reported at a sample rate