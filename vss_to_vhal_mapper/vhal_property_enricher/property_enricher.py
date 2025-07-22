# Applies rules to generate aospId, aospArea, vhal_type, etc.
import yaml
import re
from typing import Dict, Any, Optional, List, Union

from model.signal import SignalNode
from model.constants import VhalPropertyType, VhalAreaType, VhalAccessMode, VhalChangeMode

class PropertyEnricher:
    """
    Enriches SignalNode objects (parsed from VSS) with Android VHAL-like attributes
    such as aospId, vhal_type, aospArea, access mode, change mode, and unit conversions.

    This class loads configuration from typemap.yml, unit_conversion_rules.yml,
    and property_heuristics.yml to perform the enrichment.
    """

    def __init__(self,
                 typemap_filepath: str,
                 unit_conversion_rules_filepath: str,
                 property_heuristics_filepath: str,
                 parsed_vhal_properties: Dict[str, Dict[str, Any]]):
        """
        Initializes the PropertyEnricher with necessary configuration files
        and a reference to parsed standard VHAL properties.

        Args:
            typemap_filepath (str): Path to the typemap.yml configuration file.
            unit_conversion_rules_filepath (str): Path to the unit_conversion_rules.yml file.
            property_heuristics_filepath (str): Path to the property_heuristics.yml file.
            parsed_vhal_properties (Dict[str, Dict[str, Any]]): Structured data
                representing standard Android VHAL property definitions parsed from
                VehicleProperty.aidl. Used as a reference for conventions.
        """
        self.typemap = self._load_config(typemap_filepath)
        self.unit_conversion_rules = self._load_config(unit_conversion_rules_filepath)
        self.property_heuristics = self._load_config(property_heuristics_filepath)
        self.parsed_vhal_properties = parsed_vhal_properties

        if not self.typemap:
            print(f"Warning: typemap.yml not loaded or empty from {typemap_filepath}")
        if not self.unit_conversion_rules:
            print(f"Warning: unit_conversion_rules.yml not loaded or empty from {unit_conversion_rules_filepath}")
        if not self.property_heuristics:
            print(f"Warning: property_heuristics.yml not loaded or empty from {property_heuristics_filepath}")
        if not self.parsed_vhal_properties:
            print("Warning: No standard VHAL properties provided for reference.")


    def _load_config(self, filepath: str) -> Dict[str, Any]:
        """Helper method to load a YAML configuration file."""
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {filepath}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {filepath}: {e}")
            return {}

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
            # Corrected condition: Enrich if node_type is a data-carrying type in VSS
            if signal_node.node_type in ["signal", "sensor", "actuator", "attribute"]:
                self._enrich_single_signal(signal_node)
                enriched_signals_count += 1
            # Branch nodes are for hierarchy and do not directly become VHAL properties.

        print(f"Finished enriching {enriched_signals_count} VSS signals.")
        return vss_signals # Return the modified dictionary

    def _enrich_single_signal(self, signal_node: SignalNode):
        """
        Applies all enrichment rules to a single SignalNode.
        """
        # 1. aospId Generation
        self._generate_aosp_id(signal_node)

        # 2. vhal_type Mapping
        self._map_vhal_type(signal_node)

        # 3. aospArea Inference
        self._infer_aosp_area(signal_node)

        # 4. Access Mode Determination
        self._infer_access_mode(signal_node)

        # 5. Change Mode Determination
        self._infer_change_mode(signal_node)

        # 6. Unit Conversion and Multipliers
        self._apply_unit_conversion(signal_node)

        # 7. Min/Max Values (simplified for this generic phase)
        self._set_min_max_values(signal_node)

    def _generate_aosp_id(self, signal_node: SignalNode):
        """
        Generates a VHAL-like property ID (aospId) from the VSS signal path.
        Example: "Vehicle.Speed" -> "VehicleProperty::VEHICLE_SPEED"
        """
        # Replace periods with underscores, convert to uppercase, and prefix
        vhal_name = signal_node.path.replace('.', '_').upper()
        signal_node.aospId = f"VehicleProperty::{vhal_name}"

    def _map_vhal_type(self, signal_node: SignalNode):
        """
        Maps the VSS datatype to its corresponding VHAL type using typemap.yml.
        """
        if signal_node.datatype and signal_node.datatype.upper() in self.typemap:
            signal_node.vhal_type = self.typemap[signal_node.datatype.upper()].get("vhal")
        elif signal_node.datatype and signal_node.datatype.endswith("[]"):
            base_vss_type = signal_node.datatype[:-2].upper()
            if base_vss_type in self.typemap and "vhal" in self.typemap[base_vss_type]:
                # VHAL typically uses _VEC for array types (e.g., INT32_VEC)
                signal_node.vhal_type = f"{self.typemap[base_vss_type]['vhal'].upper()}_VEC"
            else:
                print(f"Warning: Base VHAL type mapping for array '{signal_node.datatype}' not found in typemap. Setting vhal_type to None.")
                signal_node.vhal_type = None
        else:
            print(f"Warning: No VHAL type mapping found for VSS datatype '{signal_node.datatype}' for signal '{signal_node.path}'. Setting vhal_type to None.")
            signal_node.vhal_type = None # Explicitly set to None if no mapping

    def _infer_aosp_area(self, signal_node: SignalNode):
        """
        Infers the VHAL area type (aospArea) based on keywords in the VSS signal path.
        Prioritizes specific areas over global.
        """
        path_upper = signal_node.path.upper()
        
        if "DOOR" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.DOOR}"
        elif "WHEEL" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.WHEEL}"
        elif "SEAT" in path_upper or "DRIVER" in path_upper or "OCCUPANT" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.SEAT}"
        elif "MIRROR" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.MIRROR}"
        elif "WINDOW" in path_upper and "WIPER" not in path_upper: # Exclude WiperSystem under Window
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.WINDOW}"
        elif "LIGHT" in path_upper and "LIGHTING" in path_upper: # For Vehicle.Lighting branches and signals
            # Vehicle.Lighting.Brake -> Should be GLOBAL (for lights in general)
            # Vehicle.Lighting.Head -> GLOBAL
            # These are typically global if not tied to specific area instances.
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"
        elif "HVAC" in path_upper: # HVAC can be GLOBAL or SEAT
             if "STATION" in path_upper: # HVAC.Station.Row1.Driver.FanSpeed
                signal_node.aospArea = f"VehicleArea::{VhalAreaType.SEAT}"
             else:
                signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}" # General HVAC properties
        elif "POWERTRAIN" in path_upper or "ENGINE" in path_upper or "FUEL" in path_upper or "BATTERY" in path_upper:
            # Powertrain components are typically GLOBAL
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"
        elif "ADAS" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"
        elif "CHASSIS" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}" # Chassis can be global or specific (wheel, axle)
        elif "OBD" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"
        elif "HMI" in path_upper or "INFOTAINMENT" in path_upper or "MEDIA" in path_upper:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"
        elif "ACCELERATOR" in path_upper or "BRAKE" in path_upper:
             signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}" # Pedals are global

        # Default fallback (should be covered by heuristics but for safety)
        if signal_node.aospArea is None:
            signal_node.aospArea = f"VehicleArea::{VhalAreaType.GLOBAL}"


    def _apply_heuristic_rule(self,
                              target_string: str,
                              rules: List[Dict[str, Any]],
                              result_key: str) -> Optional[str]:
        """
        Helper method to apply a list of heuristic rules against a target string.
        Rules are evaluated by their defined 'priority' (lower is higher priority).
        """
        sorted_rules = sorted(rules, key=lambda x: x.get('priority', 999))

        for rule in sorted_rules:
            patterns = rule.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, target_string, re.IGNORECASE):
                    return rule.get(result_key)
        return None # Return None if no rule matches

    def _infer_access_mode(self, signal_node: SignalNode):
        """
        Infers the VHAL access mode (READ, WRITE, READ_WRITE) using heuristics
        from property_heuristics.yml.
        Prioritizes specific rules over general ones.
        Also uses VSS 'type' (sensor/actuator/attribute) for primary inference.
        """
        inferred_access = None

        # Prioritize VSS 'type' (sensor/actuator/attribute) if available
        if signal_node.node_type == "sensor":
            inferred_access = VhalAccessMode.READ
        elif signal_node.node_type == "actuator":
            # Actuators can be READ_WRITE if their state can also be read, or just WRITE
            # Default actuators to READ_WRITE, but heuristics can refine this
            inferred_access = VhalAccessMode.READ_WRITE
        elif signal_node.node_type == "attribute":
            # Attributes are usually STATIC and READ, but some can be set (WRITE).
            # Default to READ, heuristics can refine.
            inferred_access = VhalAccessMode.READ

        # Apply heuristics from config file for refinement or if node_type is generic 'signal'
        if self.property_heuristics and "access_mode_rules" in self.property_heuristics:
            heuristic_access = self._apply_heuristic_rule(
                signal_node.name, # Use signal name for heuristics
                self.property_heuristics["access_mode_rules"],
                "vhal_access"
            )
            # If heuristic provides a more specific access mode, use it.
            # E.g., an actuator named 'IsActive' might be READ_WRITE by heuristic but ACTUATOR defaults to WRITE.
            # Here, the heuristic is meant to refine.
            if heuristic_access:
                signal_node.access = heuristic_access
            elif inferred_access: # Use type-based inference if no heuristic matched
                signal_node.access = inferred_access
            else: # Fallback if nothing matched (should be caught by default rule in heuristics)
                signal_node.access = VhalAccessMode.READ # Safe default
                print(f"Warning: No access mode inferred for '{signal_node.path}'. Defaulting to READ.")
        else:
            signal_node.access = inferred_access if inferred_access else VhalAccessMode.READ
            print(f"Warning: Property heuristics for access modes not loaded. Defaulting '{signal_node.path}' to {signal_node.access}.")

    def _infer_change_mode(self, signal_node: SignalNode):
        """
        Infers the VHAL change mode (STATIC, ON_CHANGE, CONTINUOUS) using heuristics.
        """
        if self.property_heuristics and "change_mode_rules" in self.property_heuristics:
            inferred_change_mode = self._apply_heuristic_rule(
                signal_node.name, # Use signal name for heuristics
                self.property_heuristics["change_mode_rules"],
                "vhal_change_mode"
            )
            if inferred_change_mode:
                signal_node.change_mode = inferred_change_mode
            else:
                # Fallback if no specific rule matched (should be covered by "Default On-Change" rule)
                signal_node.change_mode = VhalChangeMode.ON_CHANGE
                print(f"Warning: No change mode heuristic matched for '{signal_node.path}'. Defaulting to ON_CHANGE.")
        else:
            signal_node.change_mode = VhalChangeMode.ON_CHANGE # Default if heuristics not loaded
            print(f"Warning: Property heuristics for change modes not loaded. Defaulting '{signal_node.path}' to ON_CHANGE.")


    def _apply_unit_conversion(self, signal_node: SignalNode):
        """
        Applies unit conversion multipliers and offsets to the SignalNode
        based on its VSS unit and the unit_conversion_rules.
        """
        # Only apply unit conversion if unit is specified and datatype is numeric
        # VSS 'attribute' can also have units if they are numeric (e.g. dimensions)
        if signal_node.unit and signal_node.datatype in [
            "float", "double", "int", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64",
            "float[]", "double[]", "int8[]", "uint8[]", "int16[]", "uint16[]", "int32[]", "uint32[]", "int64[]", "uint64[]"
        ]:
            vss_unit_key = signal_node.unit.lower() # Normalize unit key from VSS
            
            if vss_unit_key in self.unit_conversion_rules:
                unit_info = self.unit_conversion_rules[vss_unit_key]
                signal_node.unit_multiplier = unit_info.get("to_base_multiplier")
                signal_node.unit_offset = unit_info.get("to_base_offset")
                if signal_node.unit_multiplier is None or signal_node.unit_offset is None:
                    print(f"Warning: Unit conversion rule for '{signal_node.unit}' is incomplete (missing multiplier/offset) for signal '{signal_node.path}'.")
            else:
                # If unit is specified but no conversion rule, assume 1:1 mapping (no conversion needed)
                signal_node.unit_multiplier = 1.0
                signal_node.unit_offset = 0.0
                print(f"Info: No specific unit conversion rule found for VSS unit '{signal_node.unit}' for signal '{signal_node.path}'. Assuming 1:1 conversion.")
        else:
            # For non-numeric types or if no unit is specified in VSS
            signal_node.unit_multiplier = None
            signal_node.unit_offset = None

    def _set_min_max_values(self, signal_node: SignalNode):
        """
        Sets min_value and max_value on the SignalNode, prioritizing VSS-defined
        values.
        """
        # Prioritize VSS-defined min/max (from vss_min and vss_max attributes parsed by VSSParser)
        if signal_node.vss_min is not None:
            signal_node.min_value = float(signal_node.vss_min)
        if signal_node.vss_max is not None:
            signal_node.max_value = float(signal_node.vss_max)

        # If min/max are still None after VSS attributes, apply VHAL type-based defaults
        # or look up in parsed_vhal_properties if available and relevant.
        
        # Check against VHAL types (INT32, INT64, FLOAT, BOOLEAN) as provided by typemap
        if signal_node.min_value is None:
            if signal_node.vhal_type == VhalPropertyType.BOOLEAN:
                signal_node.min_value = 0.0
            elif signal_node.vhal_type == VhalPropertyType.INT32:
                # Assuming 32-bit signed integer range if no VSS min and not a specific VHAL property with defined range
                # Or leave None if range is usually inferred by platform.
                pass 
            elif signal_node.vhal_type == VhalPropertyType.INT64:
                # Same for 64-bit signed integer
                pass
            elif signal_node.vhal_type == VhalPropertyType.FLOAT:
                # Float ranges are vast, often left as None unless specifically defined
                pass

        if signal_node.max_value is None:
            if signal_node.vhal_type == VhalPropertyType.BOOLEAN:
                signal_node.max_value = 1.0
            elif signal_node.vhal_type == VhalPropertyType.INT32:
                # Assuming 32-bit signed integer max
                pass 
            elif signal_node.vhal_type == VhalPropertyType.INT64:
                # Same for 64-bit signed integer
                pass
            elif signal_node.vhal_type == VhalPropertyType.FLOAT:
                # Float ranges are vast, often left as None unless specifically defined
                pass

        # Optional: Lookup in parsed_vhal_properties if you have min/max explicitly extracted from AIDL
        # canonical_prop_info = self.parsed_vhal_properties.get(signal_node.aospId.split('::')[-1]) if signal_node.aospId else None
        # if canonical_prop_info:
        #     if signal_node.min_value is None and 'min_value_from_aidl' in canonical_prop_info:
        #         signal_node.min_value = float(canonical_prop_info['min_value_from_aidl'])
        #     if signal_node.max_value is None and 'max_value_from_aidl' in canonical_prop_info:
        #         signal_node.max_value = float(canonical_prop_info['max_value_from_aidl'])