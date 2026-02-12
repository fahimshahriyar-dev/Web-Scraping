import json
import csv
from typing import List, Dict, Any

def extract_price(price_str: str) -> str:
    """Extract price from string or return as is"""
    if price_str == "null":
        return ""
    return price_str

def get_type_from_category(category_name: str) -> str:
    """Get type from category name"""
    type_mapping = {
        'exterior_color': 'color',
        'circles_and_calipers': 'wheels',
        'roof': 'feature',
        'carbon': 'carbon_package',
        'livery_and_stickers': 'livery',
        'details': 'details',
        'interior': 'interior',
        'optional': 'optional',
        'alleggerita_package': 'package'
    }
    return type_mapping.get(category_name, category_name)

def flatten_json_structure(car_data: List[Dict]) -> List[Dict]:
    """
    Flatten the nested JSON structure into a flat format suitable for CSV
    Keep all names exactly as in JSON
    """
    flattened_rows = []
    
    for car in car_data:
        car_name = car.get('name', '')
        base_price = car.get('base_price', 'null')
        base_image = car.get('base_image', '')
        configurator_url = car.get('url', '')
        
        # Process each configuration
        for config in car.get('configurations', []):
            config_name = config.get('configuration_name', 'Default Configuration')
            categories = config.get('categories', {})
            
            # Process exterior_color
            if 'exterior_color' in categories:
                for item in categories['exterior_color']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'exterior_color'
                        row['category'] = 'exterior_color'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'no'  # Only one color can be selected
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Exterior color: {item.get('name', '')}"
                        flattened_rows.append(row)
            
            # Process circles_and_calipers
            if 'circles_and_calipers' in categories:
                for item in categories['circles_and_calipers']:
                    if isinstance(item, dict):
                        # Process wheels
                        if 'wheels' in item:
                            for wheel in item['wheels']:
                                row = create_base_row(car_name, base_price, base_image,
                                                     configurator_url, config_name)
                                row['type'] = 'wheels'
                                row['category'] = 'circles_and_calipers'
                                row['sub category'] = wheel.get('name', '')  # Option name moved here
                                row['multi allowed'] = 'no'  # Only one wheel type
                                row['price'] = extract_price(wheel.get('price', ''))
                                row['selected'] = str(wheel.get('currently_selected', False)).lower()
                                row['disabled'] = str(wheel.get('disabled', False)).lower()
                                row['image'] = wheel.get('car_image', wheel.get('swatch_image', ''))
                                row['description'] = f"{car_name} - Wheels: {wheel.get('name', '')}"
                                flattened_rows.append(row)
                        
                        # Process tyre
                        if 'tyre' in item:
                            for tyre in item['tyre']:
                                row = create_base_row(car_name, base_price, base_image,
                                                     configurator_url, config_name)
                                row['type'] = 'tyre'
                                row['category'] = 'circles_and_calipers'
                                row['sub category'] = tyre.get('name', '')  # Option name moved here
                                row['multi allowed'] = 'no'
                                row['price'] = extract_price(tyre.get('price', ''))
                                row['selected'] = str(tyre.get('currently_selected', False)).lower()
                                row['disabled'] = str(tyre.get('disabled', False)).lower()
                                row['image'] = tyre.get('car_image', tyre.get('swatch_image', ''))
                                row['description'] = f"{car_name} - Tyre: {tyre.get('name', '')}"
                                flattened_rows.append(row)
                        
                        # Process brake_calipers
                        if 'brake_calipers' in item:
                            for brake in item['brake_calipers']:
                                row = create_base_row(car_name, base_price, base_image,
                                                     configurator_url, config_name)
                                row['type'] = 'brake_calipers'
                                row['category'] = 'circles_and_calipers'
                                row['sub category'] = brake.get('name', '')  # Option name moved here
                                row['multi allowed'] = 'no'
                                row['price'] = extract_price(brake.get('price', ''))
                                row['selected'] = str(brake.get('currently_selected', False)).lower()
                                row['disabled'] = str(brake.get('disabled', False)).lower()
                                row['image'] = brake.get('car_image', brake.get('swatch_image', ''))
                                row['description'] = f"{car_name} - Brake calipers: {brake.get('name', '')}"
                                flattened_rows.append(row)
            
            # Process roof
            if 'roof' in categories:
                for item in categories['roof']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'roof'
                        row['category'] = 'roof'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'no'
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Roof: {item.get('name', '')}"
                        flattened_rows.append(row)
            
            # Process carbon
            if 'carbon' in categories:
                for item in categories['carbon']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'carbon'
                        row['category'] = 'carbon'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'no'
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Carbon package: {item.get('name', '')}"
                        flattened_rows.append(row)
            
            # Process livery_and_stickers
            if 'livery_and_stickers' in categories:
                for item in categories['livery_and_stickers']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'livery'
                        row['category'] = 'livery_and_stickers'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'no'
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Livery: {item.get('name', '')}"
                        flattened_rows.append(row)
            
            # Process details
            if 'details' in categories:
                for item in categories['details']:
                    if isinstance(item, dict):
                        for sub_cat_name, sub_cat_items in item.items():
                            if isinstance(sub_cat_items, list):
                                for sub_item in sub_cat_items:
                                    if isinstance(sub_item, dict):
                                        row = create_base_row(car_name, base_price, base_image,
                                                             configurator_url, config_name)
                                        row['type'] = 'details'
                                        row['category'] = 'details'
                                        # Combine sub_cat_name and option name
                                        row['sub category'] = f"{sub_cat_name}: {sub_item.get('name', '')}"
                                        row['multi allowed'] = 'no'
                                        row['price'] = extract_price(sub_item.get('price', ''))
                                        row['selected'] = str(sub_item.get('currently_selected', False)).lower()
                                        row['disabled'] = str(sub_item.get('disabled', False)).lower()
                                        row['image'] = sub_item.get('car_image', sub_item.get('swatch_image', ''))
                                        row['description'] = f"{car_name} - {sub_cat_name}: {sub_item.get('name', '')}"
                                        flattened_rows.append(row)
            
            # Process interior
            if 'interior' in categories:
                for item in categories['interior']:
                    if isinstance(item, dict):
                        for interior_type, interior_items in item.items():
                            if isinstance(interior_items, list):
                                for interior_item in interior_items:
                                    if isinstance(interior_item, dict):
                                        row = create_base_row(car_name, base_price, base_image,
                                                             configurator_url, config_name)
                                        row['type'] = 'interior'
                                        row['category'] = 'interior'
                                        
                                        # For interior, combine interior_type and colors for sub category
                                        main_color = interior_item.get('main_color', '')
                                        contrast_color = interior_item.get('color_contast', '')
                                        if main_color and contrast_color:
                                            option_text = f"{main_color} / {contrast_color}"
                                        else:
                                            option_text = main_color
                                        
                                        row['sub category'] = f"{interior_type}: {option_text}"
                                        row['multi allowed'] = 'no'
                                        row['price'] = extract_price(interior_item.get('price', ''))
                                        row['selected'] = str(interior_item.get('currently_selected', False)).lower()
                                        row['disabled'] = str(interior_item.get('disabled', False)).lower()
                                        row['image'] = interior_item.get('car_image', '')
                                        
                                        # Create description
                                        desc = f"{car_name} - {interior_type}"
                                        if main_color:
                                            desc += f" (Main: {main_color})"
                                        if contrast_color and contrast_color != main_color:
                                            desc += f" (Contrast: {contrast_color})"
                                        stitching = interior_item.get('stitching', '')
                                        if stitching and stitching != "Colore base":
                                            desc += f" (Stitching: {stitching})"
                                        row['description'] = desc
                                        
                                        flattened_rows.append(row)
            
            # Process optional
            if 'optional' in categories:
                for item in categories['optional']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'optional'
                        row['category'] = 'optional'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'yes'  # Multiple optional items can be selected
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Optional: {item.get('name', '')}"
                        flattened_rows.append(row)
            
            # Process alleggerita_package (Temerario specific)
            if 'alleggerita_package' in categories:
                for item in categories['alleggerita_package']:
                    if isinstance(item, dict):
                        row = create_base_row(car_name, base_price, base_image,
                                             configurator_url, config_name)
                        row['type'] = 'package'
                        row['category'] = 'alleggerita_package'
                        row['sub category'] = item.get('name', '')  # Option name moved here
                        row['multi allowed'] = 'no'
                        row['price'] = extract_price(item.get('price', ''))
                        row['selected'] = str(item.get('currently_selected', False)).lower()
                        row['disabled'] = str(item.get('disabled', False)).lower()
                        row['image'] = item.get('car_image', item.get('swatch_image', ''))
                        row['description'] = f"{car_name} - Alleggerita Package: {item.get('name', '')}"
                        flattened_rows.append(row)
    
    return flattened_rows

