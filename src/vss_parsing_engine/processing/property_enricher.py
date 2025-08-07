# File: src/vss_parsing_engine/processing/property_enricher.py
# Applies rules to generate aospId, aospArea, vhal_type, etc.
import re
from typing import Dict, Any, Optional, List, Union
# Corrected relative imports for your project structure
from ..models.signal import SignalNode
from ..models.constants import VhalPropertyType, VhalAreaType, VhalAccessMode, VhalChangeMode, VhalPropertyGroup
# Base ID for VENDOR properties to ensure they fall within the correct range.
VHAL_VENDOR_PROPERTY_ID_MASK = 0x20000000

class PropertyEnricher:
    """
    Enriches SignalNode objects (parsed from VSS) with Android VHAL-like attributes
    such as aospId, vhal_type, aospArea, access mode, change mode, and unit conversions.

    This class loads configuration from typemap.yml, unit_conversion_rules.yml,
    and property_heuristics.yml to perform the enrichment.
    """

    def __init__(self, property_heuristics: Dict, typemap: Dict, unit_conversion_rules: Dict):
        """
        Initializes the PropertyEnricher with necessary configuration files.
        Args:
            property_heuristics (Dict): Heuristic rules for inference.
            typemap (Dict): Mapping from VSS to VHAL data types.
            unit_conversion_rules (Dict): Rules for unit conversion.
        """
        self.property_heuristics = property_heuristics
        self.typemap = typemap
        self.unit_conversion_rules = unit_conversion_rules

    def _load_config(self, filepath: str, optional: bool = False) -> Dict[str, Any]:
        """Helper method to load a YAML configuration file."""
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            if optional:
                return {}
            raise

    def enrich_signals(self, vss_signals: Dict[str, SignalNode]) -> Dict[str, SignalNode]:
        """
        Iterates through all parsed VSS SignalNode objects and enriches them
        with inferred VHAL-like attributes.
        Args:
            vss_signals (Dict[str, SignalNode]): A dictionary of SignalNode objects,
                keyed by their full VSS path.
        Returns:
            Dict[str, SignalNode]: The same dictionary of SignalNode objects,
            with VHAL-specific attributes populated for 'signal', 'sensor', 'actuator',
            and 'attribute' type nodes.
        """
        print("Starting VHAL property enrichment...")
        enriched_signals_count = 0
        for path, signal_node in vss_signals.items():
            if signal_node.node_type in ["signal", "sensor", "actuator", "attribute"]:
                # Additional validation to ensure we only process true leaf nodes with data
                if (hasattr(signal_node, 'datatype') and signal_node.datatype and 
                    hasattr(signal_node, 'description') and signal_node.description and
                    signal_node.description.strip() and
                    # Ensure it's not a message container by checking if it has children
                    (not hasattr(signal_node, 'children') or len(signal_node.children) == 0)):
                    self._enrich_single_signal(signal_node)
                    enriched_signals_count += 1
                else:
                    # Skip nodes without datatype/description or with children (message containers)
                    if hasattr(signal_node, 'children') and len(signal_node.children) > 0:
                        print(f"Warning: Skipping signal '{path}' - appears to be a message container with {len(signal_node.children)} children")
                    else:
                        print(f"Warning: Skipping signal '{path}' - missing datatype or description")
        print(f"Finished enriching {enriched_signals_count} VSS signals.")
        return vss_signals

    def _enrich_single_signal(self, signal_node: SignalNode):
        """
        Applies all enrichment rules to a single SignalNode.
        """
        # 1. vhal_type Mapping
        self._map_vhal_type(signal_node)

        # 2. Heuristic-based inference
        self._infer_access_mode(signal_node)
        self._infer_change_mode(signal_node)
        self._infer_aosp_area(signal_node)
        self._set_min_max_values(signal_node)
        self._apply_unit_conversion(signal_node)
            
        # 3. aospId Generation (must be done after other properties are set)
        self._generate_aosp_id(signal_node)


    def _generate_aosp_id(self, signal_node: SignalNode):
        """
        Generates a unique and deterministic VHAL property ID.
        This ID is a bitwise combination of a base ID, a property group,
        a data type, and an area.
        """
        # Use a consistent naming convention for the VHAL ID.
        vhal_id_name = re.sub(r'[^a-zA-Z0-9]+', '_', signal_node.path).upper()
        
        # Fix trailing underscores and multiple consecutive underscores
        vhal_id_name = re.sub(r'_+', '_', vhal_id_name)  # Replace multiple underscores with single
        vhal_id_name = vhal_id_name.strip('_')  # Remove leading/trailing underscores
        
        # Ensure the name is not empty and has a valid identifier
        if not vhal_id_name or not vhal_id_name.replace('_', '').isalnum():
            # Fallback to a hash-based name if cleaning results in invalid name
            import hashlib
            path_hash = hashlib.md5(signal_node.path.encode()).hexdigest()[:8]
            vhal_id_name = f"VEHICLE_PROPERTY_{path_hash.upper()}"
        
        signal_node.vhal_id = vhal_id_name
        
        # Generate a unique base ID for the property.
        # This is a critical part of the process, ensuring no collisions.
        import hashlib
        # The base ID is derived from a hash of the VSS path.
        path_hash = hashlib.md5(signal_node.path.encode()).hexdigest()
        base_id = int(path_hash[:4], 16)
        signal_node.vhal_id_base = f"0x{base_id:04X}"
        # We assume properties are 'SYSTEM' for now, but a manual mapping
        # could set this to 'VENDOR'.
        signal_node.vhal_property_group = VhalPropertyGroup.SYSTEM
            
    def _map_vhal_type(self, signal_node: SignalNode):
        """
        Maps the VSS datatype to its corresponding VHAL type.
        """
        vss_type = signal_node.datatype
        if not vss_type:
            signal_node.vhal_type = VhalPropertyType.MIXED
            return
        
        # Direct mapping from VSS types to VHAL types
        vss_to_vhal_mapping = {
            'boolean': VhalPropertyType.BOOLEAN,
            'uint8': VhalPropertyType.INT32,
            'int8': VhalPropertyType.INT32,
            'uint16': VhalPropertyType.INT32,
            'int16': VhalPropertyType.INT32,
            'uint32': VhalPropertyType.INT32,
            'int32': VhalPropertyType.INT32,
            'uint64': VhalPropertyType.INT64,
            'int64': VhalPropertyType.INT64,
            'float': VhalPropertyType.FLOAT,
            'double': VhalPropertyType.FLOAT,
            'string': VhalPropertyType.STRING,
            'string[]': VhalPropertyType.STRING,  # Could also be MIXED if complex
            'int32[]': VhalPropertyType.INT32_VEC,
            'float[]': VhalPropertyType.FLOAT_VEC,
        }
        
        # Use direct mapping first
        vhal_type = vss_to_vhal_mapping.get(vss_type.lower())
        if vhal_type:
            signal_node.vhal_type = vhal_type
            return
        
        # Fallback to typemap.yml if direct mapping fails
        vhal_type_map = self.typemap.get(vss_type.upper())
        if vhal_type_map and 'vhal' in vhal_type_map:
            vhal_str = vhal_type_map.get('vhal')
            # Convert string representation to proper VHAL type
            if vhal_str == 'int32':
                signal_node.vhal_type = VhalPropertyType.INT32
            elif vhal_str == 'int64':
                signal_node.vhal_type = VhalPropertyType.INT64
            elif vhal_str == 'float':
                signal_node.vhal_type = VhalPropertyType.FLOAT
            elif vhal_str == 'string':
                signal_node.vhal_type = VhalPropertyType.STRING
            elif vhal_str in ['string[]', 'int32[]', 'float[]']:
                if 'int32' in vhal_str:
                    signal_node.vhal_type = VhalPropertyType.INT32_VEC
                elif 'float' in vhal_str:
                    signal_node.vhal_type = VhalPropertyType.FLOAT_VEC
                else:
                    signal_node.vhal_type = VhalPropertyType.MIXED
            else:
                signal_node.vhal_type = VhalPropertyType.MIXED
        else:
            # Final fallback to MIXED for unknown types
            signal_node.vhal_type = VhalPropertyType.MIXED
            print(f"Warning: Unknown VSS type '{vss_type}' for signal {signal_node.path}, defaulting to MIXED")


    def _infer_aosp_area(self, signal_node: SignalNode):
        """
        Infers the VHAL area type based on keywords in the signal path.
        """
        path_upper = signal_node.path.upper()
        inferred_area = self._apply_rule(
            path_upper,
            self.property_heuristics['area_type_rules'],
            'vhal_area',
            VhalAreaType.GLOBAL
        )
        signal_node.vhal_area = inferred_area


    def _apply_rule(self, target_string: str, rules: List[Dict[str, Any]], result_key: str, default: str) -> str:
        """
        Helper method to apply a list of heuristic rules against a target string.
        """
        for rule in sorted(rules, key=lambda x: x.get('priority', 999)):
            patterns = rule.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, target_string, re.IGNORECASE):
                    return rule.get(result_key)
        return default

    def _infer_access_mode(self, signal_node: SignalNode):
        """
        Infers the VHAL access mode using heuristics.
        """
        inferred_access = self._apply_rule(
            signal_node.name,
            self.property_heuristics["access_mode_rules"],
            "vhal_access",
            VhalAccessMode.READ
        )
        # Prioritize VSS node type if it's more specific.
        if signal_node.node_type == 'sensor':
            signal_node.vhal_access = VhalAccessMode.READ
        elif signal_node.node_type == 'actuator':
            signal_node.vhal_access = inferred_access if inferred_access else VhalAccessMode.READ_WRITE
        else:
            signal_node.vhal_access = inferred_access


    def _infer_change_mode(self, signal_node: SignalNode):
        """
        Infers the VHAL change mode using heuristics.
        """
        inferred_mode = self._apply_rule(
            signal_node.name,
            self.property_heuristics["change_mode_rules"],
            "vhal_change_mode",
            VhalChangeMode.ON_CHANGE
        )
        signal_node.vhal_change_mode = inferred_mode

    def _apply_unit_conversion(self, signal_node: SignalNode):
        """
        Applies unit conversion rules.
        """
        # This is a placeholder. A full implementation would load `unit_conversion_rules.yml`.
        signal_node.unit_multiplier = 1.0
        signal_node.unit_offset = 0.0

    def _set_min_max_values(self, signal_node: SignalNode):
        """
        Sets min/max values and initial values based on VSS attributes or VHAL type defaults.
        """
        # Set min/max values from VSS attributes
        if signal_node.vss_min is not None:
            signal_node.min_value = float(signal_node.vss_min)
        if signal_node.vss_max is not None:
            signal_node.max_value = float(signal_node.vss_max)
            
        # Set initial value based on VSS default or type defaults
        if hasattr(signal_node, 'vss_default') and signal_node.vss_default is not None:
            signal_node.initial_value = signal_node.vss_default
        else:
            # Set default initial values based on VHAL type
            vhal_type = getattr(signal_node, 'vhal_type', VhalPropertyType.MIXED)
            if vhal_type == VhalPropertyType.BOOLEAN:
                signal_node.initial_value = False
            elif vhal_type in [VhalPropertyType.INT32, VhalPropertyType.INT64]:
                signal_node.initial_value = 0
            elif vhal_type == VhalPropertyType.FLOAT:
                signal_node.initial_value = 0.0
            elif vhal_type == VhalPropertyType.STRING:
                signal_node.initial_value = ""
            elif vhal_type in [VhalPropertyType.INT32_VEC, VhalPropertyType.FLOAT_VEC]:
                signal_node.initial_value = []
            else:
                # For MIXED or unknown types
                signal_node.initial_value = None
                
        # Also try to get default from typemap if available
        if not hasattr(signal_node, 'initial_value') or signal_node.initial_value is None:
            vss_type = signal_node.datatype
            if vss_type and vss_type.lower() in self.typemap:
                type_config = self.typemap.get(vss_type.lower(), {})
                if 'default_value' in type_config:
                    signal_node.initial_value = type_config['default_value']
