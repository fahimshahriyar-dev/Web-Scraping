import json
import csv
import random

# --- Per-trim exterior color reorder config ---
TRIM_COLOR_REORDER = {
    "718 Cayman GT4 RS": [1, 9, 0, 2, 3, 4, 5, 6, 7, 8],
    "718 Spyder RS":     [2, 0, 1, 3, 4, 5, 6, 7, 8, 9],
}

# Expanded exterior color key patterns
EXTERIOR_COLOR_PATTERNS = [
    "exterior_colors", 
    "exterior colors", 
    "exteriorcolors",
    "exterior",
    "paint",
    "body_color",
    "body_colors"
]

# Wheels section patterns
WHEELS_PATTERNS = [
    "wheels",
    "wheel",
    "rims",
    "wheel_styles",
    "wheel styles"
]

def is_exterior_color_section(key):
    """Check if a section key relates to exterior colors."""
    key_lower = key.strip().lower()
    return any(pattern in key_lower for pattern in EXTERIOR_COLOR_PATTERNS)

def is_wheels_section(key):
    """Check if a section key relates to wheels."""
    key_lower = key.strip().lower()
    return any(pattern in key_lower for pattern in WHEELS_PATTERNS)

def get_safe_price(price_value):
    """Extract price safely. Returns price string or '$0'."""
    if price_value is None:
        return "$0"
    
    price_str = str(price_value).strip()
    
    if not price_str or price_str == "0" or price_str == "$0" or price_str == "":
        return "$0"
    
    if price_str.startswith("$"):
        return price_str
    
    return f"${price_str}"

def reorder_exterior_colors_with_random_first(items, trim_name):
    """
    Reorder exterior color items based on per-trim config,
    but randomly select one color from indices 1-10 to place first.
    """
    if not items:
        return items
    
    # Get the per-trim reorder config if it exists
    order = TRIM_COLOR_REORDER.get(trim_name)
    
    # If we have a specific order config, use it as base
    if order:
        reordered = []
        used_indices = set()
        
        for idx in order:
            if idx < len(items):
                reordered.append(items[idx])
                used_indices.add(idx)
        
        for i, item in enumerate(items):
            if i not in used_indices:
                reordered.append(item)
    else:
        # No specific config, keep original order
        reordered = items.copy()
    
    # Now randomly select a color from index 1 to min(10, len(reordered)-1)
    # and move it to the first position
    if len(reordered) > 1:
        # Determine the range for random selection (1 to 10, but limited by list length)
        max_index = min(10, len(reordered) - 1)
        
        if max_index >= 1:
            # Select a random index between 1 and max_index
            random_index = random.randint(1, max_index)
            
            # Remove the randomly selected item and insert it at position 0
            selected_item = reordered.pop(random_index)
            reordered.insert(0, selected_item)
    
    return reordered

def order_sections(categories, trim_name):
    """
    Reorder sections so that exterior_colors comes first,
    then wheels, then all other sections in their original order.
    """
    ordered_sections = []
    
    # Separate sections into three categories
    exterior_sections = []
    wheels_sections = []
    other_sections = []
    
    for section_key, section_value in categories.items():
        if is_exterior_color_section(section_key):
            exterior_sections.append((section_key, section_value))
        elif is_wheels_section(section_key):
            wheels_sections.append((section_key, section_value))
        else:
            other_sections.append((section_key, section_value))
    
    # Combine in desired order: exterior first, then wheels, then others
    ordered_sections.extend(exterior_sections)
    ordered_sections.extend(wheels_sections)
    ordered_sections.extend(other_sections)
    
    return ordered_sections