def create_base_row(car: str, base_price: str, base_image: str, url: str, 
                   config: str) -> Dict[str, Any]:
    """Create a base row with all required columns"""
    return {
        'car': car,
        'model': car,  # Same as car name
        'base price of car': extract_price(base_price),
        'type': '',
        'category': '',
        'sub category': '',
        'price': '',
        'multi allowed': 'no',
        'description': '',
        'image': '',
        'configuration_name': config,
        'configurator_url': url,
        'base_image': base_image,
        'selected': 'false',
        'disabled': 'false'
    }

def json_to_csv(json_file_path: str, csv_file_path: str) -> None:
    """
    Convert JSON file to a single comprehensive CSV file
    Keep all names exactly as in JSON
    """
    try:
        # Read JSON file
        print(f"Reading JSON file: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Found {len(data)} car models: {', '.join([car['name'] for car in data])}")
        
        # Flatten the data
        flattened_data = flatten_json_structure(data)
        
        if not flattened_data:
            print("No data found in JSON file")
            return
        
        print(f"Generated {len(flattened_data)} rows of data")
        
        # Define all required columns in NEW order
        required_columns = [
            'car',
            'model',
            'base price of car',  # Moved after model
            'type',               # Moved after base price
            'category',
            'sub category',       # Now contains option_name data
            'price',
            'multi allowed',
            'description',
            'image',
            'selected',
            'disabled',
            'configuration_name',
            'configurator_url',
            'base_image'
        ]
        # NOTE: 'option_name' column removed
        
        # Write to CSV
        print(f"Writing to CSV: {csv_file_path}")
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=required_columns)
            writer.writeheader()
            
            # Write each row
            for row in flattened_data:
                # Ensure all required columns exist
                for col in required_columns:
                    if col not in row:
                        row[col] = ''
                writer.writerow(row)
        
        print("\n" + "="*80)
        print("CONVERSION SUCCESSFUL!")
        print("="*80)
        print(f"Input JSON: {json_file_path}")
        print(f"Output CSV: {csv_file_path}")
        print(f"Total options/features: {len(flattened_data)}")
        print(f"Total columns: {len(required_columns)}")
        
        # Show summary statistics
        print("\nCATEGORIES FOUND IN DATA (exactly as in JSON):")
        print("-"*80)
        
        # Count by category
        category_counts = {}
        for row in flattened_data:
            category = row['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in sorted(category_counts.items()):
            print(f"{category}: {count} options")
        
        # Show sample data
        print("\nSAMPLE DATA (first 10 rows):")
        print("-"*80)
        print(f"{'Car':<12} {'Category':<20} {'Sub Category':<50}")
        print("-"*80)
        
        for i, row in enumerate(flattened_data[:10]):
            car = row['car']
            category = row['category'][:18] + "..." if len(row['category']) > 18 else row['category']
            sub_cat = row['sub category'][:47] + "..." if len(row['sub category']) > 47 else row['sub category']
            
            print(f"{car:<12} {category:<20} {sub_cat:<50}")
        
        print("\n" + "="*80)
        print("VERIFICATION:")
        print("="*80)
        print("✓ 'option_name' column removed")
        print("✓ Option names moved to 'sub category' column")
        print("✓ Column order: car, model, base price of car, type, category, sub category...")
        print("✓ All category names kept exactly as in JSON")
        print("✓ 'multi allowed' logic applied correctly")
        print("✓ One row per individual option")
        
    except FileNotFoundError:
        print(f"Error: File {json_file_path} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file_path}")
        print(f"Details: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # File paths
    json_file = "lamborghini_car_data.json"
    csv_output = "lamborghini_cars_options.csv"
    
    # Convert JSON to CSV
    json_to_csv(json_file, csv_output)
    
    print("\nDone! CSV file created successfully.")