import json
import csv
import re

def clean_price(price_str):
    """Extract numeric price from string like '$595' or '$ 1,150' or return '0' for standard items"""
    if not price_str or price_str == "$0" or price_str == "null" or price_str == 0:
        return "0"
    # Remove $ and commas, extract numbers
    cleaned = re.sub(r'[,$\s]', '', str(price_str))
    # Try to extract first number found
    match = re.search(r'\d+', cleaned)
    return match.group(0) if match else "0"

def get_selection_state(item_data):
    """Get selection/enabled state from various field names"""
    if 'currently_selected' in item_data:
        return item_data['currently_selected']
    elif 'currently_enabled' in item_data:
        return item_data['currently_enabled']
    elif 'state' in item_data:
        return item_data['state'] == 'yes'
    return False

def get_enabled_state(item_data):
    """Get enabled state for toggle items"""
    if 'currently_enabled' in item_data:
        return item_data['currently_enabled']
    elif 'state' in item_data:
        return item_data['state'] == 'yes'
    return False

def format_category_name(key):
    """Convert snake_case to Title Case"""
    return ' '.join(word.capitalize() for word in key.split('_'))

def process_item_list(items, parent_section, category_key, model_variant, base_price, rows):
    """Process a list of items (colors, wheels, etc.)"""
    if not isinstance(items, list):
        return
    
    # Use the category name as the section name (keep each category separate)
    category = format_category_name(category_key)
    section_name = category
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        # Skip explicitly disabled items
        if item.get('disabled') is True:
            continue
        
        # Check if this is a language selection item
        if 'language' in item and len(item) == 1:
            # Process as language option
            row = [
                model_variant,
                model_variant,
                base_price,
                section_name,
                category,
                item.get('language', ''),
                'No',
                '',
                '',
                '0',
                '',
                '',
                '',
                ''
            ]
            rows.append(row)
            continue
        
        # Check if this is a toggle item (has 'state' field only)
        is_toggle = 'state' in item and len([k for k in item.keys() if k != 'state']) == 0
        
        if is_toggle:
            # Process as toggle item
            row = [
                model_variant,
                model_variant,
                base_price,
                section_name,
                category,
                category,  # Sub Category same as category for toggles
                'No',
                '',
                '',
                '0',
                '',
                '',
                '',
                'Yes' if get_enabled_state(item) else 'No'
            ]
        else:
            # Process as regular item
            # Determine the image field to use
            image_field = ''
            if 'swatch_image' in item:
                image_field = 'swatch_image'
            elif 'wheel_image' in item:
                image_field = 'wheel_image'
            elif 'brake_image' in item:
                image_field = 'brake_image'
            elif 'image' in item:
                image_field = 'image'
            
            row = [
                model_variant,
                model_variant,
                base_price,
                section_name,
                category,
                item.get('name', ''),
                'No',
                item.get('group', ''),
                item.get('car_image', ''),
                clean_price(item.get('price', '$0')),
                item.get(image_field, ''),
                item.get('product_image', ''),
                'Yes' if get_selection_state(item) else 'No',
                'Yes' if get_enabled_state(item) else 'No' if 'currently_enabled' in item else ''
            ]
        
        rows.append(row)

def process_section(section_data, section_name, model_variant, base_price, rows):
    """Process a main section (color, wheels_brakes, exterior, interior, etc.)"""
    if not isinstance(section_data, dict):
        return
    
    # Process each category within the section
    for category_key, category_data in section_data.items():
        if isinstance(category_data, list):
            process_item_list(category_data, section_name, category_key, model_variant, base_price, rows)