def extract_items(categories, car_name, trim_name, base_price):
    """Extract all items from categories with proper section ordering."""
    rows = []
    
    # Get ordered sections
    ordered_sections = order_sections(categories, trim_name)

    def item_row(car_name, trim_name, base_price, type_val, category_val, item):
        raw_price = item.get("price", "$0")
        safe_price = get_safe_price(raw_price)
        
        return {
            "car": car_name,
            "model": trim_name,
            "base price of car": base_price,
            "type": type_val,
            "category": category_val,
            "sub category": item.get("name", ""),
            "multi allowed": "",
            "description": "",
            "price": safe_price,
            "car image": item.get("car_image", ""),
            "currently selected": "yes" if item.get("currently_selected") else "no",
            "image": item.get("car_image", "") or item.get("car_image", ""),
        }

    # Process sections in the new order
    for section_key, section_value in ordered_sections:
        if isinstance(section_value, list):
            items = section_value
            if is_exterior_color_section(section_key):
                items = reorder_exterior_colors_with_random_first(items, trim_name)
            for item in items:
                rows.append(item_row(car_name, trim_name, base_price, section_key, section_key, item))

        elif isinstance(section_value, dict):
            # For nested structures, we need to process subsections too
            for subsection_key, subsection_value in section_value.items():
                if isinstance(subsection_value, list):
                    items = subsection_value
                    if is_exterior_color_section(section_key) or is_exterior_color_section(subsection_key):
                        items = reorder_exterior_colors_with_random_first(items, trim_name)
                    for item in items:
                        rows.append(item_row(car_name, trim_name, base_price, section_key, subsection_key, item))

    return rows

def get_car_image_from_exterior_colors(categories):
    """
    Extract the car image from the exterior colors section only.
    Returns the first available car_image from exterior colors.
    """
    def search_for_image(items):
        """Search through items for an image."""
        for item in items:
            # First try to get car_image
            img = item.get("car_image", "")
            if img:
                return img
        return ""

    # Search through all categories
    for section_key, section_value in categories.items():
        # Check if this is an exterior color section
        if is_exterior_color_section(section_key):
            # Direct list of items
            if isinstance(section_value, list):
                img = search_for_image(section_value)
                if img:
                    return img
            
            # Nested structure
            elif isinstance(section_value, dict):
                for subsection_key, subsection_value in section_value.items():
                    if isinstance(subsection_value, list):
                        # Check if subsection is also exterior color related
                        if is_exterior_color_section(subsection_key) or is_exterior_color_section(section_key):
                            img = search_for_image(subsection_value)
                            if img:
                                return img
    
    # If no exterior color images found, return empty string
    return ""

def convert_porsche_json_to_csv(input_file, output_file):
    """Convert Porsche JSON configuration data to CSV format."""
    print(f"Reading JSON from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fieldnames = [
        "car", "model", "base price of car", "type", "category",
        "sub category", "multi allowed", "description", "car model image",
        "trim image", "price", "car image", "currently selected", "image",
    ]

    all_rows = []
    total_items = 0

    for car in data:
        car_name = car.get("name", "")
        print(f"Processing car: {car_name}")

        for trim in car.get("trims", []):
            trim_name = trim.get("name", "")
            trim_base_price = get_safe_price(trim.get("base_price", "$0"))
            print(f"  Processing trim: {trim_name} (Base price: {trim_base_price})")

            for config in trim.get("configurations", []):
                categories = config.get("categories", {})
                
                # Get the car image from exterior colors section ONLY
                exterior_car_image = get_car_image_from_exterior_colors(categories)
                
                if exterior_car_image:
                    print(f"    Found exterior car image: {exterior_car_image[:100]}...")
                else:
                    print(f"    Warning: No exterior color images found for {trim_name}")
                
                # Extract all items with proper section ordering
                rows = extract_items(categories, car_name, trim_name, trim_base_price)
                
                # Set the same image for both car model image and trim image
                for row in rows:
                    row["car model image"] = exterior_car_image
                    row["trim image"] = exterior_car_image
                
                all_rows.extend(rows)
                total_items += len(rows)
                print(f"    Added {len(rows)} items from configuration")

    print(f"Writing {total_items} rows to {output_file}...")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Done! {len(all_rows)} rows written to {output_file}")


if __name__ == "__main__":
    input_json_file = "porsche_data.json"
    output_csv_file = "porsche_output.csv"
    
    try:
        convert_porsche_json_to_csv(input_json_file, output_csv_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_json_file}")
        print("Please make sure the file exists in the current directory.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_json_file}")
        print(f"Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")