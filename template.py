import os

def touch(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def create_project_structure(base_path="."):
    # Top-level files
    files = {
        ".gitignore": "# Python\n__pycache__/\n*.pyc\n.venv/\n",
        "LICENSE": "MIT License\n\nCopyright (c) 2025",
        "README.md": "# VSS Parsing and Signal Mapping Engine\n\nThis project maps VSS signals to Android VHAL format.",
        "requirements.txt": "pyyaml\nanytree\nvspec-tools\nfuzzywuzzy\n"
    }

    for name, content in files.items():
        touch(os.path.join(base_path, name), content)

    # Main project directory
    mapper = os.path.join(base_path, "vss_to_vhal_mapper")
    os.makedirs(mapper, exist_ok=True)
    touch(os.path.join(mapper, "__init__.py"))
    touch(os.path.join(mapper, "main.py"),
          '# CLI entrypoint: calls parser, enricher, merger\n')

    subdirs_with_files = {
        "hal_parser": {
            "vhal_aidl_parser.py": "# Parses VehicleProperty.aidl to extract AOSP property names and types"
        },
        "signal_parser": {
            "vss_parser.py": "# Parses .vspec and overlays using vspec-tools and builds SignalNode objects"
        },
        "vhal_property_enricher": {
            "property_enricher.py": "# Applies rules to generate aospId, aospArea, vhal_type, etc."
        },
        "merger": {
            "signal_merger.py": "# Combines enriched VSS signals into unified_signal_model.json"
        },
        "model": {
            "signal.py": "# Data classes for SignalNode and VHAL-enriched properties",
            "constants.py": "# Constants for types, areas, modes"
        },
        "config": {
            "typemap.yml": "# VSS type → Android type compatibility",
            "unit_conversion_rules.yml": "# Unit scaling/multiplier/offset logic",
            "property_heuristics.yml": "# Heuristics to determine areaType, changeMode, etc."
        },
        "sample_data": {
            "VehicleSignalSpecification.vspec": "# Sample VSS tree",
            "VehicleProperty.aidl": "// Android AIDL property list",
            "typemap.yml": "# Sample type compatibility data",
            "unit_conversion_rules.yml": "# Sample unit conversion config",
            "unified_signal_model.json": "{\n  \"signals\": []\n}",
        }
    }

    for subdir, files in subdirs_with_files.items():
        full_path = os.path.join(mapper, subdir)
        os.makedirs(full_path, exist_ok=True)
        touch(os.path.join(full_path, "__init__.py"))
        for filename, content in files.items():
            touch(os.path.join(full_path, filename), content)

    # Special case: sample_data/overlays/.keep
    overlays_path = os.path.join(mapper, "sample_data", "overlays")
    os.makedirs(overlays_path, exist_ok=True)
    touch(os.path.join(overlays_path, ".keep"), "# Keep overlays directory even if empty")

    # Mapper README
    touch(os.path.join(mapper, "README.md"),
          "# vss_to_vhal_mapper\n\nContains modules to parse VSS, enrich with AOSP-compatible VHAL metadata, and export a unified signal model.")

    print(f"✅ Project structure created under: {os.path.abspath(base_path)}")

if __name__ == "__main__":
    create_project_structure()
