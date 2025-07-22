# Combines enriched VSS signals into unified_signal_model.json

from typing import Dict, Any
from model.signal import SignalNode

class SignalMerger:
    """
    Merges and flattens the enriched SignalNode objects into a unified
    dictionary format suitable for JSON export.

    This class ensures that only actual 'signal', 'sensor', 'actuator',
    or 'attribute' nodes are included in the final output, as 'branch'
    nodes are primarily for hierarchical organization and do not typically
    translate directly into individual VHAL properties.
    """

    def merge_and_flatten_signals(self,
                                  enriched_signals: Dict[str, SignalNode]) -> Dict[str, Any]:
        """
        Takes a dictionary of enriched SignalNode objects (which may represent
        a hierarchy internally) and flattens them into a single dictionary
        where keys are the full VSS paths of data-carrying nodes, and values are
        their dictionary representations.

        Args:
            enriched_signals (Dict[str, SignalNode]): A dictionary of SignalNode objects,
                keyed by their full VSS path, after being enriched by the PropertyEnricher.

        Returns:
            Dict[str, Any]: A flattened dictionary where keys are the full VSS paths
            of 'signal', 'sensor', 'actuator', or 'attribute' nodes, and values are
            their JSON-serializable dictionary representations. This is the content
            for unified_signal_model.json.
        """
        print("Starting signal merging and flattening for JSON export...")
        unified_model = {}
        processed_count = 0

        # Iterate through all nodes.
        for path, signal_node in enriched_signals.items():
            # Corrected condition: Include if node_type is a data-carrying type
            if signal_node.node_type in ["signal", "sensor", "actuator", "attribute"]:
                unified_model[path] = signal_node.to_dict()
                processed_count += 1
            # Branch nodes (node_type == "branch") are organizational and are not
            # typically included as distinct properties in the flattened VHAL model.

        print(f"Finished merging and flattening. Exporting {processed_count} signal properties.")
        return unified_model