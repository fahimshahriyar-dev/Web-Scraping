"""
Lincoln Complete Scraper - MODIFIED VERSION
Scrapes PAINT COLORS + EQUIPMENT COLLECTIONS + ADDITIONAL PACKAGES + POWERTRAINS + EXTERIOR + INTERIOR + ACCESSORIES

MODIFICATION: Only paint_colors section keeps car_image URLs. All other sections have car_image set to empty string.
FIXED: URL navigation issues for multiple vehicles
"""

import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from typing import List, Dict, Any


class LincolnCompleteScraper:
    def __init__(self, headless: bool = False):
        """
        Initialize the scraper with Chrome options
        """
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
    
    # ==================== URL CLEANING METHOD ====================
    
    def clean_url(self, url: str) -> str:
        """
        Clean and fix URL encoding issues
        """
        if not url:
            return url
            
        # Fix double-encoded brackets
        url = url.replace('%255B', '%5B')  # Fix [ encoding
        url = url.replace('%255D', '%5D')  # Fix ] encoding
        
        # Remove any fragments that might cause issues
        if '#/config' in url:
            # Extract base part before the config
            parts = url.split('#/config')
            if len(parts) > 1:
                # Keep only the part before #/config plus #/config
                url = parts[0] + '#/config'
                # Add back any valid path after config if it exists
                if len(parts[1]) > 0 and not parts[1].startswith('/'):
                    url = parts[0] + '#/config/' + parts[1]
        
        return url
    
    # ==================== POPUP HANDLING METHODS ====================
    
    def handle_continue_popup(self):
        """
        Check for and handle the "Do you want to continue?" popup
        Clicks "Yes, continue" if present
        """
        try:
            # Check if popup exists and is visible
            popup_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn.btn-primary.accept")
            
            for button in popup_buttons:
                if button.is_displayed() and "Yes, continue" in button.text:
                    print("      ⚠ Popup detected - clicking 'Yes, continue'")
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1.5)  # Wait for popup to close and page to update
                    return True
                    
            # Alternative selector if the above doesn't work
            popup = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, continue')]")
            for button in popup:
                if button.is_displayed():
                    print("      ⚠ Popup detected - clicking 'Yes, continue'")
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1.5)
                    return True
                    
        except Exception as e:
            # Popup not found or error - continue normally
            pass
        
        return False
    
    # ==================== IMAGE EXTRACTION AND LOADING METHODS ====================
    
    def is_image_loaded(self, img_element) -> bool:
        """
        Check if an image element is fully loaded
        
        Args:
            img_element: Selenium WebElement of the image
            
        Returns:
            True if image is loaded, False otherwise
        """
        try:
            # Check if image has natural dimensions (loaded)
            natural_width = self.driver.execute_script(
                "return arguments[0].naturalWidth;", img_element
            )
            natural_height = self.driver.execute_script(
                "return arguments[0].naturalHeight;", img_element
            )
            
            # Check if image is visible
            is_visible = self.driver.execute_script(
                "return arguments[0].offsetWidth > 0 && arguments[0].offsetHeight > 0;", 
                img_element
            )
            
            # Check if complete
            is_complete = self.driver.execute_script(
                "return arguments[0].complete;", img_element
            )
            
            return natural_width > 0 and natural_height > 0 and is_visible and is_complete
        except:
            return False
    
    def extract_car_image(self) -> str:
        """
        Extract the main car image from the page by looking for the 'asset' class
        
        Returns:
            URL of the car image
        """
        car_image = ""
        
        # Try multiple times with short delays to catch dynamic updates
        for attempt in range(3):
            # Primary strategy: look for elements with class 'asset'
            try:
                asset_elements = self.driver.find_elements(By.CLASS_NAME, "asset")
                for element in asset_elements:
                    if element.tag_name == "img":
                        src = element.get_attribute("src")
                        if src and ("HD-TILE" in src or "HD-FULL" in src or "vehicle" in src.lower()):
                            if self.is_image_loaded(element):
                                car_image = src
                                return car_image
                    else:
                        imgs = element.find_elements(By.TAG_NAME, "img")
                        for img in imgs:
                            src = img.get_attribute("src")
                            if src and ("HD-TILE" in src or "HD-FULL" in src or "vehicle" in src.lower()):
                                if self.is_image_loaded(img):
                                    car_image = src
                                    return car_image
            except Exception:
                pass
            
            # If no image found with 'asset' class, try other strategies as fallback
            if not car_image:
                strategies = [
                    (By.CSS_SELECTOR, "img[src*='HD-TILE']"),
                    (By.CSS_SELECTOR, "img[src*='HD-FULL']"),
                    (By.CSS_SELECTOR, "img[class*='vehicle']"),
                    (By.CSS_SELECTOR, "img[src*='build.ford.com']"),
                    (By.CSS_SELECTOR, "img.asset"),
                    (By.CSS_SELECTOR, ".asset img"),
                ]
                
                for selector_type, selector in strategies:
                    try:
                        elements = self.driver.find_elements(selector_type, selector)
                        for element in elements:
                            src = element.get_attribute("src")
                            if src and ("HD-TILE" in src or "HD-FULL" in src or "vehicle" in src.lower()):
                                if self.is_image_loaded(element):
                                    car_image = src
                                    return car_image
                        if car_image:
                            break
                    except Exception:
                        continue
            
            time.sleep(0.5)  # Wait before retry
        
        return car_image
    
    def wait_for_image_load(self, timeout: int = 15) -> bool:
        """
        Wait for the car image to fully load and stabilize
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if image loaded successfully, False otherwise
        """
        try:
            # Wait for any ongoing animations/updates to complete
            time.sleep(1)
            
            start_time = time.time()
            last_image = ""
            stable_count = 0
            required_stable_checks = 3  # Number of consecutive identical images to confirm stability
            
            while time.time() - start_time < timeout:
                current_image = self.extract_car_image()
                
                if current_image and current_image != last_image:
                    # Image changed, reset stable counter
                    last_image = current_image
                    stable_count = 0
                    time.sleep(0.5)
                elif current_image and current_image == last_image:
                    # Image same as before
                    stable_count += 1
                    if stable_count >= required_stable_checks:
                        # Image has been stable for multiple checks
                        time.sleep(0.5)  # Extra wait to ensure everything is rendered
                        return True
                    else:
                        time.sleep(0.3)
                else:
                    # No image yet
                    time.sleep(0.5)
            
            print(f"      ⚠ Timeout waiting for image to stabilize")
            return False
            
        except Exception as e:
            print(f"      ⚠ Error waiting for image: {e}")
            return False
    
    def click_option_and_wait(self, option_element, option_name: str) -> str:
        """
        Click on an option and wait for the car image to fully load and stabilize
        Handles any confirmation popups that may appear
        
        Args:
            option_element: Selenium WebElement of the option
            option_name: Name of the option for logging
            
        Returns:
            URL of the updated car image
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option_element)
            time.sleep(0.5)
            
            # Try different click strategies
            try:
                option_element.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", option_element)
                except:
                    # Try to find radio input or label
                    try:
                        radio = option_element.find_element(By.CSS_SELECTOR, "input[type='radio']")
                        self.driver.execute_script("arguments[0].click();", radio)
                    except:
                        try:
                            label = option_element.find_element(By.CLASS_NAME, "veh-color-tile__label")
                            label.click()
                        except:
                            print(f"      Could not click {option_name}")
                            return ""
            
            time.sleep(1)  # Wait for any popups to appear
            
            # Check for and handle confirmation popup
            self.handle_continue_popup()
            
            # Wait for image to fully load and stabilize
            self.wait_for_image_load(timeout=15)
            
            car_image = self.extract_car_image()
            return car_image
            
        except Exception as e:
            print(f"      ✗ Error clicking {option_name}: {e}")
            return ""
    
    # ==================== PAINT SCRAPING METHODS ====================
    
    def extract_paint_colors(self) -> List[Dict[str, Any]]:
        """
        Extract paint color options by clicking each one to get the car image
        
        Returns:
            List of paint color dictionaries
        """
        paint_colors = []
        
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-name='paint'], [data-url-key='paint']"))
            )
            time.sleep(2)
            
            paint_section = None
            try:
                paint_section = self.driver.find_element(By.CSS_SELECTOR, "[data-name='paint'], [data-url-key='paint']")
            except:
                try:
                    paint_section = self.driver.find_element(By.ID, "paint-view")
                except:
                    sections = self.driver.find_elements(By.CSS_SELECTOR, ".part-selector")
                    if sections:
                        paint_section = sections[0]
            
            if not paint_section:
                print("  ✗ Could not find paint section")
                return paint_colors
            
            color_tiles = paint_section.find_elements(By.CLASS_NAME, "veh-color-tile")
            print(f"\n  Found {len(color_tiles)} paint colors:")
            print("  " + "-" * 30)
            
            for index, tile in enumerate(color_tiles):
                try:
                    radio_input = tile.find_element(By.CSS_SELECTOR, "input[type='radio']")
                    aria_label = radio_input.get_attribute("aria-label")
                    
                    name = ""
                    price = "$0"
                    
                    if aria_label:
                        parts = aria_label.split("$")
                        name = parts[0].strip()
                        if len(parts) > 1:
                            price_part = parts[1].strip()
                            price = "$" + price_part.split()[0] if price_part else "0"
                    
                    swatch_color = ""
                    try:
                        color_chip = tile.find_element(By.CLASS_NAME, "veh-color-tile__part-color")
                        swatch_color = color_chip.value_of_css_property("background-color")
                    except NoSuchElementException:
                        pass
                    
                    is_default = False
                    try:
                        parent_div = tile.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                        is_default = "checked" in parent_div.get_attribute("class")
                    except:
                        pass
                    
                    car_image = self.click_color_and_wait(tile, name)
                    
                    paint_colors.append({
                        "name": name,
                        "price": price,
                        "swatch_color": swatch_color,
                        "car_image": car_image,
                        "is_default": is_default
                    })
                    
                except Exception as e:
                    print(f"    ✗ Error extracting color {index}: {e}")
                    continue
            
        except TimeoutException:
            print("  ✗ Timeout waiting for paint colors to load")
        
        return paint_colors
    
    def click_color_and_wait(self, color_tile, color_name: str) -> str:
        """
        Click on a color tile and wait for the car image to fully load and stabilize
        Handles any confirmation popups that may appear
        
        Args:
            color_tile: Selenium WebElement of the color tile
            color_name: Name of the color for logging
            
        Returns:
            URL of the updated car image
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", color_tile)
            time.sleep(0.5)
            
            try:
                label = color_tile.find_element(By.CLASS_NAME, "veh-color-tile__label")
                label.click()
            except:
                radio_input = color_tile.find_element(By.CSS_SELECTOR, "input[type='radio']")
                self.driver.execute_script("arguments[0].click();", radio_input)
            
            time.sleep(1)  # Wait for any popups to appear
            
            # Check for and handle confirmation popup
            self.handle_continue_popup()
            
            # Wait for image to fully load and stabilize
            self.wait_for_image_load(timeout=15)
            
            car_image = self.extract_car_image()
            print(f"    ✓ {color_name}")
            return car_image
            
        except Exception as e:
            print(f"    ✗ Error clicking {color_name}: {e}")
            return ""
    
    # ==================== PACKAGE SCRAPING METHODS ====================
    
    def extract_equipment_collections(self) -> List[Dict[str, Any]]:
        """
        Extract Equipment Collections (Premiere I, Premiere II, etc.)
        MODIFIED: car_image set to empty string
        
        Returns:
            List of equipment collection dictionaries
        """
        equipment_collections = []
        
        try:
            print("\n  Extracting Equipment Collections...")
            
            equipment_section = None
            try:
                equipment_section = self.driver.find_element(By.ID, "Equipment_Collections")
                equipment_section = equipment_section.find_element(By.XPATH, "./ancestor::div[contains(@class, 'part-class-container')]")
            except:
                try:
                    equipment_section = self.driver.find_element(By.XPATH, "//h3[text()='Equipment Collections']/ancestor::div[contains(@class, 'part-class-container')]")
                except:
                    print("    ✗ Could not find Equipment Collections section")
                    return equipment_collections
            
            equipment_cards = equipment_section.find_elements(By.CLASS_NAME, "equipment-group-card")
            print(f"    Found {len(equipment_cards)} equipment collections")
            
            for card in equipment_cards:
                try:
                    name = ""
                    try:
                        name_element = card.find_element(By.CLASS_NAME, "equipment-group-name")
                        name = name_element.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    price = "$0"
                    is_default = False
                    try:
                        price_element = card.find_element(By.CLASS_NAME, "price")
                        price_text = price_element.text.strip()
                        
                        if "Included" in price_text:
                            price = "$0"
                            is_default = True
                        else:
                            price = price_text.replace("Price: ", "").strip()
                    except NoSuchElementException:
                        pass
                    
                    # Check if selected
                    try:
                        parent_div = card.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                        is_default = is_default or "selected" in parent_div.get_attribute("class")
                    except:
                        is_default = is_default or "selected" in card.get_attribute("class")
                    
                    # MODIFIED: car_image set to empty string (no extraction)
                    car_image = ""
                    
                    equipment_collections.append({
                        "name": name,
                        "price": price,
                        "swatch_color": "",
                        "car_image": car_image,
                        "is_default": is_default
                    })
                    
                    status = "✓ (Default)" if is_default else "✓"
                    print(f"    {status} {name} - {price}")
                    
                except Exception as e:
                    print(f"    ✗ Error extracting equipment collection: {e}")
                    continue
            
        except Exception as e:
            print(f"  ✗ Error in extract_equipment_collections: {e}")
        
        return equipment_collections
    
    def extract_packages(self) -> List[Dict[str, Any]]:
        """
        Extract additional Packages (Jet Appearance, Towing, etc.)
        MODIFIED: car_image set to empty string
        
        Returns:
            List of package dictionaries
        """
        packages = []
        
        try:
            print("\n  Extracting Additional Packages...")
            
            packages_section = None
            try:
                packages_heading = self.driver.find_element(By.XPATH, "//h3[@id='Packages' or text()='Packages']")
                packages_section = packages_heading.find_element(By.XPATH, "./ancestor::div[contains(@class, 'part-class-container')]")
            except:
                print("    ✗ Could not find Packages section")
                return packages
            
            package_tiles = packages_section.find_elements(By.CLASS_NAME, "vehicle-part-tile")
            print(f"    Found {len(package_tiles)} packages")
            
            for tile in package_tiles:
                try:
                    name = ""
                    try:
                        name_element = tile.find_element(By.CLASS_NAME, "card-title")
                        name = name_element.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    price = "$0"
                    try:
                        price_element = tile.find_element(By.CLASS_NAME, "vehicle-part-tile__price")
                        price = price_element.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    is_default = False
                    try:
                        parent_div = tile.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                        is_default = "selected" in parent_div.get_attribute("class") or "checked" in parent_div.get_attribute("class")
                    except:
                        pass
                    
                    # MODIFIED: car_image set to empty string (no extraction)
                    car_image = ""
                    
                    packages.append({
                        "name": name,
                        "price": price,
                        "swatch_color": "",
                        "car_image": car_image,
                        "is_default": is_default
                    })
                    
                    status = "✓ (Default)" if is_default else "✓"
                    print(f"    {status} {name} - {price}")
                    
                except Exception as e:
                    print(f"    ✗ Error extracting package: {e}")
                    continue
            
        except Exception as e:
            print(f"  ✗ Error in extract_packages: {e}")
        
        return packages
    
    # ==================== POWERTRAIN SCRAPING METHODS ====================
    
    def extract_powertrains(self) -> Dict[str, Any]:
        """
        Extract Powertrain options including Engine, Drive, and Transmission
        MODIFIED: car_image set to empty string
        
        Returns:
            Dictionary containing powertrain categories and their options
        """
        powertrains = {
            "engine": [],
            "drive": [],
            "transmission": []
        }
        
        try:
            print("\n  Extracting Powertrains...")
            
            # Wait for powertrains section to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-url-key='powertrain'], .part-section-wrapper"))
                )
                time.sleep(2)
            except:
                pass
            
            # Find the powertrains section
            powertrain_section = None
            try:
                selectors = [
                    (By.CSS_SELECTOR, "[data-name='powertrain']"),
                    (By.CSS_SELECTOR, "[data-url-key='powertrain']"),
                    (By.XPATH, "//h2[contains(text(), 'Powertrains')]/ancestor::div[contains(@class, 'part-section-wrapper')]"),
                ]
                
                for selector_type, selector in selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector)
                        if elements:
                            if selector_type == By.XPATH:
                                powertrain_section = elements[0]
                            else:
                                powertrain_section = elements[0].find_element(By.XPATH, "./ancestor::div[contains(@class, 'part-section-wrapper')]")
                            break
                    except:
                        continue
                        
                if not powertrain_section:
                    part_containers = self.driver.find_elements(By.CLASS_NAME, "part-class-container")
                    for container in part_containers:
                        try:
                            header = container.find_element(By.CLASS_NAME, "part-class-name")
                            if header.text in ["Engine", "Drive", "Transmission"]:
                                powertrain_section = container.find_element(By.XPATH, "./ancestor::div[contains(@class, 'part-section-wrapper')]")
                                break
                        except:
                            continue
                            
            except Exception as e:
                print(f"    ✗ Error finding powertrains section: {e}")
                return powertrains
            
            if not powertrain_section:
                print("    ✗ Could not find Powertrains section")
                return powertrains
            
            # Extract all part-class-containers within powertrains
            part_containers = powertrain_section.find_elements(By.CLASS_NAME, "part-class-container")
            print(f"    Found {len(part_containers)} powertrain categories")
            
            for container in part_containers:
                try:
                    category_name = ""
                    try:
                        category_element = container.find_element(By.CLASS_NAME, "part-class-name")
                        category_name = category_element.text.strip().lower()
                    except NoSuchElementException:
                        continue
                    
                    category_key = None
                    if "engine" in category_name:
                        category_key = "engine"
                    elif "drive" in category_name:
                        category_key = "drive"
                    elif "transmission" in category_name:
                        category_key = "transmission"
                    
                    if not category_key:
                        continue
                    
                    print(f"\n    Processing {category_name.title()}...")
                    
                    options = container.find_elements(By.CSS_SELECTOR, ".list-group-item")
                    if not options:
                        options = container.find_elements(By.CLASS_NAME, "vehicle-part-tile")
                    
                    print(f"      Found {len(options)} options")
                    
                    for option in options:
                        try:
                            name = ""
                            name_selectors = [
                                (By.CLASS_NAME, "card-title"),
                                (By.CSS_SELECTOR, ".h2.card-title"),
                                (By.CSS_SELECTOR, "p.card-title"),
                                (By.XPATH, ".//p[contains(@class, 'card-title')]")
                            ]
                            
                            for selector_type, selector in name_selectors:
                                try:
                                    name_element = option.find_element(selector_type, selector)
                                    name = name_element.text.strip()
                                    if name:
                                        break
                                except:
                                    continue
                            
                            if not name:
                                continue
                            
                            price = "$0"
                            is_included = False
                            try:
                                price_selectors = [
                                    (By.CLASS_NAME, "vehicle-part-tile__price"),
                                    (By.CSS_SELECTOR, ".vehicle-part-tile__price"),
                                    (By.XPATH, ".//span[contains(@class, 'vehicle-part-tile__price')]")
                                ]
                                
                                for selector_type, selector in price_selectors:
                                    try:
                                        price_element = option.find_element(selector_type, selector)
                                        price_text = price_element.text.strip()
                                        
                                        if "Included" in price_text:
                                            price = "$0"
                                            is_included = True
                                        elif price_text and price_text != "Included":
                                            price_match = re.search(r'\$[\d,]+', price_text)
                                            if price_match:
                                                price = price_match.group()
                                            else:
                                                price = price_text
                                        break
                                    except:
                                        continue
                            except:
                                pass
                            
                            is_default = False
                            try:
                                parent_classes = option.get_attribute("class")
                                if parent_classes:
                                    is_default = "selected" in parent_classes or "active" in parent_classes
                                
                                if not is_default and is_included and len(options) == 1:
                                    is_default = True
                            except:
                                pass
                            
                            # MODIFIED: car_image set to empty string (no extraction)
                            car_image = ""
                            
                            powertrain_option = {
                                "name": name,
                                "price": price,
                                "is_default": is_default,
                                "swatch_color": "",
                                "car_image": car_image
                            }
                            
                            powertrains[category_key].append(powertrain_option)
                            
                            status = "✓ (Default)" if is_default else "✓"
                            print(f"      {status} {name[:60]}... - {price}")
                            
                        except Exception as e:
                            print(f"      ✗ Error extracting option: {e}")
                            continue
                            
                except Exception as e:
                    print(f"    ✗ Error processing {category_name}: {e}")
                    continue
        
        except Exception as e:
            print(f"  ✗ Error in extract_powertrains: {e}")
        
        return powertrains
    
    # ==================== EXTERIOR SCRAPING METHODS ====================
    
    def extract_exterior(self) -> Dict[str, Any]:
        """
        Extract Exterior options including Wheels and Exterior Options
        MODIFIED: car_image set to empty string
        
        Returns:
            Dictionary containing exterior categories and their options
        """
        exterior = {
            "wheels": [],
            "exterior_options": []
        }
        
        try:
            print("\n  Extracting Exterior...")
            
            # Wait for exterior section to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "exterior-view"))
                )
                time.sleep(2)
            except:
                pass
            
            # Find the exterior section
            exterior_section = None
            try:
                selectors = [
                    (By.ID, "exterior-view"),
                    (By.CSS_SELECTOR, "[data-url-key='exterior']"),
                    (By.XPATH, "//h2[contains(text(), 'Exterior')]/ancestor::section[contains(@class, 'part-selector')]"),
                    (By.CSS_SELECTOR, "section.part-selector#exterior-view"),
                ]
                
                for selector_type, selector in selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector)
                        if elements:
                            exterior_section = elements[0]
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"    ✗ Error finding exterior section: {e}")
                return exterior
            
            if not exterior_section:
                print("    ✗ Could not find Exterior section")
                return exterior
            
            # Extract all part-class-containers within exterior
            part_containers = exterior_section.find_elements(By.CLASS_NAME, "part-class-container")
            print(f"    Found {len(part_containers)} exterior categories")
            
            for container in part_containers:
                try:
                    category_name = ""
                    try:
                        category_element = container.find_element(By.CLASS_NAME, "part-class-name")
                        category_name = category_element.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    category_key = None
                    if "wheel" in category_name.lower():
                        category_key = "wheels"
                    elif "exterior option" in category_name.lower():
                        category_key = "exterior_options"
                    
                    if not category_key:
                        continue
                    
                    print(f"\n    Processing {category_name}...")
                    
                    # Get description if available (shows default option)
                    description = ""
                    try:
                        desc_element = container.find_element(By.CLASS_NAME, "description")
                        description = desc_element.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    options = container.find_elements(By.CSS_SELECTOR, ".list-group-item")
                    if not options:
                        options = container.find_elements(By.CLASS_NAME, "vehicle-part-tile")
                    
                    print(f"      Found {len(options)} options")
                    
                    for option in options:
                        try:
                            name = ""
                            name_selectors = [
                                (By.CLASS_NAME, "card-title"),
                                (By.CSS_SELECTOR, ".h2.card-title"),
                                (By.CSS_SELECTOR, "p.card-title"),
                                (By.XPATH, ".//p[contains(@class, 'card-title')]")
                            ]
                            
                            for selector_type, selector in name_selectors:
                                try:
                                    name_element = option.find_element(selector_type, selector)
                                    name = name_element.text.strip()
                                    if name:
                                        break
                                except:
                                    continue
                            
                            if not name:
                                continue
                            
                            price = "$0"
                            is_included = False
                            try:
                                price_selectors = [
                                    (By.CLASS_NAME, "vehicle-part-tile__price"),
                                    (By.CSS_SELECTOR, ".vehicle-part-tile__price"),
                                    (By.XPATH, ".//span[contains(@class, 'vehicle-part-tile__price')]")
                                ]
                                
                                for selector_type, selector in price_selectors:
                                    try:
                                        price_element = option.find_element(selector_type, selector)
                                        price_text = price_element.text.strip()
                                        
                                        if "Included" in price_text:
                                            price = "$0"
                                            is_included = True
                                        elif price_text and price_text != "Included":
                                            price_match = re.search(r'\$[\d,]+', price_text)
                                            if price_match:
                                                price = price_match.group()
                                            else:
                                                price = price_text
                                        break
                                    except:
                                        continue
                            except:
                                pass
                            
                            is_default = False
                            try:
                                parent_classes = option.get_attribute("class")
                                if parent_classes:
                                    is_default = "selected" in parent_classes or "active" in parent_classes
                                
                                try:
                                    parent_div = option.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                                    is_default = is_default or "selected" in parent_div.get_attribute("class")
                                except:
                                    pass
                                
                                if not is_default and is_included and description and name in description:
                                    is_default = True
                            except:
                                pass
                            
                            # MODIFIED: car_image set to empty string (no extraction)
                            car_image = ""
                            
                            exterior_option = {
                                "name": name,
                                "price": price,
                                "is_default": is_default,
                                "swatch_color": "",
                                "car_image": car_image
                            }
                            
                            exterior[category_key].append(exterior_option)
                            
                            status = "✓ (Default)" if is_default else "✓"
                            price_display = f" - {price}" if price != "$0" else " - Included"
                            print(f"      {status} {name[:60]}...{price_display}")
                            
                        except Exception as e:
                            print(f"      ✗ Error extracting option: {e}")
                            continue
                            
                except Exception as e:
                    print(f"    ✗ Error processing category: {e}")
                    continue
        
        except Exception as e:
            print(f"  ✗ Error in extract_exterior: {e}")
        
        return exterior
    
    # ==================== INTERIOR SCRAPING METHODS ====================
    
    def extract_interior(self) -> Dict[str, Any]:
        """
        Extract Interior options including Color, Interior Options, Technology, and Audio Upgrade
        MODIFIED: car_image set to empty string
        
        Returns:
            Dictionary containing interior categories and their options
        """
        interior = {
            "color": [],
            "interior_options": [],
            "technology": [],
            "audio_upgrade": []
        }
        
        try:
            print("\n  Extracting Interior...")
            
            # Wait for interior section to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "interior-view"))
                )
                time.sleep(2)
            except:
                pass
            
            # Find the interior section
            interior_section = None
            try:
                selectors = [
                    (By.ID, "interior-view"),
                    (By.CSS_SELECTOR, "[data-url-key='interior']"),
                    (By.XPATH, "//h2[contains(text(), 'Interior')]/ancestor::section[contains(@class, 'part-selector')]"),
                    (By.CSS_SELECTOR, "section.part-selector#interior-view"),
                ]
                
                for selector_type, selector in selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector)
                        if elements:
                            interior_section = elements[0]
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"    ✗ Error finding interior section: {e}")
                return interior
            
            if not interior_section:
                print("    ✗ Could not find Interior section")
                return interior
            
            # Extract all part-class-containers within interior
            part_containers = interior_section.find_elements(By.CLASS_NAME, "part-class-container")
            print(f"    Found {len(part_containers)} interior categories")
            
            for container in part_containers:
                try:
                    category_name = ""
                    try:
                        category_element = container.find_element(By.CLASS_NAME, "part-class-name")
                        category_name = category_element.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    # Map category name to our dictionary keys
                    category_key = None
                    if category_name.lower() == "color":
                        category_key = "color"
                    elif "interior option" in category_name.lower():
                        category_key = "interior_options"
                    elif "technology" in category_name.lower():
                        category_key = "technology"
                    elif "audio upgrade" in category_name.lower():
                        category_key = "audio_upgrade"
                    
                    if not category_key:
                        continue
                    
                    print(f"\n    Processing {category_name}...")
                    
                    # Get description if available (shows default option)
                    description = ""
                    try:
                        desc_element = container.find_element(By.CLASS_NAME, "description")
                        description = desc_element.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    # Handle Color section differently (uses veh-color-tile structure)
                    if category_key == "color":
                        options = container.find_elements(By.CLASS_NAME, "veh-color-tile")
                        print(f"      Found {len(options)} color options")
                        
                        for option in options:
                            try:
                                # Get color name from aria-label
                                name = ""
                                try:
                                    radio_input = option.find_element(By.CSS_SELECTOR, "input[type='radio']")
                                    name = radio_input.get_attribute("aria-label")
                                except:
                                    try:
                                        label = option.find_element(By.CLASS_NAME, "veh-color-tile__label")
                                        name = label.text.strip()
                                    except:
                                        continue
                                
                                if not name:
                                    continue
                                
                                # Extract swatch color
                                swatch_color = ""
                                try:
                                    color_chip = option.find_element(By.CLASS_NAME, "veh-color-tile__part-color")
                                    swatch_color = color_chip.value_of_css_property("background-color")
                                except NoSuchElementException:
                                    pass
                                
                                # Check if default/selected
                                is_default = False
                                try:
                                    # Check for checked class on input or parent
                                    try:
                                        radio_input = option.find_element(By.CSS_SELECTOR, "input[type='radio']")
                                        is_default = radio_input.get_attribute("aria-checked") == "true"
                                    except:
                                        pass
                                    
                                    # Check for checked class on label
                                    if not is_default:
                                        try:
                                            label = option.find_element(By.CLASS_NAME, "veh-color-tile__label")
                                            label_classes = label.get_attribute("class")
                                            is_default = "checked" in label_classes
                                        except:
                                            pass
                                    
                                    # Check parent classes
                                    if not is_default:
                                        try:
                                            parent_div = option.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                                            parent_classes = parent_div.get_attribute("class")
                                            is_default = "selected" in parent_classes or "checked" in parent_classes
                                        except:
                                            pass
                                except:
                                    pass
                                
                                # For interior colors, price is always $0 (Included)
                                price = "$0"
                                
                                # MODIFIED: car_image set to empty string (no extraction)
                                car_image = ""
                                
                                interior_option = {
                                    "name": name,
                                    "price": price,
                                    "swatch_color": swatch_color,
                                    "car_image": car_image,
                                    "is_default": is_default
                                }
                                
                                interior[category_key].append(interior_option)
                                
                                status = "✓ (Default)" if is_default else "✓"
                                print(f"      {status} {name} - {swatch_color}")
                                
                            except Exception as e:
                                print(f"      ✗ Error extracting color option: {e}")
                                continue
                    
                    else:
                        # Handle other interior categories (Interior Options, Technology, Audio Upgrade)
                        options = container.find_elements(By.CSS_SELECTOR, ".list-group-item")
                        if not options:
                            options = container.find_elements(By.CLASS_NAME, "vehicle-part-tile")
                        
                        print(f"      Found {len(options)} options")
                        
                        for option in options:
                            try:
                                name = ""
                                name_selectors = [
                                    (By.CLASS_NAME, "card-title"),
                                    (By.CSS_SELECTOR, ".h2.card-title"),
                                    (By.CSS_SELECTOR, "p.card-title"),
                                    (By.XPATH, ".//p[contains(@class, 'card-title')]")
                                ]
                                
                                for selector_type, selector in name_selectors:
                                    try:
                                        name_element = option.find_element(selector_type, selector)
                                        name = name_element.text.strip()
                                        if name:
                                            break
                                    except:
                                        continue
                                
                                if not name:
                                    continue
                                
                                # Extract price
                                price = "$0"
                                is_included = False
                                try:
                                    price_selectors = [
                                        (By.CLASS_NAME, "vehicle-part-tile__price"),
                                        (By.CSS_SELECTOR, ".vehicle-part-tile__price"),
                                        (By.XPATH, ".//span[contains(@class, 'vehicle-part-tile__price')]")
                                    ]
                                    
                                    for selector_type, selector in price_selectors:
                                        try:
                                            price_element = option.find_element(selector_type, selector)
                                            price_text = price_element.text.strip()
                                            
                                            if "Included" in price_text:
                                                price = "$0"
                                                is_included = True
                                            elif price_text and price_text != "Included":
                                                price_match = re.search(r'\$[\d,]+', price_text)
                                                if price_match:
                                                    price = price_match.group()
                                                else:
                                                    price = price_text
                                            break
                                        except:
                                            continue
                                except:
                                    pass
                                
                                # Check if default/selected
                                is_default = False
                                try:
                                    parent_classes = option.get_attribute("class")
                                    if parent_classes:
                                        is_default = "selected" in parent_classes or "active" in parent_classes
                                    
                                    try:
                                        parent_div = option.find_element(By.XPATH, "./ancestor::div[contains(@class, 'list-group-item')]")
                                        is_default = is_default or "selected" in parent_div.get_attribute("class")
                                    except:
                                        pass
                                    
                                    if not is_default and is_included and len(options) == 1:
                                        is_default = True
                                except:
                                    pass
                                
                                # MODIFIED: car_image set to empty string (no extraction)
                                car_image = ""
                                
                                interior_option = {
                                    "name": name,
                                    "price": price,
                                    "is_default": is_default,
                                    "swatch_color": "",
                                    "car_image": car_image
                                }
                                
                                interior[category_key].append(interior_option)
                                
                                status = "✓ (Default)" if is_default else "✓"
                                price_display = f" - {price}" if price != "$0" else " - Included"
                                print(f"      {status} {name[:60]}...{price_display}")
                                
                            except Exception as e:
                                print(f"      ✗ Error extracting option: {e}")
                                continue
                                
                except Exception as e:
                    print(f"    ✗ Error processing category: {e}")
                    continue
        
        except Exception as e:
            print(f"  ✗ Error in extract_interior: {e}")
        
        return interior
    
    # ==================== ACCESSORIES SCRAPING METHODS ====================
    
    def extract_accessories(self) -> Dict[str, Any]:
        """
        Extract Accessories options with nested accordion structure
        MODIFIED: car_image set to empty string
        
        Returns:
            Dictionary containing accessories categories and their options
        """
        accessories = {}
        
        try:
            print("\n  Extracting Accessories...")
            
            # Wait for accessories section to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "accessories-view"))
                )
                time.sleep(3)  # Extra time for accordions to load
            except:
                pass
            
            # Find the accessories section
            accessories_section = None
            try:
                selectors = [
                    (By.ID, "accessories-view"),
                    (By.CSS_SELECTOR, "[data-url-key='accessories']"),
                    (By.XPATH, "//h2[contains(text(), 'Accessories')]/ancestor::section[contains(@class, 'part-selector')]"),
                    (By.CSS_SELECTOR, "section.part-selector#accessories-view"),
                ]
                
                for selector_type, selector in selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector)
                        if elements:
                            accessories_section = elements[0]
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"    ✗ Error finding accessories section: {e}")
                return accessories
            
            if not accessories_section:
                print("    ✗ Could not find Accessories section")
                return accessories
            
            # Find all top-level accordion cards (Electronics, Exterior, Interior)
            top_level_cards = accessories_section.find_elements(By.CSS_SELECTOR, ".accordionCard")
            print(f"    Found {len(top_level_cards)} top-level accessory categories")
            
            for top_card in top_level_cards:
                try:
                    # Get top-level category name
                    top_category_name = ""
                    try:
                        top_header = top_card.find_element(By.CSS_SELECTOR, ".card-header h2 a")
                        top_category_name = top_header.text.strip().split('\n')[0].strip()
                    except:
                        continue
                    
                    if not top_category_name:
                        continue
                    
                    print(f"\n    Processing Top Category: {top_category_name}...")
                    
                    # Try to expand the top-level accordion if not already expanded
                    try:
                        top_header = top_card.find_element(By.CSS_SELECTOR, ".card-header h2 a")
                        is_expanded = top_header.get_attribute("aria-expanded")
                        
                        if is_expanded == "false":
                            self.driver.execute_script("arguments[0].click();", top_header)
                            time.sleep(1)  # Wait for accordion to expand
                            print(f"      Expanded {top_category_name} accordion")
                    except:
                        pass
                    
                    # Get the card body for this top category
                    card_body = None
                    try:
                        # Find the collapse div that contains the body
                        collapse_id = top_card.get_attribute("id")
                        if not collapse_id:
                            # Try to find by card-id attribute
                            collapse_id = top_card.get_attribute("card-id")
                        
                        if collapse_id:
                            card_body = top_card.find_element(By.CSS_SELECTOR, f".collapse#{collapse_id} .card-body")
                        else:
                            # Fallback: find any collapse in this card
                            card_body = top_card.find_element(By.CSS_SELECTOR, ".collapse .card-body")
                    except:
                        pass
                    
                    if not card_body:
                        print(f"      No expanded content found for {top_category_name}")
                        # Create empty category
                        accessories[top_category_name] = {}
                        continue
                    
                    # Find all sub-categories (second level accordions)
                    sub_categories = card_body.find_elements(By.CSS_SELECTOR, ".card.mb-lg-1.pl-3")
                    print(f"      Found {len(sub_categories)} sub-categories in {top_category_name}")
                    
                    top_category_dict = {}
                    
                    for sub_card in sub_categories:
                        try:
                            # Get sub-category name
                            sub_category_name = ""
                            try:
                                sub_header = sub_card.find_element(By.CSS_SELECTOR, ".card-header h3 a")
                                # Extract the text without the chevron icon
                                sub_header_html = sub_header.get_attribute("innerHTML")
                                # Extract text after the icon container
                                if "icon-container" in sub_header_html:
                                    match = re.search(r'</span>\s*(.*?)\s*<', sub_header_html)
                                    if match:
                                        sub_category_name = match.group(1).strip()
                                    else:
                                        sub_category_name = sub_header.text.strip()
                                else:
                                    sub_category_name = sub_header.text.strip()
                            except:
                                continue
                            
                            if not sub_category_name:
                                continue
                            
                            print(f"        Processing Sub-Category: {sub_category_name}...")
                            
                            # Try to expand sub-category accordion
                            try:
                                sub_header = sub_card.find_element(By.CSS_SELECTOR, ".card-header h3 a")
                                is_expanded = sub_header.get_attribute("aria-expanded")
                                
                                if is_expanded == "false":
                                    self.driver.execute_script("arguments[0].click();", sub_header)
                                    time.sleep(0.5)  # Wait for accordion to expand
                                    print(f"          Expanded {sub_category_name} accordion")
                            except:
                                pass
                            
                            # Get the sub-category body
                            sub_card_body = None
                            try:
                                sub_card_body = sub_card.find_element(By.CSS_SELECTOR, ".collapse .card-body")
                            except:
                                pass
                            
                            if not sub_card_body:
                                print(f"          No expanded content found for {sub_category_name}")
                                top_category_dict[sub_category_name] = []
                                continue
                            
                            # Find all items in this sub-category
                            items = sub_card_body.find_elements(By.CSS_SELECTOR, ".list-group-item")
                            print(f"          Found {len(items)} items in {sub_category_name}")
                            
                            sub_category_items = []
                            
                            for item in items:
                                try:
                                    # Extract item name
                                    name = ""
                                    name_selectors = [
                                        (By.CLASS_NAME, "card-title"),
                                        (By.CSS_SELECTOR, ".h2.card-title"),
                                        (By.CSS_SELECTOR, "p.card-title"),
                                        (By.XPATH, ".//p[contains(@class, 'card-title')]")
                                    ]
                                    
                                    for selector_type, selector in name_selectors:
                                        try:
                                            name_element = item.find_element(selector_type, selector)
                                            name = name_element.text.strip()
                                            if name:
                                                break
                                        except:
                                            continue
                                    
                                    if not name:
                                        continue
                                    
                                    # Extract price
                                    price = "$0"
                                    try:
                                        price_selectors = [
                                            (By.CLASS_NAME, "vehicle-part-tile__price"),
                                            (By.CSS_SELECTOR, ".vehicle-part-tile__price"),
                                            (By.XPATH, ".//span[contains(@class, 'vehicle-part-tile__price')]")
                                        ]
                                        
                                        for selector_type, selector in price_selectors:
                                            try:
                                                price_element = item.find_element(selector_type, selector)
                                                price_text = price_element.text.strip()
                                                
                                                if price_text and price_text != "Included":
                                                    price_match = re.search(r'\$[\d,]+', price_text)
                                                    if price_match:
                                                        price = price_match.group()
                                                    else:
                                                        price = price_text
                                                break
                                            except:
                                                continue
                                    except:
                                        pass
                                    
                                    # Accessories are never default (always optional add-ons)
                                    is_default = False
                                    
                                    # MODIFIED: car_image set to empty string (no extraction)
                                    car_image = ""
                                    
                                    accessory_item = {
                                        "name": name,
                                        "price": price,
                                        "is_default": is_default,
                                        "swatch_color": "",
                                        "car_image": car_image
                                    }
                                    
                                    sub_category_items.append(accessory_item)
                                    print(f"            ✓ {name[:50]}... - {price}")
                                    
                                except Exception as e:
                                    print(f"            ✗ Error extracting accessory item: {e}")
                                    continue
                            
                            top_category_dict[sub_category_name] = sub_category_items
                            
                        except Exception as e:
                            print(f"        ✗ Error processing sub-category: {e}")
                            continue
                    
                    accessories[top_category_name] = top_category_dict
                    
                except Exception as e:
                    print(f"    ✗ Error processing top category: {e}")
                    continue
        
        except Exception as e:
            print(f"  ✗ Error in extract_accessories: {e}")
        
        return accessories
    
    # ==================== NAVIGATION METHODS ====================
    
    def navigate_to_paint(self, base_url: str) -> bool:
        """
        Navigate to the paint configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/paint' not in base_url:
                    if base_url.endswith('/'):
                        paint_url = base_url + 'paint/'
                    else:
                        # Add paint to the hash fragment
                        paint_url = base_url.replace('#/config', '#/config/paint/')
                else:
                    paint_url = base_url
            else:
                # Handle regular URLs
                paint_url = base_url.replace("/config/", "/config/paint/")
                if "/config/paint/" not in paint_url:
                    paint_url = base_url + "paint/"
            
            print(f"  Navigating to paint page...")
            print(f"  URL: {paint_url}")
            self.driver.get(paint_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
            
        except Exception as e:
            print(f"  ✗ Error navigating to paint page: {e}")
            return False
    
    def navigate_to_packages(self, base_url: str) -> bool:
        """
        Navigate to the packages configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/packages' not in base_url:
                    if base_url.endswith('/'):
                        packages_url = base_url + 'packages/'
                    else:
                        # Add packages to the hash fragment
                        packages_url = base_url.replace('#/config', '#/config/packages/')
                else:
                    packages_url = base_url
            else:
                # Handle regular URLs
                packages_url = base_url.replace("/config/", "/config/packages/")
                if "/config/packages/" not in packages_url:
                    packages_url = base_url + "packages/"
            
            print(f"  Navigating to packages page...")
            print(f"  URL: {packages_url}")
            self.driver.get(packages_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
            
        except Exception as e:
            print(f"  ✗ Error navigating to packages page: {e}")
            return False
    
    def navigate_to_powertrains(self, base_url: str) -> bool:
        """
        Navigate to the powertrains configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/powertrain' not in base_url:
                    if base_url.endswith('/'):
                        powertrains_url = base_url + 'powertrain/'
                    else:
                        # Add powertrain to the hash fragment
                        powertrains_url = base_url.replace('#/config', '#/config/powertrain/')
                else:
                    powertrains_url = base_url
            else:
                # Handle regular URLs
                powertrains_url = base_url.replace("/config/", "/config/powertrain/")
                if "/config/powertrain/" not in powertrains_url:
                    powertrains_url = base_url + "powertrain/"
            
            print(f"  Navigating to powertrains page...")
            print(f"  URL: {powertrains_url}")
            self.driver.get(powertrains_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Powertrains')]"))
                )
                return True
            except:
                print("    ⚠ Could not verify powertrains page, but continuing...")
                return True
                
        except Exception as e:
            print(f"  ✗ Error navigating to powertrains page: {e}")
            return False
    
    def navigate_to_exterior(self, base_url: str) -> bool:
        """
        Navigate to the exterior configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/exterior' not in base_url:
                    if base_url.endswith('/'):
                        exterior_url = base_url + 'exterior/'
                    else:
                        # Add exterior to the hash fragment
                        exterior_url = base_url.replace('#/config', '#/config/exterior/')
                else:
                    exterior_url = base_url
            else:
                # Handle regular URLs
                exterior_url = base_url.replace("/config/", "/config/exterior/")
                if "/config/exterior/" not in exterior_url:
                    exterior_url = base_url + "exterior/"
            
            print(f"  Navigating to exterior page...")
            print(f"  URL: {exterior_url}")
            self.driver.get(exterior_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "exterior-view"))
                )
                return True
            except:
                print("    ⚠ Could not verify exterior page, but continuing...")
                return True
                
        except Exception as e:
            print(f"  ✗ Error navigating to exterior page: {e}")
            return False
    
    def navigate_to_interior(self, base_url: str) -> bool:
        """
        Navigate to the interior configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/interior' not in base_url:
                    if base_url.endswith('/'):
                        interior_url = base_url + 'interior/'
                    else:
                        # Add interior to the hash fragment
                        interior_url = base_url.replace('#/config', '#/config/interior/')
                else:
                    interior_url = base_url
            else:
                # Handle regular URLs
                interior_url = base_url.replace("/config/", "/config/interior/")
                if "/config/interior/" not in interior_url:
                    interior_url = base_url + "interior/"
            
            print(f"  Navigating to interior page...")
            print(f"  URL: {interior_url}")
            self.driver.get(interior_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "interior-view"))
                )
                return True
            except:
                print("    ⚠ Could not verify interior page, but continuing...")
                return True
                
        except Exception as e:
            print(f"  ✗ Error navigating to interior page: {e}")
            return False
    
    def navigate_to_accessories(self, base_url: str) -> bool:
        """
        Navigate to the accessories configuration page
        """
        try:
            # Clean the URL first
            base_url = self.clean_url(base_url)
            
            # Extract the base config part
            if '#/config' in base_url:
                # Handle hash-based URLs
                if '/accessories' not in base_url:
                    if base_url.endswith('/'):
                        accessories_url = base_url + 'accessories/'
                    else:
                        # Add accessories to the hash fragment
                        accessories_url = base_url.replace('#/config', '#/config/accessories/')
                else:
                    accessories_url = base_url
            else:
                # Handle regular URLs
                accessories_url = base_url.replace("/config/", "/config/accessories/")
                if "/config/accessories/" not in accessories_url:
                    accessories_url = base_url + "accessories/"
            
            print(f"  Navigating to accessories page...")
            print(f"  URL: {accessories_url}")
            self.driver.get(accessories_url)
            time.sleep(5)
            
            # Handle any popups that might appear
            self.handle_continue_popup()
            
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "accessories-view"))
                )
                return True
            except:
                print("    ⚠ Could not verify accessories page, but continuing...")
                return True
                
        except Exception as e:
            print(f"  ✗ Error navigating to accessories page: {e}")
            return False
    
    # ==================== MAIN SCRAPING METHODS ====================
    
    def scrape_trim_complete(self, trim_url: str) -> Dict[str, Any]:
        """
        Scrape paint, package, powertrain, exterior, interior, AND accessories data for a specific trim
        """
        result = {
            "paint_colors": [],
            "packages": {
                "equipment_collections": [],
                "additional_packages": []
            },
            "powertrains": {
                "engine": [],
                "drive": [],
                "transmission": []
            },
            "exterior": {
                "wheels": [],
                "exterior_options": []
            },
            "interior": {
                "color": [],
                "interior_options": [],
                "technology": [],
                "audio_upgrade": []
            },
            "accessories": {}
        }
        
        # Step 1: Scrape Paint Colors
        print("\n" + "="*40)
        print("SCRAPING PAINT COLORS")
        print("="*40)
        
        if self.navigate_to_paint(trim_url):
            paint_colors = self.extract_paint_colors()
            result["paint_colors"] = paint_colors
            print(f"\n  ✓ Extracted {len(paint_colors)} paint colors")
        
        time.sleep(2)
        
        # Step 2: Scrape Packages
        print("\n" + "="*40)
        print("SCRAPING PACKAGES")
        print("="*40)
        
        if self.navigate_to_packages(trim_url):
            equipment_collections = self.extract_equipment_collections()
            additional_packages = self.extract_packages()
            
            result["packages"] = {
                "equipment_collections": equipment_collections,
                "additional_packages": additional_packages
            }
            
            print(f"\n  ✓ Extracted {len(equipment_collections)} equipment collections")
            print(f"  ✓ Extracted {len(additional_packages)} additional packages")
        
        time.sleep(2)
        
        # Step 3: Scrape Powertrains
        print("\n" + "="*40)
        print("SCRAPING POWERTRAINS")
        print("="*40)
        
        if self.navigate_to_powertrains(trim_url):
            powertrains = self.extract_powertrains()
            result["powertrains"] = powertrains
            
            total_options = (
                len(powertrains.get("engine", [])) +
                len(powertrains.get("drive", [])) +
                len(powertrains.get("transmission", []))
            )
            print(f"\n  ✓ Extracted powertrain options:")
            print(f"    - Engine: {len(powertrains.get('engine', []))} options")
            print(f"    - Drive: {len(powertrains.get('drive', []))} options")
            print(f"    - Transmission: {len(powertrains.get('transmission', []))} options")
        
        time.sleep(2)
        
        # Step 4: Scrape Exterior
        print("\n" + "="*40)
        print("SCRAPING EXTERIOR")
        print("="*40)
        
        if self.navigate_to_exterior(trim_url):
            exterior = self.extract_exterior()
            result["exterior"] = exterior
            
            total_options = (
                len(exterior.get("wheels", [])) +
                len(exterior.get("exterior_options", []))
            )
            print(f"\n  ✓ Extracted exterior options:")
            print(f"    - Wheels: {len(exterior.get('wheels', []))} options")
            print(f"    - Exterior Options: {len(exterior.get('exterior_options', []))} options")
        
        time.sleep(2)
        
        # Step 5: Scrape Interior
        print("\n" + "="*40)
        print("SCRAPING INTERIOR")
        print("="*40)
        
        if self.navigate_to_interior(trim_url):
            interior = self.extract_interior()
            result["interior"] = interior
            
            total_options = (
                len(interior.get("color", [])) +
                len(interior.get("interior_options", [])) +
                len(interior.get("technology", [])) +
                len(interior.get("audio_upgrade", []))
            )
            print(f"\n  ✓ Extracted interior options:")
            print(f"    - Color: {len(interior.get('color', []))} options")
            print(f"    - Interior Options: {len(interior.get('interior_options', []))} options")
            print(f"    - Technology: {len(interior.get('technology', []))} options")
            print(f"    - Audio Upgrade: {len(interior.get('audio_upgrade', []))} options")
        
        time.sleep(2)
        
        # Step 6: Scrape Accessories
        print("\n" + "="*40)
        print("SCRAPING ACCESSORIES")
        print("="*40)
        
        if self.navigate_to_accessories(trim_url):
            accessories = self.extract_accessories()
            result["accessories"] = accessories
            
            # Count total accessories
            total_accessories = 0
            for top_category, sub_categories in accessories.items():
                for sub_category, items in sub_categories.items():
                    total_accessories += len(items)
            
            print(f"\n  ✓ Extracted accessories:")
            print(f"    - Top Categories: {len(accessories)}")
            print(f"    - Total Accessory Items: {total_accessories}")
        
        return result
    
    def scrape_vehicle_complete(self, vehicle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape complete data (paint + packages + powertrains + exterior + interior + accessories) for all trims
        """
        results = []
        
        for idx, (vehicle_name, vehicle_info) in enumerate(vehicle_data.items()):
            # Add a longer delay between different vehicles
            if idx > 0:
                print(f"\nWaiting 5 seconds before processing next vehicle...")
                time.sleep(5)
            
            print(f"\n{'='*60}")
            print(f"Processing: {vehicle_name}")
            print(f"{'='*60}")
            
            vehicle_result = {
                "vehicle": vehicle_name,
                "base_image": vehicle_info.get("base_image", ""),
                "trims": []
            }
            
            for trim in vehicle_info.get("trims", []):
                print(f"\n{'*'*60}")
                print(f"Trim: {trim['name']}")
                print(f"{'*'*60}")
                
                # Clean the trim link before using it
                if trim.get("link"):
                    trim["link"] = self.clean_url(trim["link"])
                    print(f"  Cleaned URL: {trim['link']}")
                
                trim_result = {
                    "trim_name": trim["name"],
                    "trim_price": trim.get("price", "$0"),
                    "trim_image": trim.get("image", ""),
                    "data": {
                        "paint_colors": [],
                        "packages": {
                            "equipment_collections": [],
                            "additional_packages": []
                        },
                        "powertrains": {
                            "engine": [],
                            "drive": [],
                            "transmission": []
                        },
                        "exterior": {
                            "wheels": [],
                            "exterior_options": []
                        },
                        "interior": {
                            "color": [],
                            "interior_options": [],
                            "technology": [],
                            "audio_upgrade": []
                        },
                        "accessories": {}
                    }
                }
                
                if trim.get("link"):
                    complete_data = self.scrape_trim_complete(trim["link"])
                    trim_result["data"] = complete_data
                else:
                    print("  ✗ No link provided for this trim")
                
                vehicle_result["trims"].append(trim_result)
                time.sleep(3)
            
            results.append(vehicle_result)
        
        return results
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str):
        """
        Save scraped data to JSON file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*60}")
        print(f"✓ Complete data saved to {filename}")
        print(f"{'='*60}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """
    Main function - scrapes PAINT COLORS + PACKAGES + POWERTRAINS + EXTERIOR + INTERIOR + ACCESSORIES
    """
    input_data = {
        "2026 Lincoln Corsair®": {
            "base_image": "https://build.ford.com/dig/Lincoln/Corsair/2026/HD-THUMB/Image%5B%7CLincoln%7CCorsair%7C2026%7C1%7C1.%7C100A...PUM...89E.50E.64C.STD.%5D/EXT/5/vehicle.png",
            "trims": [
                {
                    "name": "2026 Lincoln Corsair® Premiere",
                    "link": "https://shop.lincoln.com/build/corsair/#/config/Config%5B%7CLincoln%7CCorsair%7C2026%7C1%7C1.%7C100A...PD4...STD.%5D",
                    "price": "$39,985",
                    "image": "https://build.ford.com/dig/Lincoln/Corsair/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CCorsair%7C2026%7C1%7C1.%7C100A...PUM...89E.50E.64C.STD.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Corsair® Reserve",
                    "link": "https://shop.lincoln.com/build/corsair/#/config/paint/Config%255B%257CLincoln%257CCorsair%257C2026%257C1%257C1.%257C...PK1...RSV.%255D",
                    "price": "$47,640",
                    "image": "https://build.ford.com/dig/Lincoln/Corsair/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CCorsair%7C2026%7C1%7C1.%7C201A...PK1...89E.50D.64R.RSV.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Corsair® Grand Touring",
                    "link": "https://shop.lincoln.com/build/corsair/#/config/paint/Config%255B%257CLincoln%257CCorsair%257C2026%257C1%257C1.%257C...PAZ...GRT.%255D",
                    "price": "$54,365",
                    "image": "https://build.ford.com/dig/Lincoln/Corsair/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CCorsair%7C2026%7C1%7C1.%7C300A...PUM...89E.43M.50D.642.GRT.%5D/EXT/4/vehicle.png"
                }
            ]
        },
        "2026 Lincoln Nautilus": {
            "base_image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-THUMB/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C101A...PJS..88S.89T.64J.99A.STD.%5D/EXT/5/vehicle.png",
            "trims": [
                {
                    "name": "2026 Lincoln Nautilus Premiere (Gas)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PJS...99A.STD.%255D",
                    "price": "$53,995",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C101A...PJS..88S.89T.64J.99A.STD.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Nautilus Premiere (Hybrid)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PJS...994.STD.%255D",
                    "price": "$56,995",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C101A...PJS..88S.89T.64J.99A.STD.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Nautilus Reserve (Gas)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PJS...99A.RSV.%255D",
                    "price": "$63,595",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C202A...PJS..88B.89T.64S.99A.RSV.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Nautilus Reserve (Hybrid)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PJS...994.RSV.%255D",
                    "price": "$66,595",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C202A...PJS..88B.89T.64S.99A.RSV.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Nautilus Lincoln Black Label™ (Gas)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PUM...99A.BLL.%255D",
                    "price": "$77,660",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C800A...PUM..88F.89V.64K.99A.BLL.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Nautilus Lincoln Black Label™ (Hybrid)",
                    "link": "https://shop.lincoln.com/build/nautilus/#/config/paint/Config%255B%257CLincoln%257CNautilus%257C2026%257C1%257C1.%257C...PUM...994.BLL.%255D",
                    "price": "$80,660",
                    "image": "https://build.ford.com/dig/Lincoln/Nautilus/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNautilus%7C2026%7C1%7C1.%7C800A...PUM..88F.89V.64K.994.BLL.%5D/EXT/4/vehicle.png"
                }
            ]
        },
        "2026 Lincoln Aviator": {
            "base_image": "https://build.ford.com/dig/Lincoln/Aviator/2026/HD-THUMB/Image%5B%7CLincoln%7CAviator%7C2026%7C1%7C1.%7C101A...PD4...89W.64G.VS-G1.%5D/EXT/5/vehicle.png",
            "trims": [
                {
                    "name": "2026 Lincoln Aviator Premiere®",
                    "link": "https://shop.lincoln.com/build/aviator/?intcmp=show-bp#/config/paint/Config%255B%257CLincoln%257CAviator%257C2026%257C1%257C1.%257C.J6W..PD4...99C.VS-G1.%255D",
                    "price": "$56,910",
                    "image": "https://build.ford.com/dig/Lincoln/Aviator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CAviator%7C2026%7C1%7C1.%7C100A...PD4...89W.64G.VS-G1.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Aviator Reserve®",
                    "link": "https://shop.lincoln.com/build/aviator/?intcmp=show-bp#/config/paint/Config%255B%257CLincoln%257CAviator%257C2026%257C1%257C1.%257C.J7W..PAZ...99C.VS-G2.%255D",
                    "price": "$66,730",
                    "image": "https://build.ford.com/dig/Lincoln/Aviator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CAviator%7C2026%7C1%7C1.%7C200A...PAZ...89W.64C.VS-G2.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Aviator Black Label™",
                    "link": "https://shop.lincoln.com/build/aviator/?intcmp=show-bp#/config/paint/Config%255B%257CLincoln%257CAviator%257C2026%257C1%257C1.%257C.J9X..PK1...99C.VS-GS.%255D",
                    "price": "$85,910",
                    "image": "https://build.ford.com/dig/Lincoln/Aviator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CAviator%7C2026%7C1%7C1.%7C800A...PK1...89X.65L.64P.67R.VS-GS.%5D/EXT/4/vehicle.png"
                }
            ]
        },
        "2026 Lincoln Navigator": {
            "base_image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-THUMB/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C100A...PC8...89W.PRE.BYBCK.NAV.64E.%5D/EXT/5/vehicle.png",
            "trims": [
                {
                    "name": "2026 Lincoln Navigator Premiere (Navigator)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PC8...PRE.NAV.%255D",
                    "price": "$91,995",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C100A...PC8...89W.PRE.BYBCK.NAV.64E.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Navigator Premiere L (Navigator L)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PC8...PRE.LNV.%255D",
                    "price": "$",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C100A...PC8...89W.PRE.BYBCK.LNV.64E.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Navigator Reserve (Navigator)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PAZ...RES.NAV.%255D",
                    "price": "$101,995",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C202A...PAZ...89W.RES.BYBCK.NAV.64E.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Navigator Reserve L (Navigator L)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PAZ...RES.LNV.%255D",
                    "price": "$104,995",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C202A...PAZ...89W.RES.BYBCK.LNV.64E.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Navigator Black Label (Navigator)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PLT...BLA.NAV.%255D",
                    "price": "$119,525",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C800A...PLT...89J.BLA.21D.536.NAV.64F.%5D/EXT/4/vehicle.png"
                },
                {
                    "name": "2026 Lincoln Navigator Black Label L (Navigator L)",
                    "link": "https://shop.lincoln.com/build/navigator/#/config/paint/Config%255B%257CLincoln%257CNavigator%257C2026%257C1%257C1.%257C...PLT...BLA.LNV.%255D",
                    "price": "$122,525",
                    "image": "https://build.ford.com/dig/Lincoln/Navigator/2026/HD-TILE%5BEXTBCK1%5D/Image%5B%7CLincoln%7CNavigator%7C2026%7C1%7C1.%7C800A...PLT...89J.BLA.21D.536.LNV.64F.%5D/EXT/4/vehicle.png"
                }
            ]
        },
    }
    
    print("="*60)
    print("LINCOLN COMPLETE SCRAPER - MODIFIED VERSION")
    print("Scraping Paint Colors (WITH images) + All Other Sections (NO images)")
    print("="*60)
    
    with LincolnCompleteScraper(headless=False) as scraper:
        results = scraper.scrape_vehicle_complete(input_data)
        scraper.save_to_json(results, "lincoln_complete_data.json")
        
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        
        for vehicle in results:
            print(f"\nVehicle: {vehicle['vehicle']}")
            for trim in vehicle['trims']:
                print(f"\n  Trim: {trim['trim_name']} - {trim['trim_price']}")
                
                data = trim.get('data', {})
                
                # Paint Colors
                paint_colors = data.get('paint_colors', [])
                print(f"  Paint Colors: {len(paint_colors)} (WITH car_image)")
                for color in paint_colors[:3]:
                    default = " (Default)" if color.get('is_default') else ""
                    has_image = "✓ HAS IMAGE" if color.get('car_image') else "✗ NO IMAGE"
                    print(f"    - {color['name']}: {color['price']}{default} [{has_image}]")
                if len(paint_colors) > 3:
                    print(f"    ... and {len(paint_colors) - 3} more")
                
                # Packages
                packages = data.get('packages', {})
                eq_collections = packages.get('equipment_collections', [])
                print(f"\n  Equipment Collections: {len(eq_collections)} (NO car_image)")
                
                # All other sections
                print(f"\n  All other sections have car_image set to empty string")
        
    print("\n✓ Modified scraping finished successfully!")
    print("✓ Only paint_colors have car_image URLs")
    print("✓ All other sections have car_image = ''")


if __name__ == "__main__":
    main()