import json
import csv

# --- Per-trim exterior color reorder config ---
# Key: trim name (exact match)
# Value: list of original indices in the desired new order
# Any indices out of range are safely skipped.
# Trims not listed here will keep their original order.
TRIM_COLOR_REORDER = {
    "718 Cayman GT4 RS": [1, 9, 0, 2, 3, 4, 5, 6, 7, 8],
    "718 Spyder RS":     [2, 0, 1, 3, 4, 5, 6, 7, 8, 9],
    # Add more trims here as needed...
}

EXTERIOR_COLOR_KEYS = {"exterior_colors", "exterior colors", "exteriorcolors"}


def reorder_exterior_colors(items, trim_name):
    """
    Reorder exterior color items based on the per-trim config.
    Falls back to original order if trim not in config.
    """
    order = TRIM_COLOR_REORDER.get(trim_name)
    if not order or not items:
        return items

    reordered = []
    used_indices = set()

    for idx in order:
        if idx < len(items):
            reordered.append(items[idx])
            used_indices.add(idx)

    # Append any remaining items not referenced in the reorder list
    for i, item in enumerate(items):
        if i not in used_indices:
            reordered.append(item)

    return reordered


def is_exterior_color_key(key):
    return key.strip().lower() in EXTERIOR_COLOR_KEYS


def extract_items(categories, car_name, car_base_image, trim_name, trim_base_image):
    rows = []

    for section_key, section_value in categories.items():
        # Section is a flat list (no subsections)
        if isinstance(section_value, list):
            items = section_value
            if is_exterior_color_key(section_key):
                items = reorder_exterior_colors(items, trim_name)

            for item in items:
                rows.append({
                    "car": car_name,
                    "model": trim_name,
                    "base price of car": "$0",
                    "type": section_key,
                    "category": section_key,
                    "sub category": item.get("name", ""),
                    "multi allowed": "",
                    "description": "",
                    "price": "$0",
                    "car image": item.get("car_image", ""),
                    "currently selected": "no",
                    "image": item.get("car_image", "") or item.get("swatch_image", ""),
                })

        # Section is a dict (has subsections)
        elif isinstance(section_value, dict):
            for subsection_key, subsection_value in section_value.items():
                if isinstance(subsection_value, list):
                    items = subsection_value
                    if is_exterior_color_key(section_key) or is_exterior_color_key(subsection_key):
                        items = reorder_exterior_colors(items, trim_name)

                    for item in items:
                        rows.append({
                            "car": car_name,
                            "model": trim_name,
                            "base price of car": "$0",
                            "type": section_key,
                            "category": subsection_key,
                            "sub category": item.get("name", ""),
                            "multi allowed": "",
                            "description": "",
                            "price": "$0",
                            "car image": item.get("car_image", ""),
                            "currently selected": "no",
                            "image": item.get("swatch_image", ""),
                        })

    return rows


def convert_porsche_json_to_csv(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fieldnames = [
        "car", "model", "base price of car", "type", "category",
        "sub category", "multi allowed", "description", "car model image",
        "trim image", "price", "car image", "currently selected", "image",
    ]

    all_rows = []

    for car in data:
        car_name = car.get("name", "")
        car_base_image = car.get("base_image", "")

        for trim in car.get("trims", []):
            trim_name = trim.get("name", "")
            trim_base_image = trim.get("base_image", "")

            for config in trim.get("configurations", []):
                categories = config.get("categories", {})
                rows = extract_items(categories, car_name, car_base_image, trim_name, trim_base_image)
                all_rows.extend(rows)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Done! {len(all_rows)} rows written to {output_file}")


if __name__ == "__main__":
    convert_porsche_json_to_csv("porsche.json", "porsche_output.csv")