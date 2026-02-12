import json
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class FerrariCompleteScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized") 
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(90)
        self.wait = WebDriverWait(self.driver, 30)
        
    def close(self):
        self.driver.quit()

    def handle_cookies(self):
        """Handle cookie banners"""
        try:
            time.sleep(2)
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or @id='onetrust-accept-btn-handler' or @id='accept-recommended-btn-handler']"))
            )
            cookie_btn.click()
            print("  ✓ Cookie banner accepted")
            time.sleep(2)
        except:
            print("  - No cookie banner")

    def handle_apply_popup(self):
        """Handle apply button popup - handles both simple popups and checkbox popups"""
        try:
            # Wait for popup to appear
            apply_buttons = WebDriverWait(self.driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".action-button-text"))
            )
            
            # Check if there's a checkbox that needs to be clicked first
            try:
                checkbox = self.driver.find_element(By.CSS_SELECTOR, ".check-container")
                # Check if checkbox is not already selected
                checkbox_parent = checkbox.find_element(By.XPATH, "..")
                if "opt-selected" not in checkbox_parent.get_attribute("class"):
                    checkbox.click()
                    print("  ✓ Checkbox clicked in popup")
                    time.sleep(0.5)
            except:
                # No checkbox found, continue to apply button
                pass
            
            # Now click the Apply button (second button)
            if len(apply_buttons) >= 2:
                apply_buttons[1].click()  # Click the second button (Apply)
                print("  ✓ Apply popup clicked")
                time.sleep(1)
                return True
            elif len(apply_buttons) == 1:
                apply_buttons[0].click()
                print("  ✓ Apply popup clicked (single button)")
                time.sleep(1)
                return True
        except:
            return False

    def safe_click(self, element):
        """Safely click an element"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)
            element.click()
            time.sleep(0.5)
        except:
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(0.5)

    def wait_for_loading(self):
        """Wait for loading to complete"""
        time.sleep(2)
        try:
            WebDriverWait(self.driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".loading-indicator-spinner:not([style*='display: none'])"))
            )
        except:
            pass
        time.sleep(1)

    def wait_for_image_render(self, timeout=10):
        """Wait for car image to fully render with change detection"""
        print("      ⏳ Waiting for image to render...", end="", flush=True)
        
        try:
            # Get initial image
            initial_image = None
            for _ in range(3):
                initial_image = self.get_current_car_image()
                if initial_image:
                    break
                time.sleep(0.5)
            
            if not initial_image:
                print(" (no initial image)")
                time.sleep(3)
                return
            
            # Wait for image to change and stabilize
            stable_count = 0
            last_image = initial_image
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                current_image = self.get_current_car_image()
                
                if current_image and current_image != initial_image:
                    # Image has changed
                    if current_image == last_image:
                        stable_count += 1
                        if stable_count >= 2:  # Image stable for 1 second
                            print(" ✓ Rendered")
                            time.sleep(3)  # Additional 3 second wait
                            return
                    else:
                        stable_count = 0
                    last_image = current_image
            
            # Timeout reached, use fallback
            print(" (timeout, using fallback)")
            time.sleep(3)
            
        except Exception as e:
            print(f" (error: {e})")
            time.sleep(3)

    def get_current_car_image(self):
        """Get the current car rendering image"""
        try:
            render_container = self.driver.find_element(By.CSS_SELECTOR, "#render-container")
            style = render_container.get_attribute("style")
            
            if "background-image: url(" in style:
                url_start = style.find('url("') + 5
                url_end = style.find('")', url_start)
                return style[url_start:url_end]
        except:
            pass
        return None

    def click_tab(self, tab_name):
        """Click on main tabs"""
        try:
            time.sleep(1)
            tab_headers = self.driver.find_elements(By.CSS_SELECTOR, ".tab-group-header-section")
            
            for tab in tab_headers:
                try:
                    label = tab.find_element(By.CLASS_NAME, "tab-group-header-section-label")
                    if tab_name.lower() in label.text.strip().lower():
                        print(f"\n  ✓ Clicking {tab_name} tab")
                        self.safe_click(tab)
                        self.wait_for_loading()
                        time.sleep(2)
                        return True
                except:
                    continue
            
            print(f"  ✗ Tab '{tab_name}' not found")
            return False
            
        except Exception as e:
            print(f"  ✗ Error clicking tab: {e}")
            return False

    def click_category_item(self, category_keywords):
        """Click on a category item"""
        try:
            time.sleep(1)
            
            # Check for apply popup first
            self.handle_apply_popup()
            
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".item-container"))
            )
            
            item_containers = self.driver.find_elements(By.CSS_SELECTOR, ".item-container")
            print(f"    Debug: Found {len(item_containers)} item containers")
            
            # First, list all available categories
            available_categories = []
            for container in item_containers:
                try:
                    title_elem = container.find_element(By.CSS_SELECTOR, ".title-section h2 span")
                    title_text = title_elem.text.strip()
                    available_categories.append(title_text)
                except:
                    continue
            
            print(f"    Available categories: {available_categories}")
            
            # Now try to match
            for container in item_containers:
                try:
                    title_elem = container.find_element(By.CSS_SELECTOR, ".title-section h2 span")
                    title_text = title_elem.text.strip().lower()
                    
                    for keyword in category_keywords:
                        if keyword.lower() in title_text:
                            print(f"    ✓ Found & clicking: {title_elem.text}")
                            self.safe_click(container)
                            self.wait_for_loading()
                            time.sleep(2)
                            
                            # Check for apply popup after clicking
                            self.handle_apply_popup()
                            
                            return True
                except Exception as e:
                    continue
            
            print(f"    ✗ Category with keywords {category_keywords} not found")
            return False
            
        except Exception as e:
            print(f"    ✗ Error clicking category: {e}")
            return False

    def go_back_to_main_view(self):
        """Go back to category list"""
        try:
            # Check for apply popup first
            self.handle_apply_popup()
            
            back_btn = self.driver.find_element(By.CSS_SELECTOR, ".ferrari-arrow-down")
            self.safe_click(back_btn)
            print("    ← Back")
            time.sleep(2)
            
            # Check for apply popup after going back
            self.handle_apply_popup()
            
            return True
        except:
            return False

    def convert_image_url(self, img_src):
        """Convert relative URLs"""
        if not img_src or "no-color" in img_src:
            return None
        if img_src.startswith("../"):
            return img_src.replace("../../../../../", "https://carconfigurator.ferrari.com/")
        elif img_src.startswith("/"):
            return "https://carconfigurator.ferrari.com" + img_src
        return img_src

    def scrape_color_palette_options(self):
        """Scrape color palette options"""
        options = []
        try:
            # Check for apply popup first
            self.handle_apply_popup()
            
            palette_containers = self.driver.find_elements(By.CSS_SELECTOR, "rt-color-palette .list-opt-container")
            
            for palette in palette_containers:
                try:
                    palette_name = palette.find_element(By.CSS_SELECTOR, ".palette-name span").text.strip()
                    color_options = palette.find_elements(By.CSS_SELECTOR, ".image-opt-container")
                    
                    for color_opt in color_options:
                        try:
                            img = color_opt.find_element(By.TAG_NAME, "img")
                            
                            # Click to update car image
                            self.safe_click(color_opt)
                            
                            # Check for apply popup after clicking
                            self.handle_apply_popup()
                            
                            # Wait for image to render fully
                            self.wait_for_image_render()
                            
                            car_image = self.get_current_car_image()
                            
                            options.append({
                                'name': img.get_attribute("alt"),
                                'price': "$0" if palette_name.upper() in ["STANDARD", "CLASSIC"] else "Additional Cost",
                                'swath_image': self.convert_image_url(img.get_attribute("src")),
                                'car_image': car_image,
                                'selected': "opt-selected" in color_opt.get_attribute("class")
                            })
                        except:
                            continue
                except:
                    continue
            
            print(f"      → {len(options)} colors")
            return options
        except:
            return []

    def scrape_text_image_options(self):
        """Scrape text-image options"""
        options = []
        try:
            # Check for apply popup first
            self.handle_apply_popup()
            
            containers = self.driver.find_elements(By.CSS_SELECTOR, "rt-text-image .image-opt-container")
            
            for container in containers:
                try:
                    img = container.find_element(By.TAG_NAME, "img")
                    self.safe_click(container)
                    
                    # Check for apply popup after clicking
                    self.handle_apply_popup()
                    
                    # Wait for image to render fully
                    self.wait_for_image_render()
                    
                    car_image = self.get_current_car_image()
                    
                    options.append({
                        'name': img.get_attribute("alt"),
                        'price': "$0",
                        'swath_image': self.convert_image_url(img.get_attribute("src")),
                        'car_image': car_image,
                        'selected': "opt-selected" in container.get_attribute("class")
                    })
                except:
                    continue
            
            # Check for checkboxes
            try:
                checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "rt-multiple-cameras .checkbox-opt-container")
                for checkbox in checkboxes:
                    try:
                        text = checkbox.find_element(By.CSS_SELECTOR, ".selection-text-container span").text
                        check = checkbox.find_element(By.CSS_SELECTOR, ".check-container")
                        
                        self.safe_click(checkbox)
                        
                        # Check for apply popup after clicking
                        self.handle_apply_popup()
                        
                        # Wait for image to render fully
                        self.wait_for_image_render()
                        
                        car_image = self.get_current_car_image()
                        
                        options.append({
                            'name': text,
                            'price': "Additional Cost",
                            'swath_image': None,
                            'car_image': car_image,
                            'selected': "opt-selected-multiple" in check.get_attribute("class")
                        })
                    except:
                        continue
            except:
                pass
            
            print(f"      → {len(options)} options")
            return options
        except:
            return []

    def scrape_single_selection_options(self):
        """Scrape radio options"""
        options = []
        try:
            # Check for apply popup first
            self.handle_apply_popup()
            
            containers = self.driver.find_elements(By.CSS_SELECTOR, "rt-single-selection .checkbox-opt-container")
            
            for container in containers:
                try:
                    text = container.find_element(By.CSS_SELECTOR, ".selection-text-container span").text
                    self.safe_click(container)
                    
                    # Check for apply popup after clicking
                    self.handle_apply_popup()
                    
                    # Wait for image to render fully
                    self.wait_for_image_render()
                    
                    car_image = self.get_current_car_image()
                    
                    try:
                        circle = container.find_element(By.CSS_SELECTOR, ".circle-inner")
                        selected = "opt-selected-single" in circle.get_attribute("class")
                    except:
                        selected = False
                    
                    options.append({
                        'name': text,
                        'price': "$0",
                        'swath_image': None,
                        'car_image': car_image,
                        'selected': selected
                    })
                except:
                    continue
            
            print(f"      → {len(options)} options")
            return options
        except:
            return []

    def scrape_multiple_selection_options(self):
        """Scrape checkbox options"""
        options = []
        try:
            # Check for apply popup first
            self.handle_apply_popup()
            
            containers = self.driver.find_elements(By.CSS_SELECTOR, "rt-checkbox-list .checkbox-opt-container")
            
            for container in containers:
                try:
                    text = container.find_element(By.CSS_SELECTOR, ".selection-text-container span").text
                    self.safe_click(container)
                    
                    # Check for apply popup after clicking
                    self.handle_apply_popup()
                    
                    # Wait for image to render fully
                    self.wait_for_image_render()
                    
                    car_image = self.get_current_car_image()
                    
                    try:
                        check = container.find_element(By.CSS_SELECTOR, ".check-container")
                        selected = "opt-selected-multiple" in check.get_attribute("class")
                    except:
                        selected = False
                    
                    options.append({
                        'name': text,
                        'price': "Additional Cost",
                        'swath_image': None,
                        'car_image': car_image,
                        'selected': selected
                    })
                except:
                    continue
            
            print(f"      → {len(options)} options")
            return options
        except:
            return []

    def scrape_current_view(self):
        """Scrape whatever is visible"""
        all_options = []
        
        colors = self.scrape_color_palette_options()
        if colors:
            all_options.extend(colors)
        
        text = self.scrape_text_image_options()
        if text:
            all_options.extend(text)
        
        single = self.scrape_single_selection_options()
        if single:
            all_options.extend(single)
        
        multi = self.scrape_multiple_selection_options()
        if multi:
            all_options.extend(multi)
        
        return all_options

    def scrape_section(self, section_name, categories):
        """Scrape a complete section"""
        print(f"\n{'='*60}")
        print(f"Section: {section_name}")
        print(f"{'='*60}")
        
        section_data = {}
        
        if not self.click_tab(section_name):
            return section_data
        
        time.sleep(2)
        
        for category_name, keywords in categories.items():
            print(f"\n  📁 Category: {category_name}")
            
            if not self.click_category_item(keywords):
                continue
            
            options = self.scrape_current_view()
            
            if options:
                section_data[category_name] = options
                print(f"    ✓ Saved {len(options)} options")
            else:
                print(f"    ! No options found")
            
            self.go_back_to_main_view()
            time.sleep(1)
        
        return section_data

    def scrape_car(self, url, car_name):
        """Scrape complete car"""
        print(f"\n{'#'*70}")
        print(f"# {car_name}")
        print(f"{'#'*70}")
        
        try:
            self.driver.get(url)
            print(f"  Loading...")
            time.sleep(10)
            
            self.handle_cookies()
            time.sleep(2)
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".config-panel, .configuration-container"))
            )
            print("  ✓ Page loaded")
            
            # Structure definition
            structure = {
                "Exterior": {
                    "Fiorano": ["Fiorano"],
                    "Paintwork": ["Paintwork", "Colour", "Color"],
                    "Livery": ["Livery"],
                    "Painted Details": ["Painted Details"],
                    "Rims": ["Rims", "Wheels"],
                    "Exhaust System": ["Exhaust", "Exhaust System"],
                    "Carbon Fibre Details": ["Carbon Fibre Details", "Carbon Fiber Details"],
                    "Tyres": ["Tyres", "Tires"],
                    "Calipers": ["Calipers", "Brake Calipers"],
                    "Logo & Details": ["Logo", "Details", "Ferrari Logo and Details"]
                },
                "Interior": {
                    "Main Interior Colour": ["Main Interior Colour", "Interior Colour"],
                    "Cockpit Inserts": ["Cockpit Inserts"],
                    "Lower and Upper Cockpit": ["Lower and Upper Cockpit", "Cockpit"],
                    "Carpets Colours": ["Carpets Colours", "Carpets"],
                    "Carpets Logo": ["Carpets Logo"],
                    "Steering Wheel": ["Steering Wheel"],
                    "Stitching": ["Stitching"],
                    "Headliner": ["Headliner", "Upper Area"],
                    "Carbon Fibre Details": ["Carbon Fibre Details"],
                    "Cockpit Details and Personalization Plate": ["Cockpit Details", "Personalization Plate"]
                },
                "Equipment": {
                    "Infotainment": ["Infotainment"],
                    "Driving": ["Driving"],
                    "Anti-Theft": ["Anti-Theft"],
                    "Safety": ["Safety"],
                    "Functionality": ["Functionality"],
                    "Luggage Sets": ["Luggage Sets"]
                }
            }
            
            car_data = {}
            for section, categories in structure.items():
                section_data = self.scrape_section(section, categories)
                car_data[section] = section_data
            
            # Summary
            print(f"\n{'='*70}")
            print(f"SUMMARY:")
            total = 0
            for section, data in car_data.items():
                count = sum(len(items) for items in data.values())
                total += count
                print(f"  {section}: {len(data)} categories, {count} options")
            print(f"  TOTAL: {total} options")
            print(f"{'='*70}")
            
            return car_data
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def scrape_all_cars(self, cars_data):
        """Scrape all cars"""
        results = {}
        
        for car_name, car_info in cars_data.items():
            car_result = {
                "base_image": car_info.get("base_image"),
                "trims": []
            }
            
            for trim in car_info.get("trims", []):
                full_name = f"{car_name} - {trim['name']}"
                
                try:
                    specs = self.scrape_car(trim["link"], full_name)
                    
                    trim_data = trim.copy()
                    trim_data["specs"] = specs
                    car_result["trims"].append(trim_data)
                    
                    results[car_name] = car_result
                    self.save_results(results, "ferrari_complete.json")
                    
                except Exception as e:
                    print(f"\n✗ Error: {e}")
                    continue
            
        return results

    def save_results(self, results, filename):
        """Save to JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            size = os.path.getsize(filename)
            print(f"\n💾 Saved: {filename} ({size:,} bytes)")
        except Exception as e:
            print(f"\n✗ Save error: {e}")

