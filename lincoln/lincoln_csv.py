import json
import csv
import os

def extract_car_info(vehicle, trim, data_section):
    """
    Extract all the specific information needed for the columns
    Changes:
    - type column now contains what was in sub_category
    - sub category column now contains what was in name
    - name column is removed
    - description is set to empty/null
    """
    rows = []
    
    vehicle_name = vehicle.get('vehicle', '')
    base_image = vehicle.get('base_image', '')
    trim_name = trim.get('trim_name', '')
    trim_price = trim.get('trim_price', '')
    trim_image = trim.get('trim_image', '')
    
    # Extract model name by removing "2026 Lincoln " prefix
    model_name = trim_name.replace("2026 Lincoln ", "").replace("®", "").strip()
    
    # Base car info that will be common for all rows of this trim
    base_info = {
        'car': vehicle_name,
        'model': model_name,
        'base price of car': trim_price.replace('$', '').replace(',', '') if trim_price else '',
        'image': trim_image or base_image,
        'description': ''  # Set to null/empty
    }
    
    # 1. Paint Colors
    if 'paint_colors' in data_section and isinstance(data_section['paint_colors'], list):
        for color in data_section['paint_colors']:
            if isinstance(color, dict):
                row = base_info.copy()
                row.update({
                    'category': 'Paint',
                    'type': 'Exterior Color',  # What was sub_category
                    'sub category': color.get('name', ''),  # What was name
                    'price': color.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                    'multi allowed': 'false',
                    'image': color.get('car_image', ''),
                    'swatch color': color.get('swatch_color', ''),
                    'is default': str(color.get('is_default', False)).lower()
                })
                rows.append(row)
    
    # 2. Packages - Equipment Collections
    if 'packages' in data_section and isinstance(data_section['packages'], dict):
        packages = data_section['packages']
        
        if 'equipment_collections' in packages and isinstance(packages['equipment_collections'], list):
            for pkg in packages['equipment_collections']:
                if isinstance(pkg, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Package',
                        'type': 'Equipment Collection',  # What was sub_category
                        'sub category': pkg.get('name', ''),  # What was name
                        'price': pkg.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': pkg.get('car_image', ''),
                        'swatch color': pkg.get('swatch_color', ''),
                        'is default': str(pkg.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Additional Packages
        if 'additional_packages' in packages and isinstance(packages['additional_packages'], list):
            for pkg in packages['additional_packages']:
                if isinstance(pkg, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Package',
                        'type': 'Additional Package',  # What was sub_category
                        'sub category': pkg.get('name', ''),  # What was name
                        'price': pkg.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': pkg.get('car_image', ''),
                        'swatch color': pkg.get('swatch_color', ''),
                        'is default': str(pkg.get('is_default', False)).lower()
                    })
                    rows.append(row)
    
    # 3. Powertrains - Engine
    if 'powertrains' in data_section and isinstance(data_section['powertrains'], dict):
        powertrains = data_section['powertrains']
        
        if 'engine' in powertrains and isinstance(powertrains['engine'], list):
            for engine in powertrains['engine']:
                if isinstance(engine, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Powertrain',
                        'type': 'Engine',  # What was sub_category
                        'sub category': engine.get('name', ''),  # What was name
                        'price': engine.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': engine.get('car_image', ''),
                        'swatch color': engine.get('swatch_color', ''),
                        'is default': str(engine.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Drive
        if 'drive' in powertrains and isinstance(powertrains['drive'], list):
            for drive in powertrains['drive']:
                if isinstance(drive, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Powertrain',
                        'type': 'Drive Type',  # What was sub_category
                        'sub category': drive.get('name', ''),  # What was name
                        'price': drive.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': drive.get('car_image', ''),
                        'swatch color': drive.get('swatch_color', ''),
                        'is default': str(drive.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Transmission
        if 'transmission' in powertrains and isinstance(powertrains['transmission'], list):
            for trans in powertrains['transmission']:
                if isinstance(trans, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Powertrain',
                        'type': 'Transmission',  # What was sub_category
                        'sub category': trans.get('name', ''),  # What was name
                        'price': trans.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': trans.get('car_image', ''),
                        'swatch color': trans.get('swatch_color', ''),
                        'is default': str(trans.get('is_default', False)).lower()
                    })
                    rows.append(row)
    
    # 4. Exterior - Wheels
    if 'exterior' in data_section and isinstance(data_section['exterior'], dict):
        if 'wheels' in data_section['exterior'] and isinstance(data_section['exterior']['wheels'], list):
            for wheel in data_section['exterior']['wheels']:
                if isinstance(wheel, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Exterior',
                        'type': 'Wheels',  # What was sub_category
                        'sub category': wheel.get('name', ''),  # What was name
                        'price': wheel.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': wheel.get('car_image', ''),
                        'swatch color': wheel.get('swatch_color', ''),
                        'is default': str(wheel.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Other exterior options
        if 'exterior_options' in data_section['exterior'] and isinstance(data_section['exterior']['exterior_options'], list):
            for option in data_section['exterior']['exterior_options']:
                if isinstance(option, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Exterior',
                        'type': 'Exterior Option',  # What was sub_category
                        'sub category': option.get('name', ''),  # What was name
                        'price': option.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': option.get('car_image', ''),
                        'swatch color': option.get('swatch_color', ''),
                        'is default': str(option.get('is_default', False)).lower()
                    })
                    rows.append(row)
    
    # 5. Interior Colors
    if 'interior' in data_section and isinstance(data_section['interior'], dict):
        if 'color' in data_section['interior'] and isinstance(data_section['interior']['color'], list):
            for color in data_section['interior']['color']:
                if isinstance(color, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Interior',
                        'type': 'Interior Color',  # What was sub_category
                        'sub category': color.get('name', ''),  # What was name
                        'price': color.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': color.get('car_image', ''),
                        'swatch color': color.get('swatch_color', ''),
                        'is default': str(color.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Interior Options
        if 'interior_options' in data_section['interior'] and isinstance(data_section['interior']['interior_options'], list):
            for option in data_section['interior']['interior_options']:
                if isinstance(option, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Interior',
                        'type': 'Interior Option',  # What was sub_category
                        'sub category': option.get('name', ''),  # What was name
                        'price': option.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': option.get('car_image', ''),
                        'swatch color': option.get('swatch_color', ''),
                        'is default': str(option.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Technology
        if 'technology' in data_section['interior'] and isinstance(data_section['interior']['technology'], list):
            for tech in data_section['interior']['technology']:
                if isinstance(tech, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Technology',
                        'type': 'Tech Feature',  # What was sub_category
                        'sub category': tech.get('name', ''),  # What was name
                        'price': tech.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': tech.get('car_image', ''),
                        'swatch color': tech.get('swatch_color', ''),
                        'is default': str(tech.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        # Entertainment/Audio
        if 'entertainment' in data_section['interior'] and isinstance(data_section['interior']['entertainment'], list):
            for audio in data_section['interior']['entertainment']:
                if isinstance(audio, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Technology',
                        'type': 'Audio System',  # What was sub_category
                        'sub category': audio.get('name', ''),  # What was name
                        'price': audio.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': audio.get('car_image', ''),
                        'swatch color': audio.get('swatch_color', ''),
                        'is default': str(audio.get('is_default', False)).lower()
                    })
                    rows.append(row)
        
        if 'audio_upgrade' in data_section['interior'] and isinstance(data_section['interior']['audio_upgrade'], list):
            for audio in data_section['interior']['audio_upgrade']:
                if isinstance(audio, dict):
                    row = base_info.copy()
                    row.update({
                        'category': 'Technology',
                        'type': 'Audio System',  # What was sub_category
                        'sub category': audio.get('name', ''),  # What was name
                        'price': audio.get('price', '').replace('$', '').replace(',', '').replace('INCLUDED', '0'),
                        'multi allowed': 'false',
                        'image': audio.get('car_image', ''),
                        'swatch color': audio.get('swatch_color', ''),
                        'is default': str(audio.get('is_default', False)).lower()
                    })
                    rows.append(row)
    
    # 6. Accessories
    if 'accessories' in data_section and isinstance(data_section['accessories'], dict):
        for main_category, subcategories in data_section['accessories'].items():
            if isinstance(subcategories, dict):
                for subcat, items in subcategories.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                row = base_info.copy()
                                row.update({
                                    'category': 'Accessory',
                                    'type': f"{main_category} - {subcat}",  # What was sub_category
                                    'sub category': item.get('name', ''),  # What was name
                                    'price': item.get('price', '').replace('$', '').replace(',', ''),
                                    'multi allowed': 'false',
                                    'image': item.get('car_image', ''),
                                    'swatch color': item.get('swatch_color', ''),
                                    'is default': str(item.get('is_default', False)).lower()
                                })
                                rows.append(row)
    
    return rows

def json_to_csv_single_file(json_file, output_file='lincoln_complete.csv'):
    """
    Converts JSON to a single CSV file with all requested columns
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {json_file} not found in current directory!")
        print(f"Current directory: {os.getcwd()}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return
    
    # Define the exact columns we want in the order specified
    # NOTE: 'name' column has been removed
    columns = [
        'car',
        'model',
        'type',
        'category',
        'sub category',
        'price',
        'multi allowed',
        'base price of car',
        'description',
        'image',
        'swatch color',
        'is default'
    ]
    
    # Extract all rows
    all_rows = []
    
    for vehicle_idx, vehicle in enumerate(data):
        for trim_idx, trim in enumerate(vehicle.get('trims', [])):
            if 'data' in trim and trim['data']:
                rows = extract_car_info(vehicle, trim, trim['data'])
                all_rows.extend(rows)
    
    # Write to single CSV file with specified columns
    if all_rows:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, restval='')
            writer.writeheader()
            writer.writerows(all_rows)
        
        print(f"✅ Conversion complete!")
        print(f"📁 Output file: {output_file}")
        print(f"📊 Total rows: {len(all_rows)}")
        print(f"📈 Columns: {', '.join(columns)}")
        print(f"📍 Location: {os.getcwd()}")
        
        # Show sample of data
        print("\n📋 Sample of first 3 rows:")
        for i, row in enumerate(all_rows[:3]):
            print(f"  Row {i+1}: {row['car']} - {row['category']} - Type: {row['type']} - Sub: {row['sub category']} - Price: ${row['price']} - Base: ${row['base price of car']}")
    else:
        print("❌ No data found to convert!")

def main():
    json_file = 'lincoln.json'
    output_file = 'lincoln_complete.csv'
    
    # Check if file exists
    if not os.path.exists(json_file):
        print(f"❌ Error: {json_file} not found in current directory!")
        print(f"Current directory: {os.getcwd()}")
        print("\nPlease make sure lincoln.json is in this folder.")
        return
    
    print(f"📁 Found {json_file}")
    print("🔄 Converting to single CSV file with all requested columns...\n")
    
    json_to_csv_single_file(json_file, output_file)

if __name__ == "__main__":
    main()