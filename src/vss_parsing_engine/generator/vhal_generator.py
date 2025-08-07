from jinja2 import Environment, FileSystemLoader
import os
import json
import shutil

class VHALGenerator:
    def __init__(self, json_file: str, templates_dir: str):
        self.json_file = json_file
        self.templates_dir = templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(templates_dir))
        self.signals = self.load_signals()

        # Files that should NEVER be generated (they are static AOSP files)
        self.static_files_dir = os.path.join(templates_dir, 'static')
        
        # Files to be generated
        self.generated_files = {
            'types.hal.jinja2': 'types.hal',
            'DefaultConfig.h.jinja2': 'impl/DefaultConfig.h',
            'PropertyUtils.h.jinja2': 'impl/PropertyUtils.h',
            'PropertyUtils.cpp.jinja2': 'src/PropertyUtils.cpp',
            'Android.bp.jinja2': 'Android.bp',
            'VehicleService.cpp.jinja2': 'src/VehicleService.cpp'
        }

        # Manual implementation templates (now treated as Jinja2 templates)
        self.manual_templates = {
            'DefaultVehicleHal.h.jinja2': 'impl/DefaultVehicleHal.h',
            'DefaultVehicleHal.cpp.jinja2': 'src/DefaultVehicleHal.cpp',
            'MockSensor.h.jinja2': 'impl/MockSensor.h',
            'MockActuator.h.jinja2': 'impl/MockActuator.h',
            'SubscriptionManager.h.jinja2': 'impl/SubscriptionManager.h'
        }
        
        # VSS Converter files (new dynamic conversion system)
        self.vss_converter_files = {
            'VssVehicleEmulator.h.jinja2': 'impl/VssVehicleEmulator.h',
            'VssVehicleEmulator.cpp.jinja2': 'src/VssVehicleEmulator.cpp',
            'VssCommConn.h.jinja2': 'impl/VssCommConn.h',
            'VssCommConn.cpp.jinja2': 'src/VssCommConn.cpp',
            'VssSocketComm.h.jinja2': 'impl/VssSocketComm.h',
            'VssSocketComm.cpp.jinja2': 'src/VssSocketComm.cpp',
            'AndroidVssConverter.h.jinja2': 'impl/AndroidVssConverter.h',
            'AndroidVssConverter.cpp.jinja2': 'src/AndroidVssConverter.cpp',
            'ConverterUtils.h.jinja2': 'impl/ConverterUtils.h',
            'ConverterUtils.cpp.jinja2': 'src/ConverterUtils.cpp'
        }

    def load_signals(self):
        """Load signals from JSON file"""
        with open(self.json_file, 'r') as f:
            return json.load(f)

    def _extract_property_data(self):
        """Extract and organize property data for templates"""
        properties = []
        signals_with_ids = 0
        
        # Debug: Print total signals and sample first few
        print(f"\nProcessing {len(self.signals)} signals for VHAL property extraction...")
        if self.signals:
            first_signal_path = list(self.signals.keys())[0] if isinstance(self.signals, dict) else "N/A"
            print(f"First signal path: {first_signal_path}")
            if isinstance(self.signals, dict) and first_signal_path in self.signals:
                sample_signal = self.signals[first_signal_path]
                print(f"Sample signal fields: {list(sample_signal.keys())}")
        
        # Handle both dict (path -> signal_data) and list formats
        signal_items = self.signals.items() if isinstance(self.signals, dict) else enumerate(self.signals)
        
        for path_or_idx, signal in signal_items:
            # Extract relevant data for VHAL generation
            property_data = {
                'id': signal.get('vhal_id_base', 'UNKNOWN'),  # Use vhal_id_base instead of aospId
                'vhal_id': signal.get('vhal_id', ''),  # String ID for template
                'vhal_id_base': signal.get('vhal_id_base', 'UNKNOWN'),  # Hex ID for template
                'name': signal.get('name', ''),
                'path': signal.get('path', path_or_idx if isinstance(path_or_idx, str) else ''),
                'type': signal.get('vhal_type', 'MIXED'),  # Use vhal_type instead of vhal_data_type
                'vhal_type': signal.get('vhal_type', 'MIXED'),  # Also provide as vhal_type for templates
                'access': signal.get('vhal_access', 'READ'),  # Use vhal_access
                'vhal_access': signal.get('vhal_access', 'READ'),  # Also provide as vhal_access for templates
                'change_mode': signal.get('vhal_change_mode', 'ON_CHANGE'),  # Use vhal_change_mode
                'vhal_change_mode': signal.get('vhal_change_mode', 'ON_CHANGE'),  # Also provide as vhal_change_mode for templates
                'areas': signal.get('vhal_area', 'GLOBAL'),  # Use vhal_area
                'vhal_area': signal.get('vhal_area', 'GLOBAL'),  # Also provide as vhal_area for templates
                'vhal_property_group': signal.get('vhal_property_group', 'SYSTEM'),  # Property group for templates
                'unit': signal.get('unit', ''),
                'description': signal.get('description', ''),
                'datatype': signal.get('datatype', ''),
                'node_type': signal.get('node_type', '')
            }
            
            # Only include signals that have valid VHAL properties AND are not branch nodes
            # Branch nodes are organizational and should not become VehicleProperty entries
            if (property_data['id'] != 'UNKNOWN' and property_data['id'] and 
                property_data['node_type'] not in ['branch']):
                properties.append(property_data)
                signals_with_ids += 1
                
                # Debug: Log first few processed signals
                if signals_with_ids <= 5:
                    print(f"  ✓ Signal: {property_data['name']} -> ID: {property_data['id']}, Type: {property_data['type']}, Node Type: {property_data['node_type']}")
            elif property_data['node_type'] == 'branch' and property_data['id'] != 'UNKNOWN':
                # Debug: Log branch nodes that are being excluded
                if signals_with_ids <= 5:
                    print(f"  ⚠ Excluded branch node: {property_data['name']} -> ID: {property_data['id']}, Node Type: {property_data['node_type']}")
        
        print(f"Successfully extracted {signals_with_ids} signals with VHAL property IDs out of {len(self.signals)} total signals.")
        
        if signals_with_ids == 0:
            print("WARNING: No signals found with valid VHAL property IDs. The generated files may be empty.")
            print("This usually means the enrichment process didn't generate vhal_id_base fields correctly.")
        
        return properties

    def _copy_static_files(self, output_dir: str):
        """Copy static AOSP files that should not be generated"""
        if not os.path.exists(self.static_files_dir):
            print(f"Warning: Static files directory not found: {self.static_files_dir}")
            return
            
        static_files_map = {
            'IVehicle.hal': 'IVehicle.hal',
            'IVehicleCallback.hal': 'IVehicleCallback.hal',
            'service.rc': 'android.hardware.automotive.vehicle@2.0-default-service.rc',
            'service.xml': 'android.hardware.automotive.vehicle@2.0-default-service.xml'
        }
        
        for src_file, dest_path in static_files_map.items():
            src_path = os.path.join(self.static_files_dir, src_file)
            dest_full_path = os.path.join(output_dir, dest_path)
            
            if os.path.exists(src_path):
                os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
                shutil.copy2(src_path, dest_full_path)
                print(f"Copied static file: {dest_path}")
            else:
                print(f"Warning: Static file not found: {src_path}")

    def _generate_manual_files(self, output_dir: str, context: dict):
        """Generate manual files from Jinja2 templates with property data"""
        for template_name, output_filename in self.manual_templates.items():
            output_path = os.path.join(output_dir, output_filename)
            # Always regenerate manual files to include latest property data
            try:
                template = self.jinja_env.get_template(f'manual/{template_name}')
                content = template.render(context)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(content)
                print(f"Generated enhanced manual implementation: {output_filename}")
            except Exception as e:
                print(f"Warning: Could not generate {template_name}: {e}")
                print(f"Falling back to static template copy...")
                # Fallback to old behavior if template is not found
                template_path = os.path.join(self.templates_dir, 'manual', template_name)
                if os.path.exists(template_path):
                    shutil.copy2(template_path, output_path)
                    print(f"Copied static template: {output_filename}")
    
    def _extract_conversion_data(self):
        """Extract VSS to VHAL conversion data for dynamic converter generation"""
        conversion_mappings = []
        
        signal_items = self.signals.items() if isinstance(self.signals, dict) else enumerate(self.signals)
        
        for path_or_idx, signal in signal_items:
            # Only process signals that have VHAL mappings and are not branch nodes
            if (signal.get('vhal_id_base', 'UNKNOWN') != 'UNKNOWN' and
                signal.get('node_type', '') not in ['branch'] and
                signal.get('datatype') and signal.get('vhal_type')):
                
                conversion_data = {
                    'vss_path': signal.get('path', path_or_idx if isinstance(path_or_idx, str) else ''),
                    'vhal_property_id': signal.get('vhal_id_base', ''),
                    'vss_datatype': signal.get('datatype', ''),
                    'vhal_type': signal.get('vhal_type', 'MIXED'),
                    'unit': signal.get('unit', ''),
                    'unit_multiplier': signal.get('unit_multiplier', 1.0),
                    'unit_offset': signal.get('unit_offset', 0.0),
                    'min_value': signal.get('min_value'),
                    'max_value': signal.get('max_value'),
                    'initial_value': signal.get('initial_value'),
                    'vhal_access': signal.get('vhal_access', 'READ'),
                    'vhal_area': signal.get('vhal_area', 'GLOBAL'),
                    'vhal_change_mode': signal.get('vhal_change_mode', 'ON_CHANGE'),
                    'description': signal.get('description', '')
                }
                conversion_mappings.append(conversion_data)
        
        print(f"Generated {len(conversion_mappings)} VSS to VHAL conversion mappings")
        return conversion_mappings
    
    def _generate_vss_converter_files(self, output_dir: str, context: dict):
        """Generate VSS converter system files"""
        print("\nGenerating VSS converter system...")
        
        # Extract conversion data for the converter
        conversion_mappings = self._extract_conversion_data()
        converter_context = {
            **context,
            'conversion_mappings': conversion_mappings,
            'total_signals': len(conversion_mappings)
        }
        
        for template_name, output_filename in self.vss_converter_files.items():
            output_path = os.path.join(output_dir, output_filename)
            try:
                template = self.jinja_env.get_template(f'vss_converter/{template_name}')
                content = template.render(converter_context)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(content)
                print(f"Generated VSS converter: {output_filename}")
            except Exception as e:
                print(f"Warning: Could not generate VSS converter {template_name}: {e}")

    def generate_vhal_files(self, output_dir: str):
        """Generate VHAL files including the VSS converter system"""
        print("\nGenerating VHAL files...")
        os.makedirs(output_dir, exist_ok=True)
        properties = self._extract_property_data()
        context = {'properties': properties, 'vss_file_path': self.json_file}

        # Generate core VHAL files
        for template_name, output_name in self.generated_files.items():
            template = self.jinja_env.get_template(template_name)
            content = template.render(context)
            output_path = os.path.join(output_dir, output_name)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(content)
            print(f"Generated {output_name}")

        # Generate VSS converter system
        self._generate_vss_converter_files(output_dir, context)
        
        # Copy static files and generate manual templates
        self._copy_static_files(output_dir)
        self._generate_manual_files(output_dir, context)
        
        print("\n" + "="*70)
        print("VHAL files generation complete!")
        print("Generated components:")
        print("  • Core VHAL files (types.hal, DefaultConfig.h, etc.)")
        print("  • VSS converter system (VssVehicleEmulator, AndroidVssConverter, etc.)")
        print("  • Communication layer (VssSocketComm, VssCommConn)")
        print("  • Enhanced manual implementations")
        print("="*70)