def fix_json_file(json_file_path):
    """Attempt to fix common JSON errors"""
    print(f"Attempting to fix JSON file: {json_file_path}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix: Remove backslashes before closing brackets
        content = re.sub(r'\}\\(\s*\])', r'}\1', content)
        
        # Fix: Remove trailing backslashes
        content = re.sub(r'\\(\s*[,\]\}])', r'\1', content)
        
        # Try to parse the fixed content
        data = json.loads(content)
        
        # If successful, save the fixed version
        backup_file = json_file_path.replace('.json', '_backup.json')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ JSON file fixed! Backup saved as: {backup_file}")
        
        # Save the properly formatted version
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Fixed JSON saved to: {json_file_path}")
        return data
        
    except Exception as e:
        print(f"✗ Could not automatically fix JSON: {e}")
        return None

def process_mclaren_json_to_csv(json_file_path, csv_file_path):
    """Convert McLaren car JSON data to CSV format"""
    
    data = None
    
    # Try to read JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print("=" * 70)
        print("ERROR: Invalid JSON format!")
        print("=" * 70)
        print(f"File: {json_file_path}")
        print(f"Error at line {e.lineno}, column {e.colno}")
        print(f"Error message: {e.msg}")
        print()
        
        # Show the problematic line
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if e.lineno <= len(lines):
                    print("Problematic line:")
                    print(f"Line {e.lineno}: {lines[e.lineno-1].rstrip()}")
                    if e.lineno > 1:
                        print(f"Line {e.lineno-1}: {lines[e.lineno-2].rstrip()}")
        except:
            pass
        
        print()
        print("Common JSON errors to check:")
        print("  1. Extra or missing commas")
        print("  2. Backslashes (\\) in the wrong place")
        print("  3. Unmatched brackets or braces")
        print("  4. Missing quotes around strings")
        print()
        print("Attempting automatic fix...")
        print()
        
        # Try to fix the file
        data = fix_json_file(json_file_path)
        
        if data is None:
            print()
            print("=" * 70)
            print("MANUAL FIX REQUIRED")
            print("=" * 70)
            print("Please fix your JSON file manually:")
            print(f"  1. Open {json_file_path} in a text editor")
            print(f"  2. Go to line {e.lineno}")
            print("  3. Look for backslashes (\\), extra commas, or missing commas")
            print("  4. Fix the error and save the file")
            print("  5. Run this script again")
            print("=" * 70)
            return
        
    except FileNotFoundError:
        print(f"ERROR: File '{json_file_path}' not found!")
        print("Please make sure the file exists in the current directory.")
        return
    
    if data is None:
        return
    
    print("Type of data:", type(data))
    
    if not isinstance(data, list):
        raise ValueError(f"Expected data to be a list, but got {type(data)}")
    
    print(f"Processing {len(data)} model(s)...")
    
    # CSV headers
    headers = [
        'Car', 'Model', 'base price of car', 'Type', 'Category', 'Sub Category', 
        'Multi Allowed', 'Description', 'Image', 'Price',
        'Swatch Image', 'Product Image', 'Currently Selected', 'Currently Enabled'
    ]
    
    rows = []
    
    # Process each model in the data
    for idx, model in enumerate(data):
        if not isinstance(model, dict):
            print(f"Warning: Item {idx} is not a dictionary, skipping...")
            continue
            
        model_variant = model.get('name', f'Model_{idx}')
        base_price = model.get('base_price', 'null')
        print(f"Processing model: {model_variant}")
        
        # Get configurations
        configurations = model.get('configurations', [])
        if not configurations:
            print(f"  Warning: No configurations found for {model_variant}")
            continue
        
        # Process each configuration
        for config in configurations:
            if not isinstance(config, dict):
                continue
                
            config_name = config.get('configuration_name', 'Default')
            sections = config.get('sections', {})
            
            if not isinstance(sections, dict):
                print(f"  Warning: sections is not a dict for {model_variant}")
                continue
            
            # Process COLOR section
            if 'color' in sections and isinstance(sections['color'], list):
                for item in sections['color']:
                    if not isinstance(item, dict) or item.get('disabled') is True:
                        continue
                    
                    image_field = 'swatch_image' if 'swatch_image' in item else 'image'
                    row = [
                        model_variant,
                        model_variant,
                        base_price,
                        'Exterior Color',
                        'Exterior Color',
                        item.get('name', ''),
                        'No',
                        item.get('group', ''),
                        item.get('car_image', ''),
                        clean_price(item.get('price', '$0')),
                        item.get(image_field, ''),
                        item.get('product_image', ''),
                        'Yes' if get_selection_state(item) else 'No',
                        'Yes' if get_enabled_state(item) else 'No' if 'currently_enabled' in item else ''
                    ]
                    rows.append(row)
            
            # Process WHEELS_BRAKES section
            if 'wheels_brakes' in sections:
                wb = sections['wheels_brakes']
                if isinstance(wb, dict):
                    for wb_key, wb_data in wb.items():
                        if isinstance(wb_data, list):
                            # Determine custom section names
                            if wb_key == 'wheels':
                                for item in wb_data:
                                    if not isinstance(item, dict) or item.get('disabled') is True:
                                        continue
                                    
                                    row = [
                                        model_variant,
                                        model_variant,
                                        base_price,
                                        'Wheel Style',
                                        'Wheel Style',
                                        item.get('name', ''),
                                        'No',
                                        item.get('group', ''),
                                        item.get('car_image', ''),
                                        clean_price(item.get('price', '$0')),
                                        item.get('wheel_image', ''),
                                        item.get('product_image', ''),
                                        'Yes' if get_selection_state(item) else 'No',
                                        'Yes' if get_enabled_state(item) else 'No' if 'currently_enabled' in item else ''
                                    ]
                                    rows.append(row)
                            elif wb_key == 'wheel_finish':
                                for item in wb_data:
                                    if not isinstance(item, dict) or item.get('disabled') is True:
                                        continue
                                    
                                    row = [
                                        model_variant,
                                        model_variant,
                                        base_price,
                                        'Wheel Finish',
                                        'Wheel Finish',
                                        item.get('name', ''),
                                        'No',
                                        item.get('group', ''),
                                        item.get('car_image', ''),
                                        clean_price(item.get('price', '$0')),
                                        item.get('wheel_image', ''),
                                        item.get('product_image', ''),
                                        'Yes' if get_selection_state(item) else 'No',
                                        'Yes' if get_enabled_state(item) else 'No' if 'currently_enabled' in item else ''
                                    ]
                                    rows.append(row)
                            elif wb_key == 'brakes':
                                for item in wb_data:
                                    if not isinstance(item, dict) or item.get('disabled') is True:
                                        continue
                                    
                                    row = [
                                        model_variant,
                                        model_variant,
                                        base_price,
                                        'Brake Caliper Colour',
                                        'Brake Caliper Colour',
                                        item.get('name', ''),
                                        'No',
                                        item.get('group', ''),
                                        item.get('car_image', ''),
                                        clean_price(item.get('price', '$0')),
                                        item.get('brake_image', ''),
                                        item.get('product_image', ''),
                                        'Yes' if get_selection_state(item) else 'No',
                                        'Yes' if get_enabled_state(item) else 'No' if 'currently_enabled' in item else ''
                                    ]
                                    rows.append(row)
                            elif wb_key == 'tyre_type':
                                process_item_list(wb_data, 'Tyre Type', wb_key, model_variant, base_price, rows)
                            elif wb_key == 'track_brake_upgrade':
                                process_item_list(wb_data, 'Track Brake Upgrade', wb_key, model_variant, base_price, rows)
                            elif wb_key == 'lightweight_titanium_wheel_bolts':
                                process_item_list(wb_data, 'Lightweight Titanium Wheel Bolts', wb_key, model_variant, base_price, rows)
                            else:
                                process_item_list(wb_data, 'Accessories', wb_key, model_variant, base_price, rows)
            
            # Process EXTERIOR section
            if 'exterior' in sections:
                process_section(sections['exterior'], 'Exterior', model_variant, base_price, rows)
            
            # Process INTERIOR_SPECIFICATION section
            if 'interior_specification' in sections:
                process_section(sections['interior_specification'], 'Interior Specification', model_variant, base_price, rows)
            
            # Process INTERIOR section
            if 'interior' in sections:
                process_section(sections['interior'], 'Interior', model_variant, base_price, rows)
            
            # Process ENTERTAINMENT section
            if 'entertainment' in sections:
                process_section(sections['entertainment'], 'Entertainment', model_variant, base_price, rows)
            
            # Process OPTION_PACKAGES section
            if 'option_packages' in sections:
                process_section(sections['option_packages'], 'Option Packages', model_variant, base_price, rows)
            
            # Process OPTIONS section
            if 'options' in sections:
                process_section(sections['options'], 'Options', model_variant, base_price, rows)
            
            # Process SAFETY_AND_SECURITY section
            if 'safety_and_security' in sections:
                process_section(sections['safety_and_security'], 'Safety And Security', model_variant, base_price, rows)
            
            # Process PRACTICAL section
            if 'Practical' in sections:
                process_section(sections['Practical'], 'Practical', model_variant, base_price, rows)
    
    # Write to CSV
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        
        print()
        print("=" * 70)
        print(f"✓ SUCCESS! Converted {len(rows)} items to CSV")
        print(f"✓ Output file: {csv_file_path}")
        print("=" * 70)
    except Exception as e:
        print(f"ERROR: Failed to write CSV file: {e}")

if __name__ == "__main__":
    json_file = "mclaren_car_data.json"
    csv_file = "mclaren_car_data.csv"
    
    print("=" * 70)
    print("McLaren JSON to CSV Converter")
    print("=" * 70)
    print()
    
    process_mclaren_json_to_csv(json_file, csv_file)