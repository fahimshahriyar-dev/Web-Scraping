import json
import csv

def flatten_configuration(config_data, model_name, config_name, base_price, base_image, url):
    """Flatten a single configuration into rows"""
    rows = []
    
    if not config_data or 'categories' not in config_data:
        return rows
    
    categories = config_data['categories']
    
    for category_name, category_data in categories.items():
        # Handle different structures in categories
        if isinstance(category_data, list):
            for item in category_data:
                if isinstance(item, dict):
                    # Handle exterior_style which has nested structure
                    if category_name == 'exterior_style':
                        for subcategory_name, subcategory_list in item.items():
                            if isinstance(subcategory_list, list):
                                for subitem in subcategory_list:
                                    if isinstance(subitem, dict):
                                        row = {
                                            'car': model_name,
                                            'model': model_name,
                                            'configuration_name': config_name,
                                            'base price of car': base_price,
                                            'base_image': base_image,
                                            'url': url,
                                            'type': subcategory_name,  # Gets "Main Exterior Colour", "Contrast Exterior Colour", etc.
                                            'sub category': subitem.get('name', ''),  # Now gets "Lyrical Copper", "Darkest Tungsten", etc.
                                            'multi allowed': 'No',
                                            'description': None,
                                            'image': subitem.get('car_image', ''),
                                            'category': category_name,
                                            'option_name': subitem.get('name', ''),
                                            'price': subitem.get('price', ''),
                                            'swath_image': subitem.get('swath_image', ''),
                                            'car_image': subitem.get('car_image', ''),
                                            'selected': subitem.get('selected', False)
                                        }
                                        rows.append(row)
                    else:
                        # Handle regular categories
                        row = {
                            'car': model_name,
                            'model': model_name,
                            'configuration_name': config_name,
                            'base price of car': base_price,
                            'base_image': base_image,
                            'url': url,
                            'type': category_name,  # Gets category name like "wheels", "coachline", etc.
                            'sub category': item.get('name', ''),  # Now gets the actual option name
                            'multi allowed': 'No',
                            'description': None,
                            'image': item.get('car_image', ''),
                            'category': category_name,
                            'option_name': item.get('name', ''),
                            'price': item.get('price', ''),
                            'swath_image': item.get('swath_image', ''),
                            'car_image': item.get('car_image', ''),
                            'selected': item.get('selected', False)
                        }
                        rows.append(row)
        elif isinstance(category_data, dict):
            # Handle interior_environments which has nested dict structure
            for env_name, env_data in category_data.items():
                if isinstance(env_data, list):
                    for env_item in env_data:
                        if isinstance(env_item, dict):
                            for interior_type, interior_list in env_item.items():
                                if isinstance(interior_list, list):
                                    for interior_item in interior_list:
                                        if isinstance(interior_item, dict):
                                            for color_type, color_list in interior_item.items():
                                                if isinstance(color_list, list):
                                                    for color_item in color_list:
                                                        if isinstance(color_item, dict):
                                                            row = {
                                                                'car': model_name,
                                                                'model': model_name,
                                                                'configuration_name': config_name,
                                                                'base price of car': base_price,
                                                                'base_image': base_image,
                                                                'url': url,
                                                                'type': f"{env_name} - {interior_type}",  # Combined as type
                                                                'sub category': color_item.get('name', ''),  # Now gets the actual color name
                                                                'multi allowed': 'Yes',
                                                                'description': None,
                                                                'image': color_item.get('car_image', ''),
                                                                'category': category_name,
                                                                'option_name': color_item.get('name', ''),
                                                                'price': color_item.get('price', ''),
                                                                'swath_image': color_item.get('swath_image', ''),
                                                                'car_image': color_item.get('car_image', ''),
                                                                'selected': color_item.get('selected', False)
                                                            }
                                                            rows.append(row)
    
    return rows

def determine_multi_allowed(category_name, option_name):
    """Determine if multiple selections are allowed for a category"""
    # Categories where multiple selections are typically allowed
    multi_allowed_categories = [
        'exterior_style',
        'interior_environments',
        'headlining',
        'seat_options',
        'veneer_extended_applications',
        'additional_interior_options'
    ]
    
    if category_name in multi_allowed_categories:
        return 'Yes'
    
    # Specific options that allow multiple selections
    multi_allowed_keywords = [
        'package',
        'set',
        'multiple',
        'various',
        'combination'
    ]
    
    option_lower = option_name.lower()
    for keyword in multi_allowed_keywords:
        if keyword in option_lower:
            return 'Yes'
    
    return 'No'

def json_to_csv(json_file_path, csv_file_path):
    """Convert JSON file to CSV"""
    try:
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_rows = []
        
        # Process each model
        for model in data:
            model_name = model.get('name', '')
            base_price = model.get('base_price', 'null')
            base_image = model.get('base_image', '')
            url = model.get('url', '')
            
            # Process each configuration
            configurations = model.get('configurations', [])
            for config in configurations:
                config_name = config.get('configuration_name', '')
                config_data = config
                
                # Flatten configuration data
                rows = flatten_configuration(config_data, model_name, config_name, base_price, base_image, url)
                all_rows.extend(rows)
        
        # Update multi_allowed for all rows
        for row in all_rows:
            row['multi allowed'] = determine_multi_allowed(row['category'], row['option_name'])
        
        # Write to CSV
        if all_rows:
            # Get all fieldnames with new column order
            fieldnames = [
                'car',
                'model',
                'configuration_name',
                'base price of car',
                'base_image',
                'url',
                'type',
                'sub category',
                'multi allowed',
                'description',
                'image',
                'category',
                'option_name',
                'price',
                'swath_image',
                'car_image',
                'selected'
            ]
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
            
            print(f"Successfully converted {len(all_rows)} rows to {csv_file_path}")
            
            print(f"\nSummary by model:")
            for model in data:
                model_rows = [r for r in all_rows if r['car'] == model['name']]
                print(f"  - {model['name']}: {len(model_rows)} options")
            
            print(f"\nColumn value mapping (FINAL):")
            print(f"  - 'type': Gets the subcategory header (e.g., 'Main Exterior Colour', 'Coachline Colour')")
            print(f"  - 'sub category': Gets the actual option name (e.g., 'Lyrical Copper', 'Darkest Tungsten')")
            print(f"  - 'description': Always None/null")
            
            # Show sample of first few rows to verify the mapping
            print(f"\nSample of first 5 rows:")
            for i in range(min(5, len(all_rows))):
                row = all_rows[i]
                print(f"\nRow {i+1}:")
                print(f"  Type: '{row['type']}'")
                print(f"  Sub Category: '{row['sub category']}'")
                print(f"  Description: {row['description']}")
                print(f"  Option Name (original): '{row['option_name']}'")
                print(f"  Price: {row['price']}")
            
        else:
            print("No data found in JSON file")
            
    except FileNotFoundError:
        print(f"Error: JSON file '{json_file_path}' not found")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_file_path}'")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # File paths
    json_file_path = "RR.json"
    csv_file_path = "RR.csv"
    
    # Convert JSON to CSV
    json_to_csv(json_file_path, csv_file_path)