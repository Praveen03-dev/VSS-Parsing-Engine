# File: VSS-Parsing-Engine/main.py

import os
import sys
import json
import shutil
import yaml

# Add the src directory to Python path for internal imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vss_parsing_engine.parsers.vss_parser import VSSParser
from vss_parsing_engine.processing.property_enricher import PropertyEnricher
from vss_parsing_engine.processing.signal_merger import SignalMerger
from vss_parsing_engine.generator.vhal_generator import VHALGenerator

def print_banner():
    """Print tool banner"""
    print("=" * 70)
    print("VSS to VHAL Conversion Tool")
    print("Vehicle Signal Specification -> Vehicle Hardware Abstraction Layer")
    print("=" * 70)

def load_yaml_config(filepath):
    """Helper function to load a YAML configuration file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {filepath}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {filepath}: {e}")
        sys.exit(1)

def vss_to_json(vss_file: str, json_output_file: str, config_dir: str):
    """Convert VSS to JSON intermediate format"""
    print("\nStep 1: Converting VSS to JSON...")

    if not os.path.exists(vss_file):
        print(f"Error: VSS file not found: {vss_file}")
        print("Please provide a valid .vspec file path.")
        sys.exit(1)

    try:
        with open(vss_file, 'r', encoding='utf-8') as f:
            vss_content = f.read()
        print(f"Loaded VSS file: {vss_file}")
    except Exception as e:
        print(f"Error loading VSS file: {e}")
        sys.exit(1)

    try:
        # Load configuration files
        print("Loading enrichment configurations...")
        typemap = load_yaml_config(os.path.join(config_dir, "typemap.yml"))
        heuristics = load_yaml_config(os.path.join(config_dir, "property_heuristics.yml"))
        unit_rules = load_yaml_config(os.path.join(config_dir, "unit_conversion_rules.yml"))

        vss_parser = VSSParser(file_resolver={vss_file: vss_content})
        
        print("Parsing VSS signals...")
        all_vss_signals = vss_parser.load_vss_signals(vss_file)
        
        if not all_vss_signals:
            print("No VSS signals found. Please check your .vspec file.")
            sys.exit(1)
        
        print(f"Parsed {len(all_vss_signals)} VSS signals")

        print("Enriching signals with VHAL attributes...")
        enricher = PropertyEnricher(
            property_heuristics=heuristics,
            typemap=typemap,
            unit_conversion_rules=unit_rules
        )
        enriched_vss_signals = enricher.enrich_signals(all_vss_signals)

        print("Merging and flattening signals...")
        merger = SignalMerger()
        unified_signal_model_data = merger.merge_and_flatten_signals(enriched_vss_signals)

        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(unified_signal_model_data, f, indent=2)

        print(f"Unified signal model saved to: {json_output_file}")
        print(f"Total signals processed: {len(unified_signal_model_data)}")
        
    except Exception as e:
        print(f"Error during VSS to JSON conversion: {e}")
        sys.exit(1)

def json_to_vhal(json_file: str, output_dir: str, templates_dir: str):
    """Generate VHAL structure from JSON"""
    print("\nStep 2: Generating VHAL structure from JSON...")
    
    try:
        vhal_generator = VHALGenerator(json_file, templates_dir)
        vhal_generator.generate_vhal_files(output_dir)
        
        print(f"VHAL files generated successfully!")
        print(f"Output directory: {output_dir}")
        
    except Exception as e:
        print(f"Error during VHAL generation: {e}")
        sys.exit(1)

def cleanup_intermediate_files(json_file: str, keep_json: bool = False):
    """Clean up intermediate files"""
    if not keep_json and os.path.exists(json_file):
        try:
            os.remove(json_file)
            print(f"Cleaned up intermediate file: {json_file}")
        except OSError as e:
            print(f"Error cleaning up file {json_file}: {e}")

def main():
    """Main entry point"""
    print_banner()
    
    if len(sys.argv) < 2:
        print("\nError: No input file specified")
        print("\nUsage:")
        print("   python main.py <vss_file>")
        print("\nExample:")
        print("   python main.py data/input/VehicleSignalSpecification.vspec")
        sys.exit(1)

    vss_file = sys.argv[1]
    json_output_file = os.path.join(os.path.dirname(vss_file), "unified_signal_model.json")
    vhal_output_dir = "output/vhal"
    config_dir = os.path.join(os.path.dirname(__file__), "config")
    templates_dir = os.path.join(os.path.dirname(__file__), "generator/templates")
    
    keep_json = "--keep-json" in sys.argv
    
    print(f"Input VSS file: {vss_file}")
    print(f"Output VHAL directory: {vhal_output_dir}")
    
    try:
        # Step 1: VSS to JSON
        vss_to_json(vss_file, json_output_file, config_dir)
        
        # Step 2: JSON to VHAL
        json_to_vhal(json_output_file, vhal_output_dir, templates_dir)
        
        # Cleanup intermediate files
        if not keep_json:
            cleanup_intermediate_files(json_output_file)
        
        # Success summary
        print("\n" + "=" * 70)
        print("SUCCESS: VSS to VHAL conversion completed!")
        print("=" * 70)
        print(f"Generated VHAL files are available in: {vhal_output_dir}/")
        print("Generated files include:")
        print("   • types.hal")
        print("   • DefaultConfig.h") 
        print("   • PropertyUtils.h")
        
        if keep_json:
            print(f"Intermediate JSON file preserved: {json_output_file}")
        
        print("\nReady for Android VHAL integration!")
        
    except KeyboardInterrupt:
        print("\n\n Process interrupted by user")
        cleanup_intermediate_files(json_output_file, False)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        cleanup_intermediate_files(json_output_file, False)
        sys.exit(1)

if __name__ == "__main__":
    main()
