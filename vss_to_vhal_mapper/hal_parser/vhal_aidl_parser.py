# Parses VehicleProperty.aidl to extract AOSP property names and types
import re
from typing import Dict, List, Any, Optional

class VhalAidlParser:
    """
    Parses the content of a VehicleProperty.aidl file to extract structured
    information about standard Android VHAL properties.

    This parser focuses on extracting:
    - Property Name (e.g., "INFO_VIN")
    - Property ID components (base ID, PropertyGroup, Area, PropertyType)
    - Associated Javadoc annotations: change_mode, access, unit, data_enum, version
    """

    # Regex to capture a single VehicleProperty enum entry and its associated Javadoc annotations.
    # It looks for:
    # 1. Javadoc comments starting with /** and ending with */
    # 2. @change_mode, @access, @unit, @data_enum, @version annotations within the Javadoc
    # 3. The enum name (e.g., INFO_VIN)
    # 4. The hexadecimal value assignment (e.g., = 0x0100 + ...)
    PROPERTY_ENTRY_PATTERN = re.compile(
        r'/\*\*\s*'                                     # Start of Javadoc comment
        r'(.*?)\s*'                                     # Non-greedy capture of full Javadoc content (Group 1)
        r'\*/\s*'                                       # End of Javadoc comment
        r'(\w+)\s*=\s*'                                 # Property Name (Group 2)
        r'(0x[0-9a-fA-F]+)\s*'                          # Base ID Hex (Group 3)
        r'(?:\+\s*VehiclePropertyGroup\.([^\s]+)\s*)?'  # Optional VehiclePropertyGroup (Group 4)
        r'(?:\+\s*VehicleArea\.([^\s]+)\s*)?'           # Optional VehicleArea (Group 5)
        r'(?:\+\s*VehiclePropertyType\.([^\s]+)\s*)?'   # Optional VehiclePropertyType (Group 6)
        r',',                                           # End of property definition
        re.DOTALL | re.IGNORECASE
    )

    # Regex patterns for individual annotations within the Javadoc block
    ACCESS_ANNOTATION_PATTERN = re.compile(r'@access\s+([^\s]+)')
    CHANGE_MODE_ANNOTATION_PATTERN = re.compile(r'@change_mode\s+([^\s]+)')
    UNIT_ANNOTATION_PATTERN = re.compile(r'@unit\s+([^\s]+)')
    DATA_ENUM_ANNOTATION_PATTERN = re.compile(r'@data_enum\s+([^\s]+)')
    VERSION_ANNOTATION_PATTERN = re.compile(r'@version\s+([^\s]+)')


    def parse_aidl_file(self, aidl_file_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parses the content of a VehicleProperty.aidl file and extracts property definitions.

        Args:
            aidl_file_content (str): The full content of the VehicleProperty.aidl file.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where keys are property names
            (e.g., "INFO_VIN") and values are dictionaries containing their parsed metadata.
            Returns an empty dictionary if parsing fails or no properties are found.
        """
        parsed_properties = {}

        # Find all property entries using the main regex pattern
        matches = self.PROPERTY_ENTRY_PATTERN.finditer(aidl_file_content)

        for match in matches:
            try:
                # Extract groups from the main regex match
                full_javadoc_block = match.group(1).strip()
                property_name = match.group(2)
                base_id_hex = match.group(3)
                property_group = match.group(4)
                vehicle_area = match.group(5)
                property_type = match.group(6)

                # Extract annotations using their specific patterns from the full Javadoc block
                access_modes = [m.group(1) for m in self.ACCESS_ANNOTATION_PATTERN.finditer(full_javadoc_block)]
                change_mode = next((m.group(1) for m in self.CHANGE_MODE_ANNOTATION_PATTERN.finditer(full_javadoc_block)), None)
                unit = next((m.group(1) for m in self.UNIT_ANNOTATION_PATTERN.finditer(full_javadoc_block)), None)
                data_enums = [m.group(1) for m in self.DATA_ENUM_ANNOTATION_PATTERN.finditer(full_javadoc_block)]
                version = next((m.group(1) for m in self.VERSION_ANNOTATION_PATTERN.finditer(full_javadoc_block)), None)

                # Clean up description: remove annotations and leading/trailing whitespace/asterisks
                clean_description_lines = []
                for line in full_javadoc_block.split('\n'):
                    stripped_line = line.strip()
                    if stripped_line.startswith('*'):
                        stripped_line = stripped_line[1:].strip() # Remove leading asterisk
                    if not stripped_line.startswith('@'): # Exclude lines that are just annotations
                        clean_description_lines.append(stripped_line)
                clean_description = ' '.join(filter(None, clean_description_lines)).strip()
                if not clean_description:
                    clean_description = None # Set to None if no meaningful description remains

                property_data = {
                    "description": clean_description,
                    "change_mode": change_mode,
                    "access": access_modes if access_modes else [],
                    "unit": unit,
                    "data_enum": data_enums if data_enums else [],
                    "version": version,
                    "base_id_hex": base_id_hex,
                    "property_group": property_group,
                    "vehicle_area": vehicle_area,
                    "property_type": property_type,
                }
                parsed_properties[property_name] = property_data
            except Exception as e:
                print(f"Error parsing property entry for match: {match.group(0)[:100]}... Error: {e}")
                continue # Continue to next property even if one fails

        return parsed_properties

# Example Usage (for testing purposes, this block would typically be removed or
# placed in a separate test file for production code).
if __name__ == "__main__":
    # Define the path to the VehicleProperty.aidl file based on your project structure
    # This assumes the script is run from the project root or 'hal_parser' directory.
    # Adjust 'aidl_file_path' if your 'sample_data' directory is located elsewhere.
    aidl_file_path = "sample_data/VehicleProperty.aidl"

    try:
        with open(aidl_file_path, "r") as f:
            aidl_content = f.read()
    except FileNotFoundError:
        print(f"Error: '{aidl_file_path}' not found. Please ensure the file exists at the specified path.")
        print("You can place the content of VehicleProperty.aidl (from your uploaded VehicleProperty.txt)")
        print(f"into '{aidl_file_path}' for testing.")
        exit(1)

    parser = VhalAidlParser()
    parsed_vhal_properties = parser.parse_aidl_file(aidl_content)

    if parsed_vhal_properties:
        print(f"Successfully parsed {len(parsed_vhal_properties)} VHAL properties.")
        # Print a few examples to verify
        for i, (prop_name, prop_data) in enumerate(parsed_vhal_properties.items()):
            if i >= 5: # Print only first 5 for brevity
                break
            print(f"\nProperty: {prop_name}")
            for key, value in prop_data.items():
                print(f"  {key}: {value}")
    else:
        print("No VHAL properties parsed or an error occurred.")