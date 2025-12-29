import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

class MaseratiScraper:
    def __init__(self):
        """Initialize the Maserati scraper"""
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--window-size=1400,900')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        self.data = []
        self.output_file = "maserati_car_data.json"
    
    def load_initial_models(self):
        """Load initial Maserati models array"""
        return [
            {
                "name": "MCPURA",
                "link": "https://www.maserati.com/us/en/shopping-tools/configurator?modelCode=8417980&modelName=MCP#/main/exteriors",
                "price": "null",
                "image": "https://maserati.scene7.com/is/image/maserati/maserati/international/Models/default/2026/mp/versions/mcpura.jpg?$600x2000$&fit=constrain"
            }
        ]
    
    def save_json(self, data):
        """Save data to JSON file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Data saved to {self.output_file}")
    
    def safe_click(self, element, element_name=""):
        """Safely click an element, handling various interception issues"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            return True
        except ElementClickInterceptedException:
            print(f"  Element {element_name} click intercepted, trying JavaScript click...")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                print(f"  JavaScript click also failed for {element_name}")
                return False
        except Exception as e:
            print(f"  Error clicking {element_name}: {e}")
            return False
    
    def handle_popups(self):
        """Handle common popups on the Maserati website."""
        print("  Checking for and handling popups...")
        time.sleep(3)
        
        # Try to close any modals or overlays
        try:
            close_selectors = [
                "button[aria-label*='close']",
                "button[class*='close']",
                ".close-btn",
                ".modal-close",
                ".cc-modal-close"
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in close_buttons:
                        if btn.is_displayed():
                            self.safe_click(btn, "Close button")
                            print("    Closed popup")
                            time.sleep(1)
                            break
                except:
                    continue
        except:
            pass
        
        print("  Popup handling complete.\n")
    
    def extract_price_from_text(self, text):
        """Extract price from text"""
        if not text:
            return "$0"
        
        # Try multiple price patterns
        price_patterns = [
            r'\$\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*\$',
            r'price:\s*\$\s*[\d,]+',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price = match.group(0)
                # Standardize format
                price = re.sub(r'\s+', ' ', price.strip())
                return price
        
        # Check if it's explicitly free
        if "included" in text.lower() or "no charge" in text.lower() or "standard" in text.lower():
            return "$0"
        
        return "$0"
    
    def get_first_car_image(self):
        """Get the first car preview image from the main carousel"""
        try:
            # Find all img elements with class 'cc-img'
            car_images = self.driver.find_elements(By.CSS_SELECTOR, "img.cc-img")
            
            for img in car_images:
                img_src = img.get_attribute("src")
                if img_src and "gfx" in img_src and "ph.cloud.maserati.com" in img_src:
                    return img_src
            
            # Alternative: look for images in the carousel
            carousel_images = self.driver.find_elements(By.CSS_SELECTOR, ".carousel img")
            for img in carousel_images:
                img_src = img.get_attribute("src")
                if img_src and "gfx" in img_src and "ph.cloud.maserati.com" in img_src:
                    return img_src
            
            return ""
            
        except Exception as e:
            print(f"      Error getting car image: {e}")
            return ""
        

    def scrape_liveries_section(self):
        """Scrape Liveries and Dreamlines section"""
        print("    Scraping Liveries and Dreamlines options...")
        options = []
        
        try:
            # Wait for the section to load
            section_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "LIVREE_section"))
            )
            
            # Find all menu items in this section
            menu_container = section_element.find_element(By.CLASS_NAME, "menu-container")
            
            # Get the current selection label first
            try:
                selection_label = menu_container.find_element(By.CLASS_NAME, "selection-label")
                current_selection_text = selection_label.text.strip()
                print(f"      Current selection: {current_selection_text}")
            except:
                pass
            
            # Find all palette options
            palettes = menu_container.find_elements(By.CLASS_NAME, "palettes")
            
            print(f"      Found {len(palettes)} palette group(s)")
            
            # Store the current state before we start clicking
            original_options = []
            
            for palette_group_idx, palette_group in enumerate(palettes):
                try:
                    # Find all labels within the palette group
                    palette_labels = palette_group.find_elements(By.TAG_NAME, "label")
                    
                    print(f"        Processing {len(palette_labels)} options in palette group {palette_group_idx + 1}")
                    
                    for label_idx, label in enumerate(palette_labels):
                        try:
                            # Skip disabled options (but you might still want to record them)
                            if "disabled" in label.get_attribute("class"):
                                # Still extract the info but mark as disabled
                                is_disabled = True
                            else:
                                is_disabled = False
                            
                            # Check if this is the currently selected option
                            is_current = "current" in label.get_attribute("class")
                            
                            # Get option name and price from aria-label
                            aria_label = label.get_attribute("aria-label")
                            if not aria_label:
                                # Try to get from img alt
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    aria_label = img.get_attribute("alt")
                                except:
                                    continue
                            
                            if aria_label:
                                # Extract price
                                price = self.extract_price_from_text(aria_label)
                                
                                # Clean up name (remove price if present)
                                name = re.sub(r'\$\s?[\d,]+(?:\.\d{2})?', '', aria_label).strip()
                                name = re.sub(r'\s+', ' ', name)  # Clean extra spaces
                                
                                # Get the swatch image URL
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    swatch_image_url = img.get_attribute("src")
                                except:
                                    swatch_image_url = ""
                                
                                option_data = {
                                    "name": name,
                                    "price": price,
                                    "swatch_image": swatch_image_url,
                                    "car_image": "",  # Will be filled after clicking
                                    "currently_selected": is_current,
                                    "disabled": is_disabled
                                }
                                
                                # Store original option data
                                original_options.append((label, option_data, is_current))
                                
                                status = "(selected)" if is_current else ""
                                status += " (disabled)" if is_disabled else ""
                                print(f"          Found: {name} - {price} {status}")
                                
                        except Exception as e:
                            print(f"          Error processing option {label_idx + 1}: {e}")
                            continue
            
                except Exception as e:
                    print(f"        Error processing palette group {palette_group_idx + 1}: {e}")
                    continue
            
            # Now process each option by clicking on the label (skip disabled ones)
            for label, option_data, is_current in original_options:
                name = option_data["name"]
                original_price = option_data["price"]
                
                # Skip disabled options for clicking
                if not option_data.get("disabled", False) and not is_current:
                    try:
                        # Click on the label element
                        print(f"          Clicking on option: {name}")
                        
                        # Scroll the label into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                        time.sleep(0.5)
                        
                        # Try clicking the label directly
                        try:
                            label.click()
                        except:
                            # If direct click fails, try JavaScript click
                            self.driver.execute_script("arguments[0].click();", label)
                        
                        # Wait for car images to load
                        time.sleep(3)
                        
                        # Get the FIRST car preview image
                        car_image_url = self.get_first_car_image()
                        
                        if car_image_url:
                            option_data["car_image"] = car_image_url
                            print(f"            Found car preview image: {car_image_url}")
                        else:
                            print(f"            No car preview image found for {name}")
                        
                        # Check if price changed in selection label
                        try:
                            updated_selection = menu_container.find_element(By.CLASS_NAME, "selection-label")
                            updated_text = updated_selection.text.strip()
                            updated_price = self.extract_price_from_text(updated_text)
                            
                            if updated_price != original_price and updated_price != "$0":
                                print(f"            Price updated to: {updated_price}")
                                option_data["price"] = updated_price
                        except Exception as e:
                            print(f"            Could not check updated price: {e}")
                        
                    except Exception as click_error:
                        print(f"            Could not click option '{name}': {click_error}")
                
                elif is_current:
                    # For currently selected option, get its car image too
                    car_image_url = self.get_first_car_image()
                    if car_image_url:
                        option_data["car_image"] = car_image_url
                        print(f"            Found car preview image for selected option: {car_image_url}")
                
                # Add to final options list (even disabled ones)
                options.append(option_data)
            
            print(f"    Successfully scraped {len(options)} Liveries and Dreamlines options")
            return options
            
        except Exception as e:
            print(f"    Error scraping Liveries and Dreamlines section: {e}")
            return []

    def scrape_soft_top_section(self):
        """Scrape Soft Top section"""
        print("    Scraping Soft Top options...")
        options = []
        
        try:
            # Wait for the section to load
            section_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "SFT_section"))
            )
            
            # Find all menu items in this section
            menu_container = section_element.find_element(By.CLASS_NAME, "menu-container")
            
            # Get the current selection label first
            try:
                selection_label = menu_container.find_element(By.CLASS_NAME, "selection-label")
                current_selection_text = selection_label.text.strip()
                print(f"      Current selection: {current_selection_text}")
            except:
                pass
            
            # Find all palette options
            palettes = menu_container.find_elements(By.CLASS_NAME, "palettes")
            
            print(f"      Found {len(palettes)} palette group(s)")
            
            # Store the current state before we start clicking
            original_options = []
            
            for palette_group_idx, palette_group in enumerate(palettes):
                try:
                    # Find all labels within the palette group
                    palette_labels = palette_group.find_elements(By.TAG_NAME, "label")
                    
                    print(f"        Processing {len(palette_labels)} options in palette group {palette_group_idx + 1}")
                    
                    for label_idx, label in enumerate(palette_labels):
                        try:
                            # Skip disabled options
                            if "disabled" in label.get_attribute("class"):
                                print(f"          Option {label_idx + 1} is disabled, skipping")
                                continue
                            
                            # Check if this is the currently selected option
                            is_current = "current" in label.get_attribute("class")
                            
                            # Get option name and price from aria-label
                            aria_label = label.get_attribute("aria-label")
                            if not aria_label:
                                # Try to get from img alt
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    aria_label = img.get_attribute("alt")
                                except:
                                    continue
                            
                            if aria_label:
                                # Extract price
                                price = self.extract_price_from_text(aria_label)
                                
                                # Clean up name (remove price if present)
                                name = re.sub(r'\$\s?[\d,]+(?:\.\d{2})?', '', aria_label).strip()
                                name = re.sub(r'\s+', ' ', name)  # Clean extra spaces
                                
                                # Get the swatch image URL
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    swatch_image_url = img.get_attribute("src")
                                except:
                                    swatch_image_url = ""
                                
                                option_data = {
                                    "name": name,
                                    "price": price,
                                    "swatch_image": swatch_image_url,
                                    "car_image": "",  # Will be filled after clicking
                                    "currently_selected": is_current
                                }
                                
                                # Store original option data
                                original_options.append((label, option_data, is_current))
                                
                                print(f"          Found: {name} - {price} {'(selected)' if is_current else ''}")
                                
                        except Exception as e:
                            print(f"          Error processing option {label_idx + 1}: {e}")
                            continue
            
                except Exception as e:
                    print(f"        Error processing palette group {palette_group_idx + 1}: {e}")
                    continue
            
            # Now process each option by clicking on the label
            for label, option_data, is_current in original_options:
                name = option_data["name"]
                original_price = option_data["price"]
                
                if not is_current:
                    try:
                        # Click on the label element
                        print(f"          Clicking on option: {name}")
                        
                        # Scroll the label into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                        time.sleep(0.5)
                        
                        # Try clicking the label directly
                        try:
                            label.click()
                        except:
                            # If direct click fails, try JavaScript click
                            self.driver.execute_script("arguments[0].click();", label)
                        
                        # Wait for car images to load
                        time.sleep(3)
                        
                        # Get the FIRST car preview image
                        car_image_url = self.get_first_car_image()
                        
                        if car_image_url:
                            option_data["car_image"] = car_image_url
                            print(f"            Found car preview image: {car_image_url}")
                        else:
                            print(f"            No car preview image found for {name}")
                        
                        # Check if price changed in selection label
                        try:
                            updated_selection = menu_container.find_element(By.CLASS_NAME, "selection-label")
                            updated_text = updated_selection.text.strip()
                            updated_price = self.extract_price_from_text(updated_text)
                            
                            if updated_price != original_price and updated_price != "$0":
                                print(f"            Price updated to: {updated_price}")
                                option_data["price"] = updated_price
                        except Exception as e:
                            print(f"            Could not check updated price: {e}")
                        
                    except Exception as click_error:
                        print(f"            Could not click option '{name}': {click_error}")
                
                else:
                    # For currently selected option, get its car image too
                    car_image_url = self.get_first_car_image()
                    if car_image_url:
                        option_data["car_image"] = car_image_url
                        print(f"            Found car preview image for selected option: {car_image_url}")
                
                # Add to final options list
                options.append(option_data)
            
            print(f"    Successfully scraped {len(options)} Soft Top options")
            return options
            
        except Exception as e:
            print(f"    Error scraping Soft Top section: {e}")
            return []

    def scrape_section_options(self, section_id, section_name):
        """Scrape options from a specific section (Exterior, Interior, etc.)"""
        print(f"    Scraping {section_name} options...")
        options = []
        
        try:
            # Wait for the section to load
            section_element = self.wait.until(
                EC.presence_of_element_located((By.ID, section_id))
            )

            # Find all menu items in this section
            menu_container = section_element.find_element(By.CLASS_NAME, "menu-container")
            
            # Get the current selection label first
            try:
                selection_label = menu_container.find_element(By.CLASS_NAME, "selection-label")
                current_selection_text = selection_label.text.strip()
                print(f"      Current selection: {current_selection_text}")
            except:
                pass
            
            # Find all palette options
            palettes = menu_container.find_elements(By.CLASS_NAME, "palettes")
            
            print(f"      Found {len(palettes)} palette group(s)")
            
            # Store the current state before we start clicking
            original_options = []
            
            for palette_group_idx, palette_group in enumerate(palettes):
                try:
                    # Find all labels within the palette group
                    palette_labels = palette_group.find_elements(By.TAG_NAME, "label")
                    
                    print(f"        Processing {len(palette_labels)} options in palette group {palette_group_idx + 1}")
                    
                    for label_idx, label in enumerate(palette_labels):
                        try:
                            # Get the actual disabled state - check multiple ways
                            is_disabled = False
                            label_class = label.get_attribute("class") or ""
                            
                            # Check if label has disabled class
                            if "disabled" in label_class:
                                is_disabled = True
                            else:
                                # Check if input is disabled
                                try:
                                    input_elem = label.find_element(By.TAG_NAME, "input")
                                    if input_elem and not input_elem.is_enabled():
                                        is_disabled = True
                                except:
                                    pass
                            
                            # Still process disabled options but mark them
                            is_current = "current" in label_class
                            
                            # Get option name and price from aria-label
                            aria_label = label.get_attribute("aria-label")
                            if not aria_label:
                                # Try to get from img alt
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    aria_label = img.get_attribute("alt")
                                except:
                                    continue
                            
                            if aria_label:
                                # Extract price
                                price = self.extract_price_from_text(aria_label)
                                
                                # Clean up name (remove price if present)
                                name = re.sub(r'\$\s?[\d,]+(?:\.\d{2})?', '', aria_label).strip()
                                name = re.sub(r'\s+', ' ', name)
                                
                                # Get swatch image
                                try:
                                    img = label.find_element(By.TAG_NAME, "img")
                                    swatch_image_url = img.get_attribute("src")
                                except:
                                    swatch_image_url = ""
                                
                                option_data = {
                                    "name": name,
                                    "price": price,
                                    "swatch_image": swatch_image_url,
                                    "car_image": "",
                                    "currently_selected": is_current,
                                    "disabled": is_disabled  # Add this field
                                }
                                
                                # Store original option data
                                original_options.append((label, option_data, is_current))
                                
                                status = []
                                if is_current:
                                    status.append("(selected)")
                                if is_disabled:
                                    status.append("(disabled)")
                                
                                status_str = " ".join(status)
                                print(f"          Found: {name} - {price} {status_str}")
                                
                        except Exception as e:
                            print(f"          Error processing option {label_idx + 1}: {e}")
                            continue
            
                except Exception as e:
                    print(f"        Error processing palette group {palette_group_idx + 1}: {e}")
                    continue
            
            # Now process each option by clicking on the label
            for label, option_data, is_current in original_options:
                name = option_data["name"]
                original_price = option_data["price"]
                is_disabled = option_data.get("disabled", False)
                
                # Skip disabled options for clicking, but still include them in results
                if not is_disabled and not is_current:
                    try:
                        # Click on the label element
                        print(f"          Clicking on option: {name}")
                        
                        # Scroll the label into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                        time.sleep(0.5)
                        
                        # Try clicking the label directly
                        try:
                            label.click()
                        except:
                            # If direct click fails, try JavaScript click
                            self.driver.execute_script("arguments[0].click();", label)
                        
                        # Wait for car images to load (increased wait time)
                        time.sleep(3)
                        
                        # Get the FIRST car preview image
                        car_image_url = self.get_first_car_image()
                        
                        if car_image_url:
                            option_data["car_image"] = car_image_url
                            print(f"            Found car preview image: {car_image_url}")
                        else:
                            print(f"            No car preview image found for {name}")
                        
                        # Check if price changed in selection label
                        try:
                            updated_selection = menu_container.find_element(By.CLASS_NAME, "selection-label")
                            updated_text = updated_selection.text.strip()
                            updated_price = self.extract_price_from_text(updated_text)
                            
                            if updated_price != original_price and updated_price != "$0":
                                print(f"            Price updated to: {updated_price}")
                                option_data["price"] = updated_price
                        except Exception as e:
                            print(f"            Could not check updated price: {e}")
                        
                    except Exception as click_error:
                        print(f"            Could not click option '{name}': {click_error}")
                
                elif is_current:
                    # For currently selected option, get its car image too
                    car_image_url = self.get_first_car_image()
                    if car_image_url:
                        option_data["car_image"] = car_image_url
                        print(f"            Found car preview image for selected option: {car_image_url}")
                
                # Add to final options list (even disabled ones, but mark them)
                options.append(option_data)
            
            # Also check for sub-sections (like EXT_SERIE, EXT_FS_CORSA, etc.)
            try:
                sub_sections = menu_container.find_elements(By.CLASS_NAME, "sub-section")
                print(f"      Found {len(sub_sections)} sub-section(s)")
                
                for sub_section in sub_sections:
                    try:
                        # Get sub-section name
                        sub_name = ""
                        try:
                            sub_title = sub_section.find_element(By.TAG_NAME, "b")
                            sub_name = sub_title.text.strip()
                        except:
                            pass
                        
                        if sub_name:
                            print(f"        Processing sub-section: {sub_name}")
                        
                        # Process palettes in sub-section
                        sub_palettes = sub_section.find_elements(By.CLASS_NAME, "palettes")
                        for palette_group in sub_palettes:
                            palette_labels = palette_group.find_elements(By.TAG_NAME, "label")
                            for label in palette_labels:
                                # Check if this option is already in our list
                                try:
                                    aria_label = label.get_attribute("aria-label")
                                    if aria_label:
                                        # Check if this option already exists
                                        name = re.sub(r'\$\s?[\d,]+(?:\.\d{2})?', '', aria_label).strip()
                                        name = re.sub(r'\s+', ' ', name)
                                        
                                        # Add sub-section name to option name
                                        if sub_name:
                                            name = f"{sub_name} - {name}"
                                        
                                        # Check if this option is already in our list
                                        option_exists = any(opt.get("name") == name for opt in options)
                                        if not option_exists:
                                            # Process this new option
                                            price = self.extract_price_from_text(aria_label)
                                            
                                            # Get swatch image
                                            try:
                                                img = label.find_element(By.TAG_NAME, "img")
                                                swatch_image_url = img.get_attribute("src")
                                            except:
                                                swatch_image_url = ""
                                            
                                            option_data = {
                                                "name": name,
                                                "price": price,
                                                "swatch_image": swatch_image_url,
                                                "car_image": "",  # Would need to click to get this
                                                "currently_selected": "current" in label.get_attribute("class"),
                                                "disabled": "disabled" in label.get_attribute("class")
                                            }
                                            
                                            options.append(option_data)
                                            print(f"          ✓ {name} - {price}")
                                except Exception as e:
                                    print(f"          Error processing sub-section label: {e}")
                                    continue
                    except Exception as e:
                        print(f"        Error processing sub-section: {e}")
                        continue
                        
            except Exception as e:
                print(f"      No sub-sections found or error: {e}")
            
            print(f"    Successfully scraped {len(options)} {section_name} options")
            return options
            
        except Exception as e:
            print(f"    Error scraping {section_name} section: {e}")
            return []
        
    def scrape_options_section(self):
        """Scrape Options section - click 'Show More' until all options are loaded"""
        print("    Scraping Options...")
        options = []
        
        try:
            options_container = self.driver.find_element(By.ID, "optionals")
            
            # Click "Show More" button until it becomes "Hide More Options"
            show_more_clicked = False
            max_clicks = 10  # Safety limit to prevent infinite loop
            
            for click_count in range(max_clicks):
                try:
                    # Look for the show/hide more button
                    show_more_btn = options_container.find_element(By.CSS_SELECTOR, "button.btn-expanded")
                    btn_text_element = options_container.find_element(By.CSS_SELECTOR, ".btn-container span")
                    btn_text = btn_text_element.text.strip() if btn_text_element else ""
                    
                    print(f"      Button text: '{btn_text}'")
                    
                    # Check if button says "Show More Options" or similar
                    if "show" in btn_text.lower() or "plus" in show_more_btn.get_attribute("class"):
                        print(f"      Clicking 'Show More' button (click {click_count + 1})")
                        self.safe_click(show_more_btn, "Show More button")
                        show_more_clicked = True
                        time.sleep(2)  # Wait for more options to load
                        
                        # Check if button state changed
                        try:
                            updated_btn = options_container.find_element(By.CSS_SELECTOR, "button.btn-expanded")
                            if "minus" in updated_btn.get_attribute("class"):
                                print("      All options loaded (button now shows 'Hide')")
                                break
                        except:
                            pass
                    elif "hide" in btn_text.lower() or "minus" in show_more_btn.get_attribute("class"):
                        print("      All options already loaded")
                        break
                    else:
                        # Unknown button state, break to avoid infinite loop
                        print(f"      Unknown button state, stopping")
                        break
                        
                except NoSuchElementException:
                    print("      No 'Show More' button found")
                    break
                except Exception as e:
                    print(f"      Error clicking 'Show More' button: {e}")
                    break
            
            if show_more_clicked:
                print("      Finished loading all options")
            
            # Now scrape all the loaded options
            optional_cards = options_container.find_elements(By.CLASS_NAME, "optional-card")
            
            print(f"      Found {len(optional_cards)} option(s) after loading all")
            
            for card in optional_cards:
                try:
                    # Get option name
                    name_element = card.find_element(By.CLASS_NAME, "card-title")
                    name = name_element.text.strip()
                    
                    # Get price
                    price_element = card.find_element(By.CLASS_NAME, "price")
                    price_html = price_element.get_attribute("innerHTML")
                    
                    # Check if price is crossed out (in package) or regular
                    if "<del>" in price_html:
                        # Price is crossed out (included in package)
                        try:
                            del_element = price_element.find_element(By.TAG_NAME, "del")
                            price = del_element.text.strip()
                            is_in_package = True
                        except:
                            price = price_element.text.strip()
                            is_in_package = False
                    else:
                        price = price_element.text.strip()
                        is_in_package = False
                    
                    # Get image
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        image_url = img.get_attribute("src")
                    except:
                        image_url = ""
                    
                    # Check if option is already selected
                    is_selected = "optionSelected" in card.get_attribute("class")
                    
                    # Check availability based on button state
                    try:
                        # Look for add button
                        add_button = card.find_element(By.CSS_SELECTOR, "button.add")
                        is_available = True
                    except:
                        try:
                            # Look for remove button (option is selected)
                            remove_button = card.find_element(By.CSS_SELECTOR, "button.remove")
                            is_available = True
                            is_selected = True
                        except:
                            # Look for status text (not available, in package, etc.)
                            try:
                                status_element = card.find_element(By.CLASS_NAME, "status")
                                status_text = status_element.text.strip().lower()
                                is_available = False
                                if "in package" in status_text:
                                    is_in_package = True
                            except:
                                is_available = False
                    
                    option_data = {
                        "name": name,
                        "price": price,
                        "image": image_url,
                        "available": is_available,
                        "selected": is_selected,
                        "in_package": is_in_package
                    }
                    
                    options.append(option_data)
                    print(f"        ✓ {name} - {price} {'(selected)' if is_selected else ''} {'(in package)' if is_in_package else ''}")
                    
                except Exception as e:
                    print(f"        Error processing option card: {e}")
                    continue
            
            print(f"    Successfully scraped {len(options)} Options")
            return options
            
        except Exception as e:
            print(f"    Error scraping Options section: {e}")
            return []

    def scrape_packages_section(self):
        """Scrape Packages section"""
        print("    Scraping Packages options...")
        options = []
        
        try:
            packages_container = self.driver.find_element(By.ID, "PacksContainer")
            
            # Check if there's a "Show More" button specifically for packages
            # Look for it in the entire document, not just in packages_container
            show_more_clicked = False
            max_clicks = 1
            
            for click_count in range(max_clicks):
                try:
                    # Look for show more button - check multiple possible selectors
                    show_more_selectors = [
                        "button[aria-label*='Show More']",
                        "button[aria-label*='More packages']",
                        "button.btn-expanded",
                        ".btn-expanded",
                        "button[class*='show-more']",
                        ".show-more",
                        "button[aria-expanded='false']",  # Button that's collapsed/not expanded
                        "span:contains('Show More') + button",  # Button next to "Show More" text
                    ]
                    
                    found_button = False
                    for selector in show_more_selectors:
                        try:
                            # Search in entire document
                            buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for btn in buttons:
                                try:
                                    # Get button text from various sources
                                    btn_text = ""
                                    try:
                                        # Get text from the button itself
                                        btn_text = btn.text.strip().lower()
                                    except:
                                        pass
                                    
                                    # Get aria-label
                                    aria_label = btn.get_attribute("aria-label") or ""
                                    
                                    # Get class
                                    btn_class = btn.get_attribute("class") or ""
                                    
                                    # Check if this looks like a show more button
                                    is_show_more = (
                                        "show" in btn_text or 
                                        "show" in aria_label.lower() or 
                                        "plus" in btn_class or 
                                        "expand" in btn_class or
                                        "more" in btn_text or
                                        "more" in aria_label.lower()
                                    )
                                    
                                    if is_show_more:
                                        print(f"      Found 'Show More' button with selector: {selector}")
                                        print(f"      Clicking 'Show More' for packages (click {click_count + 1})")
                                        self.safe_click(btn, "Show More packages button")
                                        show_more_clicked = True
                                        found_button = True
                                        time.sleep(2)  # Wait for packages to load
                                        
                                        # Check if more packages appeared
                                        current_packages = packages_container.find_elements(By.CLASS_NAME, "pack-card")
                                        print(f"      Now showing {len(current_packages)} packages")
                                        break
                                except Exception as e:
                                    print(f"      Error with button: {e}")
                                    continue
                            
                            if found_button:
                                break
                        except:
                            continue
                    
                    if not found_button:
                        print(f"      No 'Show More' button found for packages (attempt {click_count + 1})")
                        
                        # Also check for "Load More" text near the last visible package
                        try:
                            # Look for the "data-last-visible" attribute which indicates pagination
                            last_visible = packages_container.find_element(By.CSS_SELECTOR, "[data-last-visible]")
                            last_visible_num = last_visible.get_attribute("data-last-visible")
                            print(f"      Last visible package index: {last_visible_num}")
                            
                            # Try to find a button to load more (might be dynamically added)
                            time.sleep(1)  # Wait a bit
                        except:
                            pass
                        
                        break  # No button found, break the loop
                        
                except NoSuchElementException:
                    print("      No 'Show More' button found (NoSuchElementException)")
                    break
                except Exception as e:
                    print(f"      Error looking for 'Show More' button: {e}")
                    break
            
            if show_more_clicked:
                print("      Finished attempting to load all packages")
            
            # Now scrape all the packages
            pack_cards = packages_container.find_elements(By.CLASS_NAME, "pack-card")
            
            print(f"      Found {len(pack_cards)} package(s)")
            
            for card in pack_cards:
                try:
                    # Get package name
                    name_element = card.find_element(By.CLASS_NAME, "card-title")
                    name = name_element.text.strip()
                    
                    # Get price
                    try:
                        price_element = card.find_element(By.CLASS_NAME, "price")
                        price = price_element.text.strip()
                    except:
                        price = "$0"
                    
                    # Get image
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        image_url = img.get_attribute("src")
                    except:
                        image_url = ""
                    
                    # Check if add button is available
                    try:
                        add_button = card.find_element(By.CSS_SELECTOR, "button.add")
                        is_disabled = "disabled" in add_button.get_attribute("class")
                        is_available = not is_disabled
                        is_added = False
                        
                        # Check if button says "Remove" (already added)
                        try:
                            remove_span = add_button.find_element(By.CSS_SELECTOR, "span[data-key='REMOVE_OPT']")
                            is_added = True
                            is_available = True
                        except:
                            pass
                            
                    except NoSuchElementException:
                        # No add button found
                        try:
                            # Check for remove button
                            remove_button = card.find_element(By.CSS_SELECTOR, "button.remove")
                            is_available = True
                            is_added = True
                        except:
                            is_available = False
                            is_added = False
                    except Exception as e:
                        print(f"        Error checking button: {e}")
                        is_available = False
                        is_added = False
                    
                    # Try to get features list
                    features = []
                    try:
                        features_container = card.find_element(By.CLASS_NAME, "features")
                        feature_lists = features_container.find_elements(By.TAG_NAME, "ul")
                        
                        for feature_list in feature_lists:
                            feature_items = feature_list.find_elements(By.TAG_NAME, "li")
                            for feature in feature_items:
                                features.append(feature.text.strip())
                    except:
                        pass
                    
                    option_data = {
                        "name": name,
                        "price": price,
                        "image": image_url,
                        "available": is_available,
                        "added": is_added,
                        "features": features
                    }
                    
                    options.append(option_data)
                    status = ""
                    if is_added:
                        status = "(added)"
                    elif not is_available:
                        status = "(unavailable)"
                    print(f"        ✓ {name} - {price} {status}")
                    
                except Exception as e:
                    print(f"        Error processing package card: {e}")
                    continue
            
            print(f"    Successfully scraped {len(options)} Packages")
            return options
            
        except Exception as e:
            print(f"    Error scraping Packages section: {e}")
            return []

    def get_car_preview_images(self):
        """Extract the car preview images from the main carousel"""
        print("    Extracting car preview images...")
        car_images = []
        
        try:
            # Find the main carousel - there may be multiple on the page
            carousels = self.driver.find_elements(By.CSS_SELECTOR, ".carousel.slick-initialized")
            
            for i, carousel in enumerate(carousels):
                # Look for img tags with class 'cc-img' (these are the actual car images)
                car_images_in_carousel = carousel.find_elements(By.CSS_SELECTOR, "img.cc-img")
                
                for img_idx, img in enumerate(car_images_in_carousel):
                    try:
                        img_src = img.get_attribute("src")
                        if img_src and "gfx" in img_src:
                            # Extract the view angle/number from the URL if possible
                            angle_match = re.search(r'gfx(\d+)', img_src)
                            angle = angle_match.group(1) if angle_match else str(img_idx + 1)
                            
                            car_images.append({
                                "url": img_src,
                                "angle": angle,
                                "description": f"View {angle}"
                            })
                            print(f"      ✓ Found car image: {img_src}")
                    except:
                        continue
            
            # Also check for images inside figure elements
            figure_elements = self.driver.find_elements(By.CSS_SELECTOR, "figure.carousel-image-container img")
            for figure_img in figure_elements:
                try:
                    img_src = figure_img.get_attribute("src")
                    if img_src and img_src not in [img["url"] for img in car_images] and "gfx" in img_src:
                        angle_match = re.search(r'gfx(\d+)', img_src)
                        angle = angle_match.group(1) if angle_match else str(len(car_images) + 1)
                        
                        car_images.append({
                            "url": img_src,
                            "angle": angle,
                            "description": f"View {angle}"
                        })
                        print(f"      ✓ Found car image in figure: {img_src}")
                except:
                    continue
            
            print(f"    Found {len(car_images)} car preview images")
            return car_images
            
        except Exception as e:
            print(f"    Error extracting car preview images: {e}")
            return []
    
    def navigate_to_category(self, category_name):
        """Navigate to a specific category using the tabs"""
        print(f"  Navigating to {category_name}...")
        
        try:
            # For categories that are in the Exterior tab (Wheels, Brake Calipers),
            # we need to navigate to Exterior first, then scroll
            if category_name in ["Wheels", "Brake Calipers", "Trim"]:
                # First navigate to Exterior if not already there
                try:
                    ext_tab = self.driver.find_element(By.CSS_SELECTOR, "#MENU_EXT, [aria-label*='EXTERIOR']")
                    if "active" not in ext_tab.get_attribute("class"):
                        self.safe_click(ext_tab, "Exterior tab")
                        time.sleep(2)
                except:
                    pass
            
            # Now try to find and scroll to the section
            section_ids = {
                "Exterior": "MENU_EXT",
                "Interior": "MENU_INT", 
                "Wheels": "RIMS_section",
                "Brake Calipers": "CAL_section",
                "Trim": "TRIM_section",
                "Liveries and Dreamlines": "LIVREE_section",
                "Liveries": "LIVREE_section",
                "Soft Top": "SFT_section",
                "Packages": "PacksContainer",
                "Options": "optionals"
            }
            
            section_id = section_ids.get(category_name)
            if section_id:
                try:
                    # Try to find by ID first
                    element = self.driver.find_element(By.ID, section_id)
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", element)
                    time.sleep(2)
                    print(f"    Found and scrolled to {category_name} section")
                    return True
                except:
                    # Try alternative selectors
                    alternative_selectors = {
                        "Exterior": ["section[aria-label*='EXTERIOR']", "[data-path='EXT']"],
                        "Interior": ["section[aria-label*='INTERIOR']", "[data-path='INT']"],
                        "Packages": [".packs-container"],
                        "Options": [".options-container"]
                    }
                    
                    selectors = alternative_selectors.get(category_name, [])
                    for selector in selectors:
                        try:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", element)
                            time.sleep(2)
                            print(f"    Found {category_name} section using alternative selector")
                            return True
                        except:
                            continue
            
            print(f"    Could not find {category_name} section")
            return False
            
        except Exception as e:
            print(f"    Error navigating to {category_name}: {e}")
            return False
        
    def scrape_trim_section_robust(self):
        """Robust method to scrape all trim options, including those in sub-sections"""
        print("    Scraping Trim section with robust method...")
        options = []
        
        try:
            # Wait for the section to load
            section_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "TRIM_section"))
            )
            
            # Find all menu items in this section
            menu_container = section_element.find_element(By.CLASS_NAME, "menu-container")
            
            # Get the current selection label first
            try:
                selection_label = menu_container.find_element(By.CLASS_NAME, "selection-label")
                current_selection_text = selection_label.text.strip()
                print(f"      Current selection: {current_selection_text}")
            except:
                pass
            
            # METHOD 1: Find ALL labels in the entire TRIM section
            all_labels = menu_container.find_elements(By.TAG_NAME, "label")
            print(f"      Found {len(all_labels)} total label(s) in TRIM section")
            
            # Store unique options to avoid duplicates
            seen_options = set()
            
            for label_idx, label in enumerate(all_labels):
                try:
                    # Get option name and price from aria-label
                    aria_label = label.get_attribute("aria-label")
                    if not aria_label:
                        # Try to get from img alt
                        try:
                            img = label.find_element(By.TAG_NAME, "img")
                            aria_label = img.get_attribute("alt")
                        except:
                            continue
                    
                    if aria_label and aria_label.strip():
                        # Extract price
                        price = self.extract_price_from_text(aria_label)
                        
                        # Clean up name (remove price if present)
                        name = re.sub(r'\$\s?[\d,]+(?:\.\d{2})?', '', aria_label).strip()
                        name = re.sub(r'\s+', ' ', name)  # Clean extra spaces
                        
                        # Skip if we've already seen this option (prevent duplicates)
                        option_key = f"{name}_{price}"
                        if option_key in seen_options:
                            continue
                        
                        seen_options.add(option_key)
                        
                        # Check if this is the currently selected option
                        is_current = "current" in label.get_attribute("class")
                        
                        # Check if disabled
                        is_disabled = "disabled" in label.get_attribute("class")
                        
                        # Get the swatch image URL
                        try:
                            img = label.find_element(By.TAG_NAME, "img")
                            swatch_image_url = img.get_attribute("src")
                        except:
                            swatch_image_url = ""
                        
                        # Get parent sub-section name if available
                        subsection_name = ""
                        try:
                            # Find the closest sub-section
                            subsection = label.find_element(By.XPATH, "./ancestor::div[contains(@class, 'sub-section')]")
                            subsection_title = subsection.find_element(By.TAG_NAME, "b")
                            subsection_name = subsection_title.text.strip()
                        except:
                            pass
                        
                        # Include subsection name in option name
                        final_name = name
                        if subsection_name:
                            final_name = f"{subsection_name} - {name}"
                        
                        option_data = {
                            "name": final_name,
                            "price": price,
                            "swatch_image": swatch_image_url,
                            "car_image": "",  # Will be filled after clicking
                            "currently_selected": is_current,
                            "disabled": is_disabled,
                            "subsection": subsection_name
                        }
                        
                        options.append(option_data)
                        
                        status = []
                        if is_current:
                            status.append("(selected)")
                        if is_disabled:
                            status.append("(disabled)")
                        if subsection_name:
                            status.append(f"[{subsection_name}]")
                        
                        status_str = " ".join(status)
                        print(f"        Found: {final_name} - {price} {status_str}")
                        
                except Exception as e:
                    print(f"        Error processing label {label_idx + 1}: {e}")
                    continue
            
            # METHOD 2: Also process by sub-sections (for better organization)
            try:
                sub_sections = menu_container.find_elements(By.CLASS_NAME, "sub-section")
                print(f"      Also found {len(sub_sections)} sub-section(s)")
                
                for sub_idx, sub_section in enumerate(sub_sections):
                    try:
                        # Get sub-section name
                        sub_name = ""
                        try:
                            sub_title = sub_section.find_element(By.TAG_NAME, "b")
                            sub_name = sub_title.text.strip()
                        except:
                            sub_name = f"Sub-section {sub_idx + 1}"
                        
                        # Process labels in this sub-section
                        sub_labels = sub_section.find_elements(By.TAG_NAME, "label")
                        
                        # We've already processed all labels above, but we can use this
                        # to verify we got everything
                        if sub_labels:
                            print(f"        Sub-section '{sub_name}' has {len(sub_labels)} label(s)")
                            
                    except Exception as e:
                        print(f"        Error processing sub-section {sub_idx + 1}: {e}")
                        continue
            except Exception as e:
                print(f"      Error finding sub-sections: {e}")
            
            # Now click on each unique option to get car images
            print(f"      Processing {len(options)} unique trim options for car images...")
            
            # Keep track of current selection to return to it at the end
            current_selection = None
            
            for i, option in enumerate(options):
                try:
                    name = option["name"]
                    original_price = option["price"]
                    is_current = option["currently_selected"]
                    
                    # Save the first current selection
                    if is_current and current_selection is None:
                        current_selection = option
                    
                    # Skip clicking if it's already selected or disabled
                    if is_current:
                        # For currently selected option, get its car image
                        car_image_url = self.get_first_car_image()
                        if car_image_url:
                            option["car_image"] = car_image_url
                            print(f"          ✓ Selected option '{name}' - car image captured")
                        continue
                    
                    if option.get("disabled", False):
                        print(f"          ⚠ Skipping disabled option '{name}'")
                        continue
                    
                    # Find the label for this option again
                    try:
                        # Try to find by aria-label content
                        label = None
                        for lbl in all_labels:
                            try:
                                aria_lbl = lbl.get_attribute("aria-label")
                                if aria_lbl and name in aria_lbl:
                                    label = lbl
                                    break
                            except:
                                continue
                        
                        if label:
                            # Click on the label element
                            print(f"          Clicking on option {i+1}/{len(options)}: {name}")
                            
                            # Scroll the label into view
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", label)
                            time.sleep(1)
                            
                            # Try clicking using JavaScript
                            self.driver.execute_script("arguments[0].click();", label)
                            
                            # Wait for update
                            time.sleep(2)
                            
                            # Get the car preview image
                            car_image_url = self.get_first_car_image()
                            
                            if car_image_url:
                                option["car_image"] = car_image_url
                                print(f"            ✓ Car image captured")
                            else:
                                print(f"            ⚠ No car image found")
                            
                            # Check if price changed
                            try:
                                updated_selection = menu_container.find_element(By.CLASS_NAME, "selection-label")
                                updated_text = updated_selection.text.strip()
                                updated_price = self.extract_price_from_text(updated_text)
                                
                                if updated_price != original_price and updated_price != "$0":
                                    print(f"            Price updated to: {updated_price}")
                                    option["price"] = updated_price
                            except:
                                pass
                                
                        else:
                            print(f"          ⚠ Could not find label for option '{name}'")
                            
                    except Exception as click_error:
                        print(f"          ❌ Error clicking option '{name}': {click_error}")
                    
                except Exception as e:
                    print(f"          ❌ Error processing option {i+1}: {e}")
                    continue
            
            # Return to original selection if we changed it
            if current_selection and len(options) > 1:
                try:
                    print(f"      Returning to original selection: {current_selection['name']}")
                    # Find and click the original selection
                    for label in all_labels:
                        try:
                            if "current" in label.get_attribute("class"):
                                self.driver.execute_script("arguments[0].click();", label)
                                time.sleep(1)
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"      Error returning to original selection: {e}")
            
            print(f"    Successfully scraped {len(options)} unique trim options")
            return options
            
        except Exception as e:
            print(f"    Error scraping Trim section: {e}")
            import traceback
            traceback.print_exc()
            return []

    def scrape_all_categories(self):
        """Scrape all available categories"""
        print("\n  Starting to scrape all categories...")
        
        result = {}
        
        # Define categories to scrape - updated to check if sections exist
        categories_to_check = [
            ("Exterior", "EXT_section", self.scrape_section_options),
            ("Interior", "INT_section", self.scrape_section_options),
            ("Trim", "TRIM_section", self.scrape_trim_section_robust),  # CHANGED THIS LINE
            ("Wheels", "RIMS_section", self.scrape_section_options),
            ("Brake Calipers", "CAL_section", self.scrape_section_options),
            ("Liveries and Dreamlines", None, self.scrape_liveries_section),
            ("Soft Top", None, self.scrape_soft_top_section),
            ("Packages", None, self.scrape_packages_section),
            ("Options", None, self.scrape_options_section)
        ]
        
        # First, try to scrape the main exterior section which contains multiple categories
        print(f"\n  --- Exterior ---")
        if self.navigate_to_category("Exterior"):
            time.sleep(2)
            
            # Scrape Exterior Color
            exterior_options = self.scrape_section_options("EXT_section", "Exterior Color")
            result["exterior_color"] = exterior_options
            
            # Now check for other sections that might be in the same tab
            try:
                # Check if Wheels section exists
                print(f"\n  --- Wheels ---")
                wheels_section = self.driver.find_elements(By.ID, "RIMS_section")
                if wheels_section:
                    wheels_options = self.scrape_section_options("RIMS_section", "Wheels")
                    result["wheels"] = wheels_options
                else:
                    print("    Wheels section not found in current view")
                    result["wheels"] = []
            except Exception as e:
                print(f"    Error checking Wheels section: {e}")
                result["wheels"] = []
            
            try:
                # Check if Brake Calipers section exists
                print(f"\n  --- Brake Calipers ---")
                cal_section = self.driver.find_elements(By.ID, "CAL_section")
                if cal_section:
                    cal_options = self.scrape_section_options("CAL_section", "Brake Calipers")
                    result["brake_calipers"] = cal_options
                else:
                    print("    Brake Calipers section not found in current view")
                    result["brake_calipers"] = []
            except Exception as e:
                print(f"    Error checking Brake Calipers section: {e}")
                result["brake_calipers"] = []
        else:
            result["exterior_color"] = []
            result["wheels"] = []
            result["brake_calipers"] = []
            print(f"  ✗ Exterior section not found")
        
        # Scrape Interior (separate tab/section)
        print(f"\n  --- Interior ---")
        if self.navigate_to_category("Interior"):
            time.sleep(2)
            interior_options = self.scrape_section_options("INT_section", "Interior")
            result["interior"] = interior_options
        else:
            result["interior"] = []
            print(f"  ✗ Interior section not found")
        
        # Scrape Trim using the robust method
        print(f"\n  --- Trim ---")
        try:
            # First try to find it on the page
            trim_section = self.driver.find_elements(By.ID, "TRIM_section")
            if trim_section:
                # Use a more robust trim scraping method
                trim_options = self.scrape_trim_section_robust()
                result["trim"] = trim_options
            else:
                # Try to navigate to it
                if self.navigate_to_category("Trim"):
                    time.sleep(2)
                    # Try to find it again after navigation
                    trim_section = self.driver.find_elements(By.ID, "TRIM_section")
                    if trim_section:
                        trim_options = self.scrape_trim_section_robust()
                        result["trim"] = trim_options
                    else:
                        print("    Trim section not found after navigation")
                        result["trim"] = []
                else:
                    print("    Could not navigate to Trim section")
                    result["trim"] = []
        except Exception as e:
            print(f"    Error checking Trim section: {e}")
            result["trim"] = []
        
        # Scrape other sections
        other_categories = [
            ("Liveries and Dreamlines", None, self.scrape_liveries_section),
            ("Soft Top", None, self.scrape_soft_top_section),
            ("Packages", None, self.scrape_packages_section),
            ("Options", None, self.scrape_options_section)
        ]
        
        for category_name, section_id, scrape_function in other_categories:
            try:
                print(f"\n  --- {category_name} ---")
                
                if self.navigate_to_category(category_name):
                    time.sleep(2)
                    options = scrape_function()
                else:
                    options = []
                
                if options:
                    result[category_name.lower().replace(" ", "_")] = options
                    print(f"  ✓ {category_name}: {len(options)} options found")
                else:
                    result[category_name.lower().replace(" ", "_")] = []
                    print(f"  ✗ {category_name}: No options found")
                    
            except Exception as e:
                print(f"  ✗ Error scraping {category_name}: {e}")
                result[category_name.lower().replace(" ", "_")] = []
        
        # Also check for Highlights if present
        try:
            print("\n  --- Highlights ---")
            highlights = self.driver.find_elements(By.CLASS_NAME, "pack-card-highlights")
            if highlights:
                highlight_options = []
                for highlight in highlights:
                    try:
                        name = highlight.find_element(By.CLASS_NAME, "highlights-content-first-row").text.strip()
                        price_element = highlight.find_element(By.CLASS_NAME, "highlights-content-price")
                        price = price_element.text.strip()
                        
                        try:
                            img = highlight.find_element(By.TAG_NAME, "img")
                            image_url = img.get_attribute("src")
                        except:
                            image_url = ""
                        
                        highlight_options.append({
                            "name": name,
                            "price": price,
                            "image": image_url
                        })
                        print(f"    ✓ Highlight: {name} - {price}")
                    except:
                        continue
                
                if highlight_options:
                    result["highlights"] = highlight_options
        except:
            pass
        
        return result

    def process_model(self, model):
        """Process a single car model"""
        print(f"\n📦 Processing: {model['name']}")
        
        try:
            model_data = {
                "name": model["name"],
                "base_price": model["price"],
                "base_image": model["image"],
                "url": model["link"],
                "configurations": []
            }
            
            print(f"  Navigating to: {model['link']}")
            self.driver.get(model['link'])
            time.sleep(5)
            
            self.handle_popups()
            time.sleep(3)
            
            # Wait for page to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "menu-container"))
                )
                print("  ✓ Page loaded successfully")
            except:
                print("  ⚠️ Page loaded but menu containers not immediately visible")
            
            print("\n  Starting category scraping...")
            all_categories_data = self.scrape_all_categories()
            
            configuration_data = {
                "configuration_name": "Default Configuration",
                "categories": all_categories_data
            }
            
            model_data["configurations"].append(configuration_data)
            
            print(f"\n  ✅ Successfully processed {model['name']}")
            print(f"     Categories scraped: {len(all_categories_data)}")
            
            total_options = sum(len(options) for options in all_categories_data.values())
            print(f"     Total options found: {total_options}")
            
            return model_data
            
        except Exception as e:
            print(f"  ❌ Error processing model {model['name']}: {e}")
            import traceback
            traceback.print_exc()
            return model_data
    
    def update_global_data(self, current_model):
        """Update the global data structure"""
        model_found = False
        for i, model in enumerate(self.data):
            if model.get("url") == current_model["url"]:
                self.data[i] = current_model
                model_found = True
                break
        
        if not model_found:
            self.data.append(current_model)
        
        self.save_json(self.data)
    
    def run(self):
        """Run the scraper"""
        print("🚀 Starting Maserati Car Scraper")
        print("=" * 60)
        
        try:
            models = self.load_initial_models()
            print(f"Loaded {len(models)} model(s) to scrape")
            
            for model_idx, model in enumerate(models):
                print(f"\n📋 Processing model {model_idx+1}/{len(models)}")
                model_data = self.process_model(model)
                
                self.update_global_data(model_data)
                
                print(f"\n✅ Completed: {model['name']}")
                print(f"   Configurations scraped: {len(model_data['configurations'])}")
                
                if model_idx < len(models) - 1:
                    print("   Waiting before next model...")
                    time.sleep(3)
            
            print("\n" + "=" * 60)
            print("🎉 All scraping completed!")
            print(f"📊 Total models processed: {len(self.data)}")
            
            total_configs = sum(len(model.get('configurations', [])) for model in self.data)
            print(f"📈 Total configurations scraped: {total_configs}")
            print(f"💾 Data saved to: {self.output_file}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            try:
                self.driver.quit()
                print("👋 Browser closed")
            except:
                pass

# Run the scraper
if __name__ == "__main__":
    scraper = MaseratiScraper()
    scraper.run()
