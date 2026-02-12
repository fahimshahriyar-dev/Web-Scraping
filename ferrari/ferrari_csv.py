import json
import csv

def flatten_specs(specs, category_name, spec_group):
    """Flatten specification details into a list of items"""
    items = []
    if spec_group in specs.get(category_name, {}):
        for item in specs[category_name][spec_group]:
            items.append({
                'name': item.get('name', ''),
                'price': item.get('price', ''),
                'selected': item.get('selected', False)
            })
    return items

def convert_ferrari_json_to_csv(json_file, output_csv):
    """Convert Ferrari JSON to CSV format"""
    
    # Read JSON file
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Prepare CSV rows
    rows = []
    
    for model in data:
        model_name = model.get('name', '')
        base_image = model.get('base_image', '')
        
        # Handle different JSON structures
        trims_list = model.get('trims', [])
        
        for trim in trims_list:
            # Check if trim has nested trims (like 296 GTB)
            if 'trims' in trim:
                package_name = trim.get('name', '')
                # IMPORTANT: Get the package image if available
                package_image = trim.get('image', '')
                for sub_trim in trim.get('trims', []):
                    # Pass the sub_trim's own image if it exists, otherwise use package image
                    process_trim(rows, model_name, base_image, package_name, sub_trim, package_image)
            else:
                process_trim(rows, model_name, base_image, '', trim, '')
    
    # Write to CSV
    if rows:
        fieldnames = rows[0].keys()
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✓ Successfully converted {json_file} to {output_csv}")
        print(f"✓ Total rows: {len(rows)}")
    else:
        print("✗ No data to convert")

def process_trim(rows, model_name, base_image, package_name, trim, package_image=''):
    """Process a single trim and add to rows"""
    
    trim_name = trim.get('name', '')
    link = trim.get('link', '')
    price = trim.get('price', '')
    # ALWAYS use the trim's own image first, then package image, then fallback
    trim_image = trim.get('image', '') or package_image or ''
    specs = trim.get('specs', {})
    
    # Extract all specifications
    for category in ['Exterior', 'Interior', 'Equipment']:
        if category in specs:
            for spec_group, items in specs[category].items():
                for item in items:
                    row = {
                        'Car': model_name,
                        'Model': trim_name,
                        'base price of car': 'null',
                        'Base Image': base_image,
                        'Trim Image': trim_image,  # This will now have the correct image
                        'Type': spec_group,
                        'Category': spec_group,
                        'Sub Category': item.get('name', ''),
                        'Multi Allowed': 'no',
                        'description': '',
                        'Image': item.get('car_image', ''),
                        'Price': item.get('price', '0'),
                        'Swatch Image': item.get('swath_image', ''),
                        'Currently Selected': 'yes' if item.get('selected', False) else 'no'
                    }
                    rows.append(row)

if __name__ == "__main__":
    # Convert the JSON file
    input_file = "ferrari.json"
    output_file = "ferrari.csv"
    
    try:
        convert_ferrari_json_to_csv(input_file, output_file)
    except FileNotFoundError:
        print(f"✗ Error: {input_file} not found in current directory")
    except json.JSONDecodeError:
        print(f"✗ Error: {input_file} is not a valid JSON file")
    except Exception as e:
        print(f"✗ Error: {str(e)}")