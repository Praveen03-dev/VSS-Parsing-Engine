# vss_to_vhal_mapper/signal_parser/vss_parser.py

import yaml
import re
import os
import json
from typing import Dict, Optional, Any, List, Union, Tuple, Iterator, Set
from vss_parsing_engine.models.signal import SignalNode

class VSSParser:
    """
    Parses Vehicle Signal Specification (.vspec) files, including handling
    of hierarchical structures, '#include' directives, and 'instances' expansion.
    Builds a complete hierarchy of SignalNode objects and provides a flattened view.
    """

    def __init__(self, file_resolver: Dict[str, str] = None, mapping_file_path: str = None):
        """
        Initializes the VSSParser.
        Args:
            file_resolver: A dictionary mapping VSS include paths (as found in
                           #include directives, e.g., "Vehicle/Vehicle.vspec")
                           to their actual file content strings.
            mapping_file_path: Optional path to vendor mapping file for custom AOSP ID mapping
        """
        self.file_resolver = file_resolver if file_resolver is not None else {}
        self._parsed_file_stack: List[str] = []  # To detect and prevent circular includes
        self._all_nodes_in_hierarchy: Dict[str, SignalNode] = {} # Stores all nodes by their full path
        self.mapping_file_path = mapping_file_path
        self.vendor_mapping: Dict[str, Any] = self._load_mapping_file() if mapping_file_path else {}
        self._aosp_id_counter = 0x0100  # Starting AOSP ID for custom properties

    def _load_mapping_file(self) -> Dict[str, Any]:
        """
        Loads the vendor mapping file if provided, to customize AOSP ID mapping.
        """
        if not self.mapping_file_path or not os.path.exists(self.mapping_file_path):
            print("No valid mapping file path provided or file does not exist.")
            return {}

        try:
            with open(self.mapping_file_path, 'r', encoding='utf-8') as file:
                vendor_mapping = json.load(file)
            print("Vendor mapping file loaded successfully.")
            return vendor_mapping
        except Exception as e:
            print(f"Error loading mapping file: {e}")
            return {}

    def _generate_aosp_id(self, signal_path: str) -> int:
        """
        Generates a unique AOSP ID for a given signal.
        Uses vendor mapping if available, otherwise assigns a new ID.
        """
        if signal_path in self.vendor_mapping:
            return self.vendor_mapping[signal_path].get('aosp_id', self._aosp_id_counter)
        else:
            self._aosp_id_counter += 1
            return self._aosp_id_counter

    def _generate_instance_paths(self, base_name: str, instances_def: List[Union[str, List[str]]]) -> Iterator[Tuple[str, str]]:
        """
        Generates all possible full paths and names by expanding 'instances' definitions.
        Instances can be like:
        - "Left", "Right" (simple list of names)
        - "Row[1,2]" (range-based names)
        - [["Row[1,2]", ["Left", "Right"]]] (nested lists for multiple instance types)
        Yields tuples of (instance_name_segment, instance_path_segment).
        """

        current_combinations = [([], [])]

        for instance_item in instances_def:
            next_combinations = []
            if isinstance(instance_item, str): # Simple name or range like "Row[1,2]"
                range_match = re.match(r'^(\w+)\[(\d+),(\d+)\]$', instance_item)
                if range_match: # Range-based like "Row[1,2]"
                    prefix = range_match.group(1)
                    start, end = int(range_match.group(2)), int(range_match.group(3))
                    instance_segments = [f"{prefix}{i}" for i in range(start, end + 1)]
                else: # Simple name like "Left"
                    instance_segments = [instance_item]
                
                for segment in instance_segments:
                    for prev_names, prev_paths in current_combinations:
                        next_combinations.append((prev_names + [segment], prev_paths + [segment]))

            elif isinstance(instance_item, list): # Nested instances, e.g., ["Row[1,2]", ["Left", "Right"]]
                outer_segments: List[str] = []
                outer_item = instance_item[0]
                range_match = re.match(r'^(\w+)\[(\d+),(\d+)\]$', outer_item)
                if range_match:
                    prefix = range_match.group(1)
                    start, end = int(range_match.group(2)), int(range_match.group(3))
                    outer_segments = [f"{prefix}{i}" for i in range(start, end + 1)]
                else:
                    outer_segments = [outer_item]

                inner_segments: List[str] = []
                if len(instance_item) > 1 and isinstance(instance_item[1], list):
                    for sub_item in instance_item[1]:
                        sub_range_match = re.match(r'^(\w+)\[(\d+),(\d+)\]$', sub_item)
                        if sub_range_match:
                            sub_prefix = sub_range_match.group(1)
                            sub_start, sub_end = int(sub_range_match.group(2)), int(sub_range_match.group(3))
                            inner_segments.extend([f"{sub_prefix}{i}" for i in range(sub_start, sub_end + 1)])
                        else:
                            inner_segments.append(sub_item)
                elif len(instance_item) > 1 and isinstance(instance_item[1], str):
                    inner_segments.append(instance_item[1])
                else:
                    inner_segments = [""] # Default for no specific inner segments

                for outer_seg in outer_segments:
                    for inner_seg in inner_segments:
                        combined_name = f"{outer_seg}_{inner_seg}" if inner_seg else outer_seg
                        combined_path = f"{outer_seg}.{inner_seg}" if inner_seg else outer_seg
                        for prev_names, prev_paths in current_combinations:
                            next_combinations.append((prev_names + [combined_name], prev_paths + [combined_path]))
            
            current_combinations = next_combinations

        for name_parts, path_parts in current_combinations:
            full_instance_name_segment = "_".join(filter(None, name_parts))
            full_instance_path_segment = ".".join(filter(None, path_parts))
            if not full_instance_name_segment and not full_instance_path_segment:
                yield "", ""
            else:
                yield full_instance_name_segment, full_instance_path_segment


    def _parse_vss_attributes(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts VSS-specific attributes from a node's details dictionary
        and returns them in a format ready for SignalNode constructor.
        """
        parsed_attrs = {}
        parsed_attrs['vss_min'] = details.get('min')
        parsed_attrs['vss_max'] = details.get('max')
        parsed_attrs['vss_default'] = details.get('default')
        parsed_attrs['vss_allowed_values'] = details.get('allowed')
        parsed_attrs['vss_pattern'] = details.get('pattern')
        parsed_attrs['vss_deprecation'] = details.get('deprecation')
        parsed_attrs['vss_instances'] = details.get('instances')
        return parsed_attrs

    def _parse_node_data(self, node_key: str, node_details: Dict[str, Any], parent_path: str = "") -> List[SignalNode]:
        """
        Parses a single VSS node definition. If the node is a 'branch' with 'instances',
        it expands these instances into multiple SignalNode objects for the branch itself,
        and recursively processes their children under the correct instantiated paths.
        Returns a list of SignalNode objects generated from this node definition.
        """
        vss_attrs = self._parse_vss_attributes(node_details)
        
        # --- CRITICAL FIX: Determine node_type more robustly and handle child parsing ---
        node_type = node_details.get("type")
        if node_type is None:
            # Check if it has signal-specific attributes (indicating it's a leaf)
            if 'datatype' in node_details and node_key not in ["min", "max", "allowed", "pattern"]:
                node_type = "signal"
            else:
                node_type = "branch" # Consider it as a branch if no datatype or only has aggregator attributes
        # --- END CRITICAL FIX ---

        generated_nodes: List[SignalNode] = []

        if node_type == "branch" and vss_attrs.get('vss_instances'):
            instances_def = vss_attrs['vss_instances']
            
            for instance_name_suffix, instance_path_segment in self._generate_instance_paths(node_key, instances_def):
                current_node_name = node_key
                instantiated_full_path = f"{parent_path}.{instance_path_segment}" if parent_path else instance_path_segment

                instance_node = SignalNode(
                    name=current_node_name,
                    path=instantiated_full_path,
                    node_type="branch", # Instances are typically for branches
                    description=node_details.get("description"),
                    datatype=node_details.get("datatype"), # Will be None for branches
                    unit=node_details.get("unit"), # Will be None for branches
                    **vss_attrs
                )
                generated_nodes.append(instance_node)
                
                if instance_node.path in self._all_nodes_in_hierarchy:
                    print(f"Info: Overwriting existing node definition for path: {instance_node.path} (likely from instance expansion).")
                self._all_nodes_in_hierarchy[instance_node.path] = instance_node

                for child_key_inner, child_value_inner in node_details.items():
                    # Only recurse into children that are actual node definitions (dictionaries)
                    # and are not VSS attributes we've already parsed.
                    if isinstance(child_value_inner, dict) and \
                       child_key_inner not in ['type', 'datatype', 'unit', 'description', 'min', 'max', 'default', 'allowed', 'pattern', 'deprecation', 'instances']:
                        
                        child_signal_nodes = self._parse_node_data(child_key_inner, child_value_inner, parent_path=instantiated_full_path)
                        for c_node in child_signal_nodes:
                            instance_node.children[c_node.name] = c_node
                            if c_node.path in self._all_nodes_in_hierarchy:
                                print(f"Info: Overwriting existing node definition for path: {c_node.path}")
                            self._all_nodes_in_hierarchy[c_node.path] = c_node

        else: # This is a non-instanced node (a signal, attribute, sensor, actuator, or a simple branch)
            current_full_path = f"{parent_path}.{node_key}" if parent_path else node_key
            
            main_node = SignalNode(
                name=node_key,
                path=current_full_path,
                node_type=node_type,
                description=node_details.get("description"),
                datatype=node_details.get("datatype"),
                unit=node_details.get("unit"),
                **vss_attrs
            )
            generated_nodes.append(main_node)
            
            if main_node.path in self._all_nodes_in_hierarchy:
                print(f"Info: Overwriting existing node definition for path: {main_node.path}.")
            self._all_nodes_in_hierarchy[main_node.path] = main_node

            for child_key_inner, child_value_inner in node_details.items():
                # Only recurse into children that are actual node definitions (dictionaries)
                # and are not VSS attributes we've already parsed.
                if isinstance(child_value_inner, dict) and \
                   child_key_inner not in ['type', 'datatype', 'unit', 'description', 'min', 'max', 'default', 'allowed', 'pattern', 'deprecation', 'instances']:
                    
                    child_signal_nodes = self._parse_node_data(child_key_inner, child_value_inner, parent_path=current_full_path)
                    for c_node in child_signal_nodes:
                        main_node.children[c_node.name] = c_node
        
        return generated_nodes


    def _handle_include_directive(self, include_line: str, include_value: Any, current_node: SignalNode):
        """
        Processes an '#include' directive. Fetches content and recursively parses it.
        The parsed nodes from the included file are then added to the global hierarchy map.
        """
        include_match = re.match(r"#include\s+([^\s]+)\s*(.*)", include_line)
        if not include_match:
            print(f"Warning: Malformed include directive: '{include_line}' in node '{current_node.path}'")
            return

        included_file_path_key = include_match.group(1)
        target_branch_path_in_directive = include_match.group(2).strip()

        effective_base_path_for_included_content = target_branch_path_in_directive if target_branch_path_in_directive else current_node.path

        if included_file_path_key in self.file_resolver:
            if included_file_path_key in self._parsed_file_stack:
                print(f"Warning: Circular include detected: '{included_file_path_key}'. Skipping.")
                return

            self._parsed_file_stack.append(included_file_path_key)
            included_content = self.file_resolver[included_file_path_key]
            
            print(f"  Including: '{included_file_path_key}' under target branch '{effective_base_path_for_included_content}'")

            parsed_top_level_from_include = self._parse_vss_content_internal(
                included_content,
                base_path=effective_base_path_for_included_content
            )

            if not target_branch_path_in_directive:
                 for node_name, node_obj in parsed_top_level_from_include.items():
                    current_node.children[node_name] = node_obj

            self._parsed_file_stack.pop()
        else:
            print(f"Warning: Included file content for '{included_file_path_key}' not found in resolver (referenced by '{current_node.path}'). Skipping include.")

    def _parse_vss_content_internal(self, vss_content: str, base_path: str = "") -> Dict[str, SignalNode]:
        """
        Internal recursive helper to parse a VSS content string (from a file or include).
        Returns a dictionary of top-level SignalNode objects defined directly in this content.
        This method is recursive and populates `self._all_nodes_in_hierarchy`.
        """
        try:
            parsed_yaml = yaml.safe_load(vss_content)
        except yaml.YAMLError as e:
            print(f"Error parsing VSS YAML content for base path '{base_path}': {e}")
            return {}

        top_level_nodes_in_this_content: Dict[str, SignalNode] = {}

        if not parsed_yaml:
            return top_level_nodes_in_this_content

        for key, value in parsed_yaml.items():
            if key.startswith("#include"):
                dummy_context_node = SignalNode(name="", path=base_path, node_type="branch")
                self._handle_include_directive(key, value, current_node=dummy_context_node)
                
                for child_name, child_node in dummy_context_node.children.items():
                    top_level_nodes_in_this_content[child_name] = child_node

            else:
                parsed_nodes_from_this_entry = self._parse_node_data(key, value, parent_path=base_path)
                for node in parsed_nodes_from_this_entry:
                    top_level_nodes_in_this_content[node.name] = node

        return top_level_nodes_in_this_content


    def load_vss_signals(self, root_vss_path_key: str) -> Dict[str, SignalNode]:
        """
        Loads and parses a root VSS file, recursively resolving its includes
        and expanding instances to build a complete, flattened dictionary of
        all unique SignalNode objects by their full VSS path.

        Args:
            root_vss_path_key (str): The key in the file_resolver dictionary
                                     corresponding to the main VSS file to parse.

        Returns:
            Dict[str, SignalNode]: A flattened dictionary where keys are the full
            VSS paths of all 'signal', 'branch', 'sensor', 'actuator', 'attribute' nodes found,
            and values are the corresponding SignalNode objects.
        """
        print(f"Starting VSS parsing for root: '{root_vss_path_key}'")
        
        self._parsed_file_stack = []
        self._all_nodes_in_hierarchy = {}

        if root_vss_path_key not in self.file_resolver:
            raise FileNotFoundError(f"Root VSS file '{root_vss_path_key}' not found in file resolver. "
                                    "Ensure it's provided in the VSSParser's file_resolver dictionary in main.py.")

        root_content = self.file_resolver[root_vss_path_key]
        self._parsed_file_stack.append(root_vss_path_key)
        
        self._parse_vss_content_internal(root_content, base_path="")
        
        self._parsed_file_stack.pop()

        print(f"Finished VSS parsing. Found {len(self._all_nodes_in_hierarchy)} unique nodes (including branches and instances).")
        return self._all_nodes_in_hierarchy