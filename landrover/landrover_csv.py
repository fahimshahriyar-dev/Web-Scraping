import json
import csv

# --- Per-trim exterior color reorder config ---
TRIM_COLOR_REORDER = {
    "718 Cayman GT4 RS": [1, 9, 0, 2, 3, 4, 5, 6, 7, 8],
    "718 Spyder RS":     [2, 0, 1, 3, 4, 5, 6, 7, 8, 9],
}

# Keys that are considered "exterior colors" for reordering
EXTERIOR_COLOR_KEYS = {"exterior_colors", "exterior colors", "exteriorcolors", "colors"}

# Subsection keys inside "exterior" that are NOT actual car options
# (junk scraped from the Range Rover Sport page navigation etc.)
JUNK_FILTER_KEYS = {"exterior_packs"}

# Known valid subsection keys — anything not in this list inside a nested dict
# will still be processed, but exterior_packs specifically is noisy
VALID_ITEM_KEYS = {
    "name", "price", "car_image", "swatch_image", "interior_car_image",
    "specs", "is_selected", "is_recommended", "option_id", "description",
    "category", "material", "type", "features"
}

# Junk names to skip (scraped navigation/UI artifacts)
JUNK_NAMES = {
    "VEHICLES", "OWNERS", "EXPLORE", "SHOP NOW", "logo", "picture", "image",
    "BUILDS", "icon", "SUPPORT", "INSPIRATION", "MODEL", "PROPULSION",
    "EXTERIOR", "WHEELS", "INTERIOR", "PACKS", "OPTIONS", "ACCESSORIES",
    "SUMMARY", "SAVE BUILD", "MAXIMISE", "Copy", "ADD", "EDIT",
    "icon-contact-and-help", "icon-test-id", "feature-block-row-title-icon",
    "cplayerwrapper", "More Information", "Recommended", "feature_more_info",
    "GO TO PREVIOUS SLIDE", "GO TO NEXT SLIDE", "COOKIE AND PRIVACY POLICY",
    "PERSONALISED PDF", "LOCATE A RETAILER", "Your vehicle link",
    "infobar-calc-zone-id", "Standard Interior", "Your Vehicle",
    "Configuration", "Standard features", "Technical specifications",
    "Compare models", "Next Steps", "PACKS",
}

# Junk name patterns (startswith)
JUNK_PREFIXES = (
    "N-", "A-", "VPLK", "VPLX", "VPLL", "VPLE", "VPLR", "VPLZ", "VPLV",
    "VPLG", "VPLP", "VPLC", "VPLS", "VPL", "stage-", "cta-icon", "share-zone",
    "configurationCell", "saved-builds",
)


def is_junk_name(name: str) -> bool:
    if not name or not name.strip():
        return True
    n = name.strip()
    if n in JUNK_NAMES:
        return True
    for prefix in JUNK_PREFIXES:
        if n.startswith(prefix):
            return True
    # Pagination artifacts like "2 / 7", "6,4 (6,1)"
    if n.count("/") == 1 and all(part.strip().isdigit() for part in n.split("/")):
        return True
    return False


def reorder_exterior_colors(items, trim_name):
    order = TRIM_COLOR_REORDER.get(trim_name)
    if not order or not items:
        return items
    reordered = []
    used = set()
    for idx in order:
        if idx < len(items):
            reordered.append(items[idx])
            used.add(idx)
    for i, item in enumerate(items):
        if i not in used:
            reordered.append(item)
    return reordered


def is_exterior_color_key(key):
    return key.strip().lower() in EXTERIOR_COLOR_KEYS


def get_image(item: dict) -> str:
    """Pick the best available image URL from an item."""
    return (
        item.get("car_image") or
        item.get("swatch_image") or
        item.get("interior_car_image") or
        ""
    )


def get_thumb(item: dict) -> str:
    """Pick swatch/thumb image (prefers swatch_image for color swatches)."""
    return (
        item.get("swatch_image") or
        item.get("car_image") or
        item.get("interior_car_image") or
        ""
    )


def make_row(car_name, trim_name, section_type, category, item: dict) -> dict:
    """Build a single CSV row from an item dict."""
    name = item.get("name", "").strip()
    if is_junk_name(name):
        return None

    is_selected = item.get("is_selected", "")
    if isinstance(is_selected, bool):
        is_selected = "yes" if is_selected else "no"

    is_recommended = item.get("is_recommended", "")
    if isinstance(is_recommended, bool):
        is_recommended = "yes" if is_recommended else ""

    specs = item.get("specs", {})
    fuel_type = specs.get("fuel_type", "") if isinstance(specs, dict) else ""

    return {
        "car":               car_name,
        "model":             trim_name,
        "base price of car": "$0",
        "type":              section_type,
        "category":          category,
        "sub category":      name,
        "fuel type":         fuel_type,
        "multi allowed":     "",
        "description":       item.get("description", ""),
        "price":             item.get("price", "$0") or "$0",
        "car image":         item.get("car_image", ""),
        "currently selected": is_selected,
        "image":             get_image(item),
        "swatch image":      get_thumb(item),
        "is recommended":    is_recommended,
        "option_id":         item.get("option_id", ""),
        "material":          item.get("material", ""),
    }


def extract_items(configurations: dict, car_name: str, trim_name: str) -> list:
    rows = []

    for section_key, section_value in configurations.items():

        # ── Flat list section (e.g. engine, packs, options, accessories) ──
        if isinstance(section_value, list):
            items = section_value
            if is_exterior_color_key(section_key):
                items = reorder_exterior_colors(items, trim_name)

            for item in items:
                if not isinstance(item, dict):
                    continue
                row = make_row(car_name, trim_name, section_key, section_key, item)
                if row:
                    rows.append(row)

        # ── Dict section (e.g. exterior, wheels, interior) ──
        elif isinstance(section_value, dict):
            for subsection_key, subsection_value in section_value.items():

                # Skip known junk subsections
                if subsection_key in JUNK_FILTER_KEYS:
                    continue

                if not isinstance(subsection_value, list):
                    continue

                items = subsection_value
                if is_exterior_color_key(section_key) or is_exterior_color_key(subsection_key):
                    items = reorder_exterior_colors(items, trim_name)

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    row = make_row(
                        car_name, trim_name,
                        section_type=section_key,
                        category=subsection_key,
                        item=item
                    )
                    if row:
                        rows.append(row)

    return rows


def convert_landrover_json_to_csv(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fieldnames = [
        "car", "model", "base price of car", "type", "category",
        "sub category", "fuel type", "multi allowed", "description",
        "price", "car image", "currently selected", "image",
        "swatch image", "is recommended", "option_id", "material",
    ]

    all_rows = []

    for car in data:
        car_name = car.get("name", "")

        for trim in car.get("trims", []):
            trim_name = trim.get("name", "")
            configurations = trim.get("configurations", {})

            if not isinstance(configurations, dict):
                print(f"  ⚠ Skipping trim '{trim_name}' — configurations is not a dict")
                continue

            rows = extract_items(configurations, car_name, trim_name)
            all_rows.extend(rows)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ Done! {len(all_rows)} rows written to '{output_file}'")


if __name__ == "__main__":
    convert_landrover_json_to_csv("landrover.json", "landrover.csv")