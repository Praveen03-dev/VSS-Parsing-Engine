

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run the main module
from vss_parsing_engine.main import main

if __name__ == "__main__":
    import sys
    
    # Check for --keep-json flag
    keep_json = "--keep-json" in sys.argv
    
    # Auto-detect the first available VSS file
    vss_file = os.path.join('data', 'input', 'VehicleSignalSpecification.vspec')
    json_output_file = os.path.join('data', 'input', 'unified_signal_model.json')
    vhal_output_dir = os.path.join('data', 'output')
    config_dir = os.path.join('src', 'vss_parsing_engine', 'config')
    templates_dir = os.path.join('src', 'vss_parsing_engine', 'generator', 'templates')

    # Use the detected file if it exists
    if os.path.exists(vss_file):
        print(f"Auto-detected VSS file: {vss_file}")
        if keep_json:
            print("--keep-json flag detected: intermediate JSON file will be preserved")
        from vss_parsing_engine.main import vss_to_json, json_to_vhal, cleanup_intermediate_files
        vss_to_json(vss_file, json_output_file, config_dir)
        json_to_vhal(json_output_file, vhal_output_dir, templates_dir)
        cleanup_intermediate_files(json_output_file, keep_json=keep_json)
    else:
        print("Error: No VSS file detected. Please place a .vspec file in the 'data/input' directory.")
