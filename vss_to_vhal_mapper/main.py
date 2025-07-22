# CLI entrypoint: calls parser, enricher, merger
import os
import json
import yaml
from typing import Dict, Any

# Import modules from our project structure
from signal_parser.vss_parser import VSSParser
from hal_parser.vhal_aidl_parser import VhalAidlParser
from vhal_property_enricher.property_enricher import PropertyEnricher
from merger.signal_merger import SignalMerger
from model.signal import SignalNode # For type hinting, if needed

def main():
    """
    Orchestrates the VSS to VHAL Mapper Tool process.
    Reads input files, processes signals, and generates a unified signal model JSON.
    """
    print("Starting VSS to VHAL Mapper Tool...")

    # --- Define file paths ---
    # Adjust these paths if your 'sample_data' or 'config' directories
    # are not directly under the 'vss_to_vhal_mapper' directory when running main.py
    # For this structure, assuming main.py is in vss_to_vhal_mapper/
    
    # Input VSS and AIDL files
    VSS_ROOT_FILE = os.path.join("sample_data", "VehicleSignalSpecification.vspec")
    VHAL_AIDL_FILE = os.path.join("sample_data", "VehicleProperty.aidl")

    # Configuration files
    TYPEMAP_CONFIG = os.path.join("config", "typemap.yml")
    UNIT_CONVERSION_CONFIG = os.path.join("config", "unit_conversion_rules.yml")
    PROPERTY_HEURISTICS_CONFIG = os.path.join("config", "property_heuristics.yml")

    # Output file
    OUTPUT_UNIFIED_MODEL_JSON = os.path.join("sample_data", "unified_signal_model.json")


    # --- Step 1: Load Raw File Contents ---
    file_contents: Dict[str, str] = {}
    try:
        # Crucial fix: Specify encoding to avoid 'charmap' decode errors
        with open(VSS_ROOT_FILE, 'r', encoding='utf-8') as f:
            file_contents[VSS_ROOT_FILE] = f.read()
        
        # Load other VSS files needed by includes.
        # This is a critical point: ALL .vspec files referenced by #include directives
        # in VehicleSignalSpecification.vspec and its transitive includes MUST be loaded here
        # and added to the file_contents dictionary with their correct relative paths.
        # Otherwise, VSSParser will report 'Included file content not found'.
        # Example for Vehicle/Vehicle.vspec and Powertrain/Powertrain.vspec:
        # (You need to extend this for all your project's .vspec files)
        
        # NOTE: For a complete solution, you'd likely write a helper function
        # that recursively finds and loads all .vspec files in your 'spec' and 'overlays'
        # directories into this file_contents dictionary based on their paths.
        
        # Hardcoding a few common includes for demonstration based on COVESA VSS structure:
        # Example: if Vehicle/Vehicle.vspec is at sample_data/Vehicle/Vehicle.vspec
        # with open(os.path.join("sample_data", "Vehicle", "Vehicle.vspec"), 'r', encoding='utf-8') as f:
        #     file_contents[os.path.join("Vehicle", "Vehicle.vspec")] = f.read() # Key should match #include path

        # with open(os.path.join("sample_data", "Powertrain", "Powertrain.vspec"), 'r', encoding='utf-8') as f:
        #     file_contents[os.path.join("Powertrain", "Powertrain.vspec")] = f.read()

        # Load the VHAL AIDL file
        with open(VHAL_AIDL_FILE, 'r', encoding='utf-8') as f:
            file_contents[VHAL_AIDL_FILE] = f.read()

    except FileNotFoundError as e:
        print(f"Critical Error: Required input file not found: {e.filename}. Please ensure all input and included files are correctly placed and accessible.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while loading files: {e}")
        return

    # --- Step 2: Parse VHAL AIDL File ---
    print("\nParsing VehicleProperty.aidl...")
    aidl_parser = VhalAidlParser()
    parsed_vhal_properties = aidl_parser.parse_aidl_file(file_contents[VHAL_AIDL_FILE])
    if not parsed_vhal_properties:
        print("Warning: No standard VHAL properties parsed from AIDL. Heuristics might be less accurate.")

    # --- Step 3: Parse VSS Signals ---
    print("\nParsing VSS signals from .vspec files...")
    # Initialize VSSParser with the file_contents dictionary as its resolver
    vss_parser = VSSParser(file_resolver=file_contents)
    
    # The root_vss_path passed here must be a key present in file_contents
    all_vss_signals = vss_parser.load_vss_signals(VSS_ROOT_FILE)
    if not all_vss_signals:
        print("Error: No VSS signals were parsed. Exiting.")
        return

    # --- Step 4: Enrich VSS Signals with VHAL Attributes ---
    print("\nEnriching VSS signals with VHAL-like attributes...")
    enricher = PropertyEnricher(
        typemap_filepath=TYPEMAP_CONFIG,
        unit_conversion_rules_filepath=UNIT_CONVERSION_CONFIG,
        property_heuristics_filepath=PROPERTY_HEURISTICS_CONFIG,
        parsed_vhal_properties=parsed_vhal_properties # Pass AIDL parsed data here
    )
    enriched_vss_signals = enricher.enrich_signals(all_vss_signals)

    # --- Step 5: Merge and Flatten for JSON Output ---
    print("\nMerging and flattening enriched signals for JSON export...")
    merger = SignalMerger()
    unified_signal_model_data = merger.merge_and_flatten_signals(enriched_vss_signals)

    # --- Step 6: Write Unified Signal Model to JSON File ---
    try:
        with open(OUTPUT_UNIFIED_MODEL_JSON, 'w', encoding='utf-8') as f: # Also specify encoding for output
            json.dump(unified_signal_model_data, f, indent=2)
        print(f"\n✅ Unified signal model successfully saved to: {OUTPUT_UNIFIED_MODEL_JSON}")
    except IOError as e:
        print(f"Error writing unified signal model to file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during JSON export: {e}")

if __name__ == "__main__":
    main()