def get_ferrari_data():
    """Cars to scrape"""
    return {
        "GIALLO MODENA": {
                "base_image": "https://carconfigurator.ferrari.com/rt-assets/data/cars/296gtb/ui/preview-default.jpg",
                "trims": [
                    {
                        "name": "GIALLO MODENA",
                        "link": "https://carconfigurator.ferrari.com/en_EN/ferrari_car_configurator/296gtb/default/exterior?configuration=0ca146b92bd636a72b2e447982c36ecfff3a9392040cdee9999edfa2b4c9b12b&isStreaming=false",
                        "price": "$0",
                        "image": "https://carconfigurator.ferrari.com/f171/0ca146b92bd636a72b2e447982c36ecfff3a9392040cdee9999edfa2b4c9b12b-Blackroom-Day-beautyshot_ext_frontleft-2d.jpg"
                    }
                ]
        },
        "FERRARI 296 GTS": {
                "base_image": "https://carconfigurator.ferrari.com/rt-assets/data/cars/296gts/ui/preview-default.jpg",
                "trims": [
                    {
                        "name": "BLU CORSA",
                        "link": "https://carconfigurator.ferrari.com/en_EN/ferrari_car_configurator/296gts/default/exterior?configuration=3b9ca91e35cc4f95c7c0a3a58b1a129288c5ee02dbe92fd11f6271c0866e3c21&isStreaming=false",
                        "price": "$0",
                        "image": "https://carconfigurator.ferrari.com/f171spider/217a5257e3144ef53a2edfd9bf70ebac4a60b6ef68d8efb302e6b6a2a0422166-Blackroom-Day-beautyshot_ext_frontleft-2d.jpg"
                    }
                ]
        },
        "FERRARI F80": {
            "base_image": "https://carconfigurator.ferrari.com/rt-assets/data/cars/f80/ui/splashpage.jpg",
            "trims": [
                {
                    "name": "DEFAULT CONFIGURATION",
                    "link": "https://carconfigurator.ferrari.com/en_EN/ferrari_car_configurator/f80/default/exterior?configuration=691ba4b976378ce903ff4d4ea8239d353ba52931234ed727825423eb673254f8&isStreaming=false",
                    "price": "$0",
                    "image": "https://carconfigurator.ferrari.com/f250/ed189c1967ceb105ef58743004d4fcc8cffb573bce0a53e28961428c3d90bff7-Blackroom-Day-beautyshot_ext_frontleft-2d.jpg"
                }
            ]
        }
    }

def main():
    print("\n" + "🏎️ "*35)
    print("FERRARI CONFIGURATOR SCRAPER")
    print("🏎️ "*35 + "\n")
    
    cars_data = get_ferrari_data()
    scraper = FerrariCompleteScraper()
    
    try:
        results = scraper.scrape_all_cars(cars_data)
        scraper.save_results(results, "ferrari_final.json")
        print("\n✅ COMPLETE!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("🔒 Browser closed\n")

if __name__ == "__main__":
    main()