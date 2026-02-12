import time
import json
import base64
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image
import io
import cloudinary
import cloudinary.uploader
import cloudinary.api
import re

class MiniColorScraper:
    def __init__(self, url, model_data, cloudinary_config=None):
        """
        Initialize the scraper with the target URL and model data
        """
        self.url = url
        self.model_data = model_data
        self.driver = None
        self.configurations = []
        self.output_dir = "mini_color_screenshots"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Configure Cloudinary
        if cloudinary_config:
            cloudinary.config(
                cloud_name=cloudinary_config['cloud_name'],
                api_key=cloudinary_config['api_key'],
                api_secret=cloudinary_config['api_secret']
            )
            self.cloudinary_enabled = True
            print("✓ Cloudinary configured successfully")
        else:
            self.cloudinary_enabled = False
            print("⚠ Cloudinary not configured - images will only be saved locally")
    
    def sanitize_filename(self, filename):
        """
        Sanitize filename for Windows compatibility
        Remove invalid characters: / : * ? " < > |
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*"\''
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Also remove double quotes specifically
        filename = filename.replace('"', 'inch').replace('"', 'inch').replace('"', 'inch')
        # Remove multiple consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores and spaces
        filename = filename.strip(' _')
        # Limit length to avoid Windows path issues
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def upload_to_cloudinary(self, image_base64, category_name, option_name, index):
        """
        Upload base64 image to Cloudinary
        
        Args:
            image_base64: Base64 encoded image string
            category_name: Category name (e.g., exterior_colors, wheels)
            option_name: Name of the option
            index: Index of the option
        
        Returns:
            Cloudinary URL or None if upload fails
        """
        if not self.cloudinary_enabled or not image_base64:
            return None
        
        try:
            # Create a safe public_id
            safe_model_name = self.model_data['name'].replace(' ', '_').replace('/', '_').lower()
            safe_category = category_name.replace(' ', '_').lower()
            safe_option_name = self.sanitize_filename(option_name).replace(' ', '_').replace('/', '_').replace("'", '').lower()
            
            public_id = f"mini_cooper_cars/{safe_model_name}/{safe_category}/{safe_category}_{index}_{safe_option_name}"
            
            # Prepare the data URI for Cloudinary
            data_uri = f"data:image/png;base64,{image_base64}"
            
            # Upload to Cloudinary
            print(f"      Uploading to Cloudinary...")
            response = cloudinary.uploader.upload(
                data_uri,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                folder=f"mini_cooper_cars/{safe_model_name}/{safe_category}"
            )
            
            print(f"      ✓ Uploaded: {response['secure_url'][:80]}...")
            return response['secure_url']
            
        except Exception as e:
            print(f"      ✗ Error uploading to Cloudinary: {e}")
            return None
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        options = webdriver.ChromeOptions()
        # Remove headless for debugging
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # Add user agent to mimic real browser
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
    
    def navigate_to_url(self):
        """Navigate to the target URL and wait for page to load"""
        print(f"Navigating to URL: {self.url}")
        self.driver.get(self.url)
        
        # Wait longer for SPA to load
        time.sleep(5)
        
        # Try to dismiss any cookie banners
        self.dismiss_cookie_banner()
        
        # Wait for the page to fully load
        self.wait_for_page_load()
    
    def dismiss_cookie_banner(self):
        """Try to dismiss cookie consent banner if present"""
        try:
            # Common cookie banner selectors for MINI site
            cookie_selectors = [
                '#onetrust-accept-btn-handler',
                'button[id*="cookie"]',
                'button[class*="cookie"]',
                'button:contains("Accept")',
                'button:contains("Got it")',
                'button:contains("OK")',
                '.cookie-accept',
                '.cc-dismiss'
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_button.is_displayed():
                        cookie_button.click()
                        print("Cookie banner dismissed")
                        time.sleep(1)
                        break
                except:
                    continue
        except Exception as e:
            print(f"No cookie banner found or error dismissing: {e}")
    
    def wait_for_page_load(self):
        """Wait for the page to fully load"""
        try:
            # Wait for body to be present
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print("Page body loaded")
            
            # Additional wait for SPA content
            time.sleep(3)
            
        except TimeoutException:
            print("Timeout waiting for page to load")
    
    def find_car_preview_section(self):
        """Find the car preview section using multiple selectors"""
        selectors = [
            ".stage-view-color",
            ".stage-view",
            ".stage-view-wheel",  # Added for wheels
            "[class*='stage-view']",
            "[class*='stage']",
            "[class*='view']",
            "[class*='car']",
            "[class*='preview']",
            "[class*='visualization']",
            "#stage-view",
            ".byo-3d-viewer",
            ".vehicle-visualization"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.size['height'] > 100 and element.size['width'] > 100:
                    print(f"    Found preview section with selector: {selector}")
                    return element
            except:
                continue
        
        # Try to find any large image or canvas element
        try:
            # Look for canvas elements (3D viewer)
            canvas_elements = self.driver.find_elements(By.TAG_NAME, "canvas")
            for canvas in canvas_elements:
                if canvas.is_displayed() and canvas.size['height'] > 200:
                    print("    Found preview section: canvas element")
                    return canvas.find_element(By.XPATH, "./ancestor::div[1]")
        except:
            pass
        
        print("    Could not find car preview section")
        return None
    
    def get_category_name(self, section_title):
        """Determine category name from section title"""
        title_lower = section_title.lower()
        
        # Check for roof/mirror first (before exterior colors)
        if "roof" in title_lower or "mirror" in title_lower or "cap" in title_lower:
            return "roof_mirror_caps"
        elif "body color" in title_lower or "exterior color" in title_lower or "paint" in title_lower:
            return "exterior_colors"
        elif "wheel" in title_lower or "rim" in title_lower:
            return "wheels"
        elif "interior" in title_lower or "upholstery" in title_lower or "fabric" in title_lower:
            return "interior"
        else:
            return None

    def extract_price(self, container):
        """
        Extract price from option container with proper logic:
        1. Get listprice from byo-rail-option div
        2. Check byo-rail-container__titles--price for "Included" or actual price
        3. If "Included" or empty -> return "$0"
        4. If has price text -> use listprice value
        
        Args:
            container: The option container element
        
        Returns:
            Price string (e.g., "$500" or "$0")
        """
        price = "$0"
        
        try:
            # Step 1: Get listprice from byo-rail-option div
            listprice = None
            try:
                option_div = container.find_element(By.CSS_SELECTOR, ".byo-rail-option")
                listprice = option_div.get_attribute('listprice')
                if not listprice:
                    listprice = option_div.get_attribute('data-listprice')
                if not listprice:
                    listprice = option_div.get_attribute('price')
                if not listprice:
                    listprice = option_div.get_attribute('data-price')
                if listprice:
                    listprice = str(listprice).strip()
                print(f"        Listprice attribute: {listprice}")
            except Exception as e:
                print(f"        Could not find listprice: {e}")
            
            # Step 2: Check the price display element
            price_text = None
            has_price_display = False
            
            try:
                # Try multiple selectors for price element
                price_selectors = [
                    ".byo-rail-container__titles--price",
                    ".byo-rail-option__price",
                    "[class*='price']",
                    ".price"
                ]
                
                price_elem = None
                for selector in price_selectors:
                    try:
                        price_elem = container.find_element(By.CSS_SELECTOR, selector)
                        if price_elem:
                            break
                    except:
                        continue
                
                if price_elem:
                    # Get text content
                    price_text = price_elem.text.strip()
                    if not price_text:
                        price_text = price_elem.get_attribute('innerText')
                    if not price_text:
                        price_text = price_elem.get_attribute('textContent')
                    
                    if price_text:
                        price_text = price_text.strip()
                        print(f"        Price text found: '{price_text}'")
                        has_price_display = price_elem.is_displayed()
            except Exception as e:
                print(f"        Error finding price element: {e}")
            
            # Step 3: Determine the actual price
            print(f"        Decision: has_price_display={has_price_display}, price_text='{price_text}', listprice={listprice}")
            
            # If price text says "Included" or "No charge" -> $0
            if price_text and ("included" in price_text.lower() or "no charge" in price_text.lower()):
                price = "$0"
                print(f"        ✓ Final decision: Included -> $0")
            # If we have a listprice value
            elif listprice and listprice != "" and listprice != "0":
                price = f"${listprice}" if not listprice.startswith('$') else listprice
                print(f"        ✓ Final decision: Using listprice -> {price}")
            # Try to extract from price_text
            elif price_text:
                price_match = re.search(r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text)
                if price_match:
                    price_value = price_match.group(1).replace(',', '')
                    price = f"${price_value}"
                    print(f"        ✓ Final decision: Extracted from text -> {price}")
                else:
                    price = "$0"
            else:
                price = "$0"
                print(f"        ✓ Final decision: No price found -> $0")
                
        except Exception as e:
            print(f"        ✗ Error extracting price: {e}")
            price = "$0"
        
        return price

    def get_all_categories(self):
        """Extract all categories and their options from the page"""
        categories = {
            "exterior_colors": [],
            "roof_mirror_caps": [],
            "wheels": [],
            "interior": []
        }
        
        try:
            # Find all sections
            sections = self.driver.find_elements(By.CSS_SELECTOR, ".rail-section")
            print(f"Found {len(sections)} rail sections")
            
            for section in sections:
                try:
                    # Get section title
                    title_elem = section.find_element(By.CSS_SELECTOR, ".rail-section__title")
                    title_text = title_elem.text if title_elem else "Unknown"
                    
                    # Determine category
                    category_name = self.get_category_name(title_text)
                    
                    if category_name:
                        print(f"\n  Found {category_name} section: {title_text}")
                        
                        # Find all options in this section
                        option_containers = section.find_elements(By.CSS_SELECTOR, ".byo-rail-option-base")
                        
                        if not option_containers:
                            option_containers = section.find_elements(By.CSS_SELECTOR, "[class*='option']")
                        
                        print(f"    Found {len(option_containers)} options in this section")
                        
                        for container in option_containers:
                            try:
                                # Get option name
                                option_name = container.get_attribute('title')
                                
                                if not option_name:
                                    try:
                                        name_elem = container.find_element(
                                            By.CSS_SELECTOR, ".byo-rail-container__titles--name"
                                        )
                                        option_name = name_elem.text
                                    except:
                                        option_name = container.text.split('\n')[0] if container.text else "Unknown Option"
                                
                                # Get price using the new extraction method
                                price = self.extract_price(container)
                                
                                # Get swatch image from byo-rail-option div
                                swatch_image = ""
                                try:
                                    option_div = container.find_element(By.CSS_SELECTOR, ".byo-rail-option")
                                    swatch_image = option_div.get_attribute('asseturl')
                                    if not swatch_image:
                                        swatch_image = option_div.get_attribute('data-asseturl')
                                    if not swatch_image:
                                        # For interior, try to get from style background-image
                                        style = option_div.get_attribute('style')
                                        if style and 'background-image' in style:
                                            match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                                            if match:
                                                swatch_image = match.group(1)
                                    if not swatch_image:
                                        swatch_image = ""
                                except:
                                    pass
                                
                                # Check if currently selected
                                is_selected = False
                                try:
                                    is_selected = "selected" in container.get_attribute("class").lower()
                                except:
                                    pass
                                
                                if option_name and option_name != "Unknown Option":
                                    # Sanitize the option name for display
                                    display_name = self.sanitize_filename(option_name)
                                    categories[category_name].append({
                                        'name': display_name,
                                        'original_name': option_name,  # Keep original name for reference
                                        'price': price,
                                        'swatch_image': swatch_image,
                                        'element': container,
                                        'currently_selected': is_selected
                                    })
                                    swatch_status = "✓" if swatch_image else "✗"
                                    print(f"      - {display_name} ({price}) [Swatch: {swatch_status}]")
                                
                            except Exception as e:
                                print(f"      Error parsing option: {e}")
                                continue
                
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"Error finding sections: {e}")
        
        return categories
    
    def crop_image(self, screenshot_bytes, crop_top_ratio=0.05, crop_bottom_ratio=0.15):
        """
        Crop the screenshot to remove top and bottom portions.
        
        Args:
            screenshot_bytes: Bytes of the screenshot image
            crop_top_ratio: Ratio of height to crop from top (default: 5%)
            crop_bottom_ratio: Ratio of height to crop from bottom (default: 15%)
        
        Returns:
            Cropped image as base64 string
        """
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(screenshot_bytes))
            width, height = image.size
            
            # Calculate crop coordinates
            top_crop = int(height * crop_top_ratio)
            bottom_crop = int(height * crop_bottom_ratio)
            
            # Define crop box (left, upper, right, lower)
            crop_box = (0, top_crop, width, height - bottom_crop)
            
            # Crop the image
            cropped_image = image.crop(crop_box)
            
            # Convert to base64
            buffered = io.BytesIO()
            cropped_image.save(buffered, format="PNG")
            cropped_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return cropped_base64
            
        except Exception as e:
            print(f"      Error cropping image: {e}")
            return base64.b64encode(screenshot_bytes).decode('utf-8')
    
    def capture_car_preview(self, option_name, category_name, index):
        """
        Capture screenshot of the car preview section and crop it.
        
        Returns:
            Cropped base64 image string
        """
        try:
            # Find the car preview section
            preview_section = self.find_car_preview_section()
            
            if not preview_section:
                print(f"      ⚠ Preview section not found")
                return None
            
            # Scroll to the preview section
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", preview_section)
            time.sleep(1.5)
            
            # Take screenshot of the preview section
            screenshot_bytes = preview_section.screenshot_as_png
            
            # Sanitize the filename for Windows
            safe_name = self.sanitize_filename(option_name)
            filename = f"{category_name}_{index}_{safe_name}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save locally
            try:
                with open(filepath, "wb") as f:
                    f.write(screenshot_bytes)
                print(f"      ✓ Saved locally: {filename}")
            except Exception as e:
                # If still fails, use a simpler filename
                safe_name = f"option_{index}"
                filename = f"{category_name}_{index}_{safe_name}.png"
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(screenshot_bytes)
                print(f"      ✓ Saved with simplified name: {filename}")
            
            # Crop the image
            cropped_base64 = self.crop_image(screenshot_bytes, crop_top_ratio=0.05, crop_bottom_ratio=0.15)
            
            # Save cropped version
            cropped_filename = f"{category_name}_{index}_{safe_name}_cropped.png"
            cropped_filepath = os.path.join(self.output_dir, cropped_filename)
            
            with open(cropped_filepath, "wb") as f:
                f.write(base64.b64decode(cropped_base64))
            
            return cropped_base64
            
        except Exception as e:
            print(f"      ✗ Error capturing preview: {str(e)[:100]}")
            return None
    
    def handle_conflict_modal(self):
        """
        Check for conflict modal popup and click confirm button if present
        Returns True if modal was found and handled, False otherwise
        """
        try:
            # Wait a short time for potential modal to appear
            time.sleep(1)
            
            # Check if conflict modal is present
            modal_selectors = [
                ".conflict-modal__content",
                "[class*='conflict-modal']"
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if modal.is_displayed():
                        modal_found = True
                        print("      ⚠ Conflict modal detected")
                        break
                except:
                    continue
            
            if not modal_found:
                return False
            
            # Try to find and click the confirm button
            confirm_button_selectors = [
                ".conflict-modal__btn-confirm.conflict-modal__btn",
                ".conflict-modal__btn-confirm",
                ".conflict-modal__btn",
                "button.conflict-modal__btn-confirm",
                "[class*='conflict-modal__btn-confirm']"
            ]
            
            for selector in confirm_button_selectors:
                try:
                    confirm_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if confirm_btn.is_displayed():
                        # Try clicking with JavaScript first
                        self.driver.execute_script("arguments[0].click();", confirm_btn)
                        print("      ✓ Clicked conflict modal confirm button")
                        
                        # Wait for modal to disappear
                        time.sleep(1.5)
                        
                        # Verify modal is gone
                        try:
                            modal_check = self.driver.find_element(By.CSS_SELECTOR, ".conflict-modal__content")
                            if not modal_check.is_displayed():
                                print("      ✓ Modal closed successfully")
                        except:
                            print("      ✓ Modal closed successfully")
                        
                        return True
                except Exception as e:
                    continue
            
            print("      ⚠ Could not find confirm button in modal")
            return False
            
        except Exception as e:
            print(f"      Error handling conflict modal: {e}")
            return False
    
    def click_option(self, option_element, option_name):
        """Click on an option to change the car preview"""
        try:
            # Scroll to the option first
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", option_element)
            time.sleep(0.5)
            
            # Click using JavaScript
            self.driver.execute_script("arguments[0].click();", option_element)
            
            # Wait for initial change to start
            time.sleep(2)
            
            # Check and handle conflict modal if it appears
            self.handle_conflict_modal()
            
            # Wait for change to render after modal handling
            time.sleep(2)
            
            # Check for loading indicators
            try:
                loading_selectors = ['.loading', '.spinner', '[class*="loader"]', '[class*="loading"]']
                for selector in loading_selectors:
                    try:
                        loading = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if loading.is_displayed():
                            self.wait.until(EC.invisibility_of_element(loading))
                    except:
                        continue
            except:
                pass
            
            # Final wait to ensure rendering is complete
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"      Error clicking option: {e}")
            return False
    
    def scrape_all_options(self):
        """Main scraping function for all categories"""
        print("\nStarting MINI configuration scraping...")
        print(f"Model: {self.model_data['name']}")
        
        # Setup and navigate
        self.setup_driver()
        self.navigate_to_url()
        
        # Get all categories
        categories = self.get_all_categories()
        
        # Prepare configuration data
        configuration = {
            "model_name": self.model_data['name'],
            "base_price": self.model_data['price'],
            "url": self.model_data['link'],
            "categories": {
                "exterior_colors": [],
                "roof_mirror_caps": [],
                "wheels": [],
                "interior": []
            }
        }
        
        # Process each category
        for category_name, options in categories.items():
            if not options:
                print(f"\n  No options found for {category_name}")
                continue
            
            print(f"\n  Processing {category_name}: {len(options)} options")
            
            for idx, option in enumerate(options):
                print(f"\n    [{idx + 1}/{len(options)}] {option['name']}")
                
                # Click the option
                if self.click_option(option['element'], option['name']):
                    # Capture the car preview
                    cropped_image = self.capture_car_preview(option['original_name'], category_name, idx)
                    
                    # Upload to Cloudinary
                    cloudinary_url = None
                    if cropped_image:
                        cloudinary_url = self.upload_to_cloudinary(
                            cropped_image,
                            category_name,
                            option['original_name'],
                            idx
                        )
                    
                    # Add to configuration
                    configuration["categories"][category_name].append({
                        "name": option['original_name'],  # Use original name in JSON
                        "display_name": option['name'],   # Use sanitized name for display
                        "price": option['price'],
                        "swatch_image": option['swatch_image'],
                        "car_image": cloudinary_url or "",
                        "currently_selected": option['currently_selected']
                    })
                    
                    time.sleep(1)
                else:
                    # Still add option even if click failed
                    configuration["categories"][category_name].append({
                        "name": option['original_name'],
                        "display_name": option['name'],
                        "price": option['price'],
                        "swatch_image": option['swatch_image'],
                        "car_image": "",
                        "currently_selected": option['currently_selected']
                    })
        
        self.configurations.append(configuration)
        
        print(f"\n✓ Scraping completed!")
        print(f"  Exterior Colors: {len(configuration['categories']['exterior_colors'])}")
        print(f"  Roof/Mirror Caps: {len(configuration['categories']['roof_mirror_caps'])}")
        print(f"  Wheels: {len(configuration['categories']['wheels'])}")
        print(f"  Interior: {len(configuration['categories']['interior'])}")
    
    def save_to_json(self):
        """Save scraped data to JSON file"""
        filename = f"mini_{self.model_data['name'].replace(' ', '_').lower()}_data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.configurations, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Data saved to: {filename}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            print("\nBrowser closed.")

def load_initial_models():
    """Load initial Mini Cooper models array grouped by car family"""
    return {
        "Countryman": {
            "base_image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MM&client=NVCO&paint=P0C71&fabric=FKXJ5&sa=S01AG,S01CB,S01CR,S01D0,S01KS,S0248,S02VB,S02XH,S0300,S0302,S0322,S0386,S03AF,S0402,S0420,S0430,S0431,S0451,S0459,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AU,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EP,S07ER,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TT,S0925,S0992,S09T0,S0ZHI,S0ZJY,S0ZNH,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3",
            "trims": [
                {
                    "name": "Countryman S ALL4",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs41dv7b/build/engine",
                    "price": "$40,450",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MM&client=NVCO&paint=P0C71&fabric=FKXJ5&sa=S01AG,S01CB,S01CR,S01D0,S01KS,S0248,S02VB,S02XH,S0300,S0302,S0322,S0386,S03AF,S0402,S0420,S0430,S0431,S0451,S0459,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AU,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EP,S07ER,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TT,S0925,S0992,S09T0,S0ZHI,S0ZJY,S0ZNH,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "JCW Countryman ALL4",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5xo2ma/build/engine",
                    "price": "$46,900",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MM&client=NVCO&paint=P0C71&fabric=FKXJ5&sa=S01AG,S01CB,S01CR,S01D0,S01KS,S0248,S02VB,S02XH,S0300,S0302,S0322,S0386,S03AF,S0402,S0420,S0430,S0431,S0451,S0459,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AU,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EP,S07ER,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TT,S0925,S0992,S09T0,S0ZHI,S0ZJY,S0ZNH,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                }
            ]
        },
        "Countryman SE": {
            "base_image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MP&client=NVCO&paint=P0C6A&fabric=FKXJ4&sa=S01K7,S0248,S02VB,S02VC,S02XH,S0302,S0322,S0386,S03B5,S0402,S0420,S0430,S0431,S0451,S0459,S0494,S04AA,S04FN,S04NR,S04T3,S04U9,S04VF,S05A4,S05AC,S05AU,S05DN,S05YZ,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EP,S07ER,S0823,S0845,S0853,S08BK,S08R9,S08SM,S08TN,S08TT,S0925,S0992,S09T0,S0ZHI,S0ZJY,S0ZKO,S0ZNH,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3",
            "trims": [
                {
                    "name": "COUNTRYMAN SE ALL4",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5g0okb/build/engine",
                    "price": "$45,200",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MP&client=NVCO&paint=P0C6A&fabric=FKXJ4&sa=S01K7,S0248,S02VB,S02VC,S02XH,S0302,S0322,S0386,S03B5,S0402,S0420,S0430,S0431,S0451,S0459,S0494,S04AA,S04FN,S04NR,S04T3,S04U9,S04VF,S05A4,S05AC,S05AU,S05DN,S05YZ,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EP,S07ER,S0823,S0845,S0853,S08BK,S08R9,S08SM,S08TN,S08TT,S0925,S0992,S09T0,S0ZHI,S0ZJY,S0ZKO,S0ZNH,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                }
            ]
        },
        "Cooper 2 Door": {
            "base_image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MB&client=NVCO&paint=P0C6M&fabric=FTCJ1&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QP,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S0382,S0402,S0430,S0431,S044C,S0494,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EA,S07ED,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T3,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3",
            "trims": [
                {
                    "name": "Cooper C 2 Door",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5e70zb/build/engine",
                    "price": "$29,500",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MB&client=NVCO&paint=P0C6M&fabric=FTCJ1&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QP,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S0382,S0402,S0430,S0431,S044C,S0494,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EA,S07ED,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T3,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "Cooper S 2 Door",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5gpaxm/build/engine",
                    "price": "$32,800",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MB&client=NVCO&paint=P0C6M&fabric=FTCJ1&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QP,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S0382,S0402,S0430,S0431,S044C,S0494,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EA,S07ED,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T3,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "JCW 2 Door",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs52fp47/build/engine",
                    "price": "$38,900",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26MB&client=NVCO&paint=P0C6M&fabric=FTCJ1&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QP,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S0382,S0402,S0430,S0431,S044C,S0494,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07EA,S07ED,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T3,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                }
            ]
        },
        "Cooper 4 Door": {
            "base_image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26M3&client=NVCO&paint=P0C6L&fabric=FKXJ2&sa=S01CB,S01CR,S01DS,S01KF,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S03B4,S0402,S0430,S0431,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T0,S0ZHI,S0ZJY,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3",
            "trims": [
                {
                    "name": "Cooper C 4 Door",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5bb8ac/build/engine",
                    "price": "$32,900",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26M3&client=NVCO&paint=P0C6L&fabric=FKXJ2&sa=S01CB,S01CR,S01DS,S01KF,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S03B4,S0402,S0430,S0431,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T0,S0ZHI,S0ZJY,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "Cooper S 4 Door",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5w9srt/build/engine",
                    "price": "$33,800",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26M3&client=NVCO&paint=P0C6L&fabric=FKXJ2&sa=S01CB,S01CR,S01DS,S01KF,S0248,S02TF,S02VB,S02VC,S02XH,S0302,S0322,S03B4,S0402,S0430,S0431,S0494,S04AA,S04FN,S04NR,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S0925,S0992,S09T0,S0ZHI,S0ZJY,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                }
            ]
        },
        "Cooper Convertible": {
            "base_image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26ME&client=NVCO&paint=P0C77&fabric=FKXB4&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QL,S0248,S02TF,S02VB,S02VC,S02XH,S0322,S0387,S03BE,S03YR,S0430,S0431,S0451,S0459,S0494,S04FN,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S05DS,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TV,S0925,S0992,S09T0,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3",
            "trims": [
                {
                    "name": "Cooper C Convertible",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs567hm4/build/engine",
                    "price": "$34,600",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26ME&client=NVCO&paint=P0C77&fabric=FKXB4&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QL,S0248,S02TF,S02VB,S02VC,S02XH,S0322,S0387,S03BE,S03YR,S0430,S0431,S0451,S0459,S0494,S04FN,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S05DS,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TV,S0925,S0992,S09T0,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "Cooper S Convertible",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs582tdx/build/engine",
                    "price": "$37,900",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26ME&client=NVCO&paint=P0C77&fabric=FKXB4&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QL,S0248,S02TF,S02VB,S02VC,S02XH,S0322,S0387,S03BE,S03YR,S0430,S0431,S0451,S0459,S0494,S04FN,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S05DS,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TV,S0925,S0992,S09T0,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                },
                {
                    "name": "JCW Convertible",
                    "link": "https://www.miniusa.com/build-your-own.html#/studio/fs5rgsib/build/engine",
                    "price": "$44,600",
                    "image": "https://cache.miniusa.com/cosy.arox?pov=walkaround&brand=WBMI&vehicle=26ME&client=NVCO&paint=P0C77&fabric=FKXB4&sa=CTRLLIGHTSON,S01CB,S01CR,S01DS,S01QL,S0248,S02TF,S02VB,S02VC,S02XH,S0322,S0387,S03BE,S03YR,S0430,S0431,S0451,S0459,S0494,S04FN,S04VF,S05A4,S05AC,S05AS,S05AT,S05DN,S05DS,S0645,S0655,S0688,S06AC,S06AD,S06AE,S06NX,S06PA,S06UQ,S07ED,S07EP,S0823,S0840,S0842,S0845,S0850,S0853,S08KL,S08R9,S08SM,S08TN,S08TV,S0925,S0992,S09T0,S0ZHI,CTRLLIGHTSON&quality=90&sharp=100&resp=png&BKGND=TRANSPARENT&width=2000&angle=45&cut=3"
                }
            ]
        }
    }


def group_scraped_data_by_car(all_scraped_data):
    """
    Group all scraped trim data by car family
    
    Args:
        all_scraped_data: List of trim configurations from scraping
    
    Returns:
        List of car families with grouped trims
    """
    car_families = load_initial_models()
    output = []
    
    for car_name, car_info in car_families.items():
        car_entry = {
            "name": car_name,
            "base_image": car_info["base_image"],
            "trims": []
        }
        
        # Find all trims for this car family
        for trim_data in all_scraped_data:
            # Check if this trim belongs to this car family
            trim_name = trim_data.get("model_name", "")
            if any(trim["name"] == trim_name for trim in car_info["trims"]):
                car_entry["trims"].append(trim_data)
        
        # Only add car if it has trims
        if car_entry["trims"]:
            output.append(car_entry)
    
    return output


def save_grouped_json(all_scraped_data, filename="mini_cooper.json"):
    """
    Save all scraped data grouped by car family
    
    Args:
        all_scraped_data: List of all scraped trim configurations
        filename: Output filename
    """
    grouped_data = group_scraped_data_by_car(all_scraped_data)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(grouped_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Grouped data saved to: {filename}")
    print(f"  Total car families: {len(grouped_data)}")
    for car in grouped_data:
        print(f"    - {car['name']}: {len(car['trims'])} trims")


def main():
    # Load available models grouped by car family
    car_families = load_initial_models()
    
    # Flatten to get all trims
    all_trims = []
    for car_name, car_info in car_families.items():
        all_trims.extend(car_info["trims"])
    
    print("\n" + "="*60)
    print("MINI COOPER AUTOMATIC SCRAPING - ALL TRIMS")
    print("="*60)
    print(f"\nTotal trims to scrape: {len(all_trims)}")
    
    # Group by car family for display
    for car_name, car_info in car_families.items():
        print(f"\n{car_name}:")
        for trim in car_info["trims"]:
            print(f"  - {trim['name']} ({trim['price']})")
    print("="*60)
    
    # Cloudinary configuration
    cloudinary_config = {
        'cloud_name': "dsmkxcczo",
        'api_key': "395956489484953",
        'api_secret': "rMIXWeYnZI7-ir834KFjEpf0dWI"
    }
    
    # Store all scraped configurations
    all_scraped_data = []
    
    # Loop through all trims
    for idx, trim in enumerate(all_trims, 1):
        print(f"\n{'='*60}")
        print(f"PROCESSING TRIM {idx}/{len(all_trims)}")
        print(f"{'='*60}")
        print(f"Trim: {trim['name']}")
        print(f"Price: {trim['price']}")
        print(f"URL: {trim['link']}\n")
        
        # Initialize scraper with selected trim
        scraper = MiniColorScraper(
            trim['link'],
            trim,
            cloudinary_config=cloudinary_config
        )
        
        try:
            # Start scraping
            scraper.scrape_all_options()
            
            # Add scraped data to collection
            if scraper.configurations:
                all_scraped_data.extend(scraper.configurations)
            
            print(f"\n✅ Successfully completed: {trim['name']}")
        
        except KeyboardInterrupt:
            print(f"\n❌ Scraping interrupted by user at trim: {trim['name']}")
            if scraper.configurations:
                all_scraped_data.extend(scraper.configurations)
            break  # Exit the loop if user interrupts
        
        except Exception as e:
            print(f"\n❌ Error occurred while scraping {trim['name']}: {e}")
            import traceback
            traceback.print_exc()
            # Continue to next trim even if current one fails
        
        finally:
            # Cleanup
            scraper.cleanup()
            
        # Add a small delay between trims
        if idx < len(all_trims):
            print(f"\n⏳ Waiting 5 seconds before next trim...")
            time.sleep(5)
    
    # Save grouped data
    if all_scraped_data:
        save_grouped_json(all_scraped_data)
    
    print("\n" + "="*60)
    print("ALL TRIMS PROCESSING COMPLETED")
    print("="*60)


if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        from PIL import Image
    except ImportError:
        print("Installing Pillow for image processing...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'Pillow'])
        from PIL import Image
    
    try:
        import cloudinary
    except ImportError:
        print("Installing Cloudinary SDK...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'cloudinary'])
        import cloudinary
    
    main()