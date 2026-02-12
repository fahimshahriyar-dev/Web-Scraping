import json
import csv
import re

def clean_price(price_str):
    """Extract numeric price from string like '$595' or '$ 1,150' or return '0' for standard items"""
    if not price_str or price_str == "$0":
        return "0"
    # Remove $ and commas, extract numbers
    cleaned = re.sub(r'[,$\s]', '', str(price_str))
    # Try to extract first number found
    match = re.search(r'\d+', cleaned)
    return match.group(0) if match else "0"

def process_json_to_csv(json_file_path, csv_file_path):
    """Convert grouped car JSON data to CSV format"""
    
    # Read JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Debug: Check what type of data we have
    print("Type of data:", type(data))
    
    # Ensure data is a list
    if not isinstance(data, list):
        raise ValueError(f"Expected data to be a list, but got {type(data)}")
    
    print(f"Processing {len(data)} car family(ies)...")
    
    # CSV headers - Car, Model, base price of car, then other columns
    headers = [
        'Car', 'Model', 'base price of car', 'Type', 'Category', 'Sub Category', 
        'Multi Allowed', 'Description', 'Image', 'Price',
        'Display Name', 'Swatch Image', 'Currently Selected'
    ]
    
    rows = []
    
    # Process each car family in the data
    for idx, car_family in enumerate(data):
        if not isinstance(car_family, dict):
            print(f"Warning: Item {idx} is not a dictionary, skipping...")
            continue
        
        # Get car family name (e.g., "Countryman", "Cooper 2 Door")
        car_name = car_family.get('name', f'Car_{idx}')
        print(f"\nProcessing car family: {car_name}")
        
        # Get all trims for this car family
        trims = car_family.get('trims', [])
        if not trims:
            print(f"  Warning: No trims found for {car_name}")
            continue
        
        print(f"  Found {len(trims)} trim(s)")
        
        # Process each trim
        for trim_idx, trim in enumerate(trims):
            if not isinstance(trim, dict):
                print(f"  Warning: Trim {trim_idx} is not a dictionary, skipping...")
                continue
            
            # Get trim name from 'name' field (e.g., "Countryman S ALL4", "Cooper C 2 Door")
            trim_name = trim.get('name', f'Trim_{trim_idx}')
            base_price = clean_price(trim.get('base_price', '$0'))
            print(f"    Processing trim: {trim_name} (base price: {base_price})")
            
            # Get configurations
            configurations = trim.get('configurations', [])
            if not configurations:
                print(f"      Warning: No configurations found for {trim_name}")
                continue
            
            # Process each configuration
            for config in configurations:
                if not isinstance(config, dict):
                    continue
                
                config_name = config.get('configuration_name', 'Default')
                print(f"      Processing configuration: {config_name}")
                
                # Handle "Trim & Style" configuration differently
                if config_name == "Trim & Style":
                    trim_style_items = config.get('categories', [])
                    for item in trim_style_items:
                        if not isinstance(item, dict):
                            continue
                        
                        # Build display name and description
                        trim_type = item.get('name', '')
                        style = item.get('style', '')
                        
                        # Create sub category - combine trim name and style if style exists
                        if style:
                            sub_category = f"{trim_type} - {style}"
                        else:
                            sub_category = trim_type
                        
                        row = [
                            car_name,
                            trim_name,
                            base_price,
                            'Trim & Style',
                            'Trim & Style',
                            sub_category,
                            'No',
                            style,  # Put style in description
                            item.get('car_image', ''),
                            clean_price(item.get('price', '$0')),
                            sub_category,  # Display name same as sub category
                            '',  # No swatch image for trim & style
                            'No'  # No currently_selected field in this data
                        ]
                        rows.append(row)
                    
                    continue  # Skip to next configuration
                
                # Handle regular configurations (Default Configuration, etc.)
                categories = config.get('categories', {})
                
                if not isinstance(categories, dict):
                    print(f"      Warning: categories is not a dict for {trim_name}")
                    continue
                
                # Process Exterior Colors
                exterior_colors = categories.get('exterior_colors', [])
                for color in exterior_colors:
                    if not isinstance(color, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Color',
                        'Exterior Color',
                        color.get('name', ''),
                        'No',
                        '',
                        color.get('car_image', ''),
                        clean_price(color.get('price', '$0')),
                        color.get('display_name', ''),
                        color.get('swatch_image', ''),
                        'Yes' if color.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Roof and Mirror Caps
                roof_mirror_caps = categories.get('roof_mirror_caps', [])
                for item in roof_mirror_caps:
                    if not isinstance(item, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Roof & Mirror',
                        'Roof and Mirror Caps',
                        item.get('name', ''),
                        'No',
                        '',
                        item.get('car_image', ''),
                        clean_price(item.get('price', '$0')),
                        item.get('display_name', ''),
                        item.get('swatch_image', ''),
                        'Yes' if item.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Wheels
                wheels = categories.get('wheels', [])
                for wheel in wheels:
                    if not isinstance(wheel, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Wheels',
                        'Wheels',
                        wheel.get('name', ''),
                        'No',
                        '',
                        wheel.get('car_image', ''),
                        clean_price(wheel.get('price', '$0')),
                        wheel.get('display_name', ''),
                        wheel.get('swatch_image', ''),
                        'Yes' if wheel.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Brake Calipers
                brake_calipers = categories.get('brake_calipers', [])
                for caliper in brake_calipers:
                    if not isinstance(caliper, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Brake Calipers',
                        'Brake Calipers',
                        caliper.get('name', ''),
                        'No',
                        '',
                        caliper.get('car_image', ''),
                        clean_price(caliper.get('price', '$0')),
                        caliper.get('display_name', ''),
                        caliper.get('swatch_image', ''),
                        'Yes' if caliper.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Interior
                interior = categories.get('interior', [])
                for item in interior:
                    if not isinstance(item, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Interior',
                        'Interior',
                        item.get('name', ''),
                        'No',
                        '',
                        item.get('car_image', ''),
                        clean_price(item.get('price', '$0')),
                        item.get('display_name', ''),
                        item.get('swatch_image', ''),
                        'Yes' if item.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Trim
                trim_options = categories.get('trim', [])
                for trim_item in trim_options:
                    if not isinstance(trim_item, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Trim',
                        'Trim',
                        trim_item.get('name', ''),
                        'No',
                        '',
                        trim_item.get('car_image', ''),
                        clean_price(trim_item.get('price', '$0')),
                        trim_item.get('display_name', ''),
                        trim_item.get('swatch_image', ''),
                        'Yes' if trim_item.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Liveries and Dreamlines
                liveries = categories.get('liveries_and_dreamlines', [])
                for livery in liveries:
                    if not isinstance(livery, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Liveries',
                        'Liveries and Dreamlines',
                        livery.get('name', ''),
                        'No',
                        '',
                        livery.get('car_image', ''),
                        clean_price(livery.get('price', '$0')),
                        livery.get('display_name', ''),
                        livery.get('swatch_image', ''),
                        'Yes' if livery.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Soft Top
                soft_top = categories.get('soft_top', [])
                for top in soft_top:
                    if not isinstance(top, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Soft Top',
                        'Soft Top',
                        top.get('name', ''),
                        'No',
                        '',
                        top.get('car_image', ''),
                        clean_price(top.get('price', '$0')),
                        top.get('display_name', ''),
                        top.get('swatch_image', ''),
                        'Yes' if top.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Packages
                packages = categories.get('packages', [])
                for package in packages:
                    if not isinstance(package, dict):
                        continue
                    
                    features = package.get('features', [])
                    description = ', '.join(features) if features else ''
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Packages',
                        'Packages',
                        package.get('name', ''),
                        'No',
                        description,
                        package.get('car_image', ''),
                        clean_price(package.get('price', '$0')),
                        package.get('display_name', ''),
                        package.get('swatch_image', ''),
                        'Yes' if package.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Options/Accessories
                options = categories.get('options', [])
                for option in options:
                    if not isinstance(option, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Accessories',
                        'Accessories',
                        option.get('name', ''),
                        'No',
                        '',
                        option.get('car_image', ''),
                        clean_price(option.get('price', '$0')),
                        option.get('display_name', ''),
                        option.get('swatch_image', ''),
                        'Yes' if option.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
                
                # Process Highlights (if available)
                highlights = categories.get('highlights', [])
                for highlight in highlights:
                    if not isinstance(highlight, dict):
                        continue
                    
                    row = [
                        car_name,
                        trim_name,
                        base_price,
                        'Highlights',
                        'Highlights',
                        highlight.get('name', ''),
                        'No',
                        '',
                        highlight.get('car_image', ''),
                        clean_price(highlight.get('price', '$0')),
                        highlight.get('display_name', ''),
                        highlight.get('swatch_image', ''),
                        'Yes' if highlight.get('currently_selected', False) else 'No'
                    ]
                    rows.append(row)
    
    # Write to CSV
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"\n✓ Conversion complete! {len(rows)} rows written to {csv_file_path}")
    
    # Print summary
    car_families = {}
    for row in rows:
        car = row[0]
        trim = row[1]
        if car not in car_families:
            car_families[car] = set()
        car_families[car].add(trim)
    
    print("\nSummary:")
    for car, trims in car_families.items():
        print(f"  {car}: {len(trims)} trim(s)")

# Usage
if __name__ == "__main__":
    # Replace with your actual file paths
    json_file = "mini_cooper.json"
    csv_file = "mini_cooper.csv"
    
    try:
        process_json_to_csv(json_file, csv_file)
    except FileNotFoundError:
        print(f"Error: Could not find {json_file}")
        print("Please make sure the JSON file exists in the same directory.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in the input file.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()