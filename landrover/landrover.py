import json
import random
import re
import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Any, Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import base64
from datetime import datetime
import uuid
import boto3
from botocore.exceptions import ClientError
import requests
from io import BytesIO
import os
from dotenv import load_dotenv
import hashlib
from PIL import Image
import io

load_dotenv()  # Load environment variables from .env file


class LandRoverScraper:
    def __init__(self, headless=False, cloudinary_config=None):
        """Initialize the scraper with proper browser emulation."""
        chrome_options = Options()

        # Disable automation flags
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Add arguments to make browser look more human
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process")

        # Random viewport size to appear more human
        viewport_sizes = [(1920, 1080), (1366, 768), (1536, 864)]
        width, height = random.choice(viewport_sizes)
        chrome_options.add_argument(f"--window-size={width},{height}")

        # Add user agent rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(
            f'--user-agent={random.choice(user_agents)}')

        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

        # Execute CDP commands to hide automation
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.driver.execute_script("return navigator.userAgent").replace("Headless", ""),
            "platform": "Win32"
        })

        # Override navigator.webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.scraped_data = {}
        self._last_color_canvas = None  # Store previous canvas hash for comparison

        # Initialize Cloudinary
        if cloudinary_config:
            try:
                cloudinary.config(
                    cloud_name=cloudinary_config.get('cloud_name'),
                    api_key=cloudinary_config.get('api_key'),
                    api_secret=cloudinary_config.get('api_secret'),
                    secure=True
                )
                self.cloudinary_folder = cloudinary_config.get('folder', 'landrover')
                self.cloudinary_enabled = True
                print(f"Cloudinary initialized successfully (folder: {self.cloudinary_folder})")
            except Exception as e:
                self.cloudinary_enabled = False
                print(f"Failed to initialize Cloudinary: {e}")
        else:
            self.cloudinary_enabled = False
            print("Cloudinary not configured, images will not be uploaded")

    def close(self):
        """Close the browser."""
        self.driver.quit()

    def _navigate_to_tray(self, tray_id: str) -> bool:
        """Navigates to a specific tray (e.g., 'exterior', 'interior') via data-navigation-id."""
        print(f"  > Navigating to: {tray_id}")
        try:
            nav_item = self.driver.find_element(
                By.CSS_SELECTOR, f"li[data-navigation-id*='{tray_id}'] a")
            self.driver.execute_script("arguments[0].click();", nav_item)
            time.sleep(4)
            return True
        except:
            try:
                links = self.driver.find_elements(
                    By.CSS_SELECTOR, "nav a, .scrolling-navigation-list-item__cta")
                for link in links:
                    if tray_id.lower() in link.text.lower():
                        self.driver.execute_script(
                            "arguments[0].click();", link)
                        time.sleep(4)
                        return True
            except:
                pass

        print(f"    x Could not navigate to {tray_id}")
        return False

    def _extract_item_from_block(self, block) -> Optional[Dict]:
        """Extracts Name, Price, and Image from a feature block."""
        try:
            item = {}

            name_selectors = [
                "[data-testid*='feature_heading']",
                "[id*='feature_heading']",
                "._feature-block__title_1dubr_249",
                "[class*='feature-block__title']",
                "._copy_x3ymg_220._bold_x3ymg_485"
            ]
            for sel in name_selectors:
                try:
                    el = block.find_element(By.CSS_SELECTOR, sel)
                    if el.text.strip():
                        item["name"] = el.text.strip()
                        break
                except:
                    continue

            if not item.get("name"):
                try:
                    item["name"] = block.find_element(
                        By.TAG_NAME, "a").get_attribute("aria-label")
                except:
                    pass

            if not item.get("name"):
                return None

            item["price"] = "$0"
            price_selectors = [
                "[data-testid*='feature_price']",
                "[class*='feature-block__price']"
            ]
            for sel in price_selectors:
                try:
                    el = block.find_element(By.CSS_SELECTOR, sel)
                    if el.text.strip():
                        item["price"] = el.text.strip()
                        break
                except:
                    continue

            img_url = ""
            img_selectors = ["img", "[class*='thumbnail']",
                             "[data-testid*='feature_img']"]
            for sel in img_selectors:
                try:
                    img = block.find_element(By.CSS_SELECTOR, sel)
                    src = img.get_attribute("src")
                    if src and "http" in src:
                        img_url = src
                        break
                except:
                    continue

            if img_url and self.cloudinary_enabled:
                item["swatch_image"] = self._upload_to_cloudinary(img_url, item["name"], is_base64=False, category="features")
                item["image_url"] = ""
            else:
                item["swatch_image"] = img_url
                item["image_url"] = ""

            return item
        except Exception:
            return None

    def get_model_info(self, url: str, car_name: str) -> List[Dict]:
        """Get all models from the products page or direct build links."""
        print(f"Processing {car_name}...")

        models = []

        if isinstance(url, str) and 'personalise' in url:
            model_info = {
                "model": car_name,
                "bodystyle": "Standard",
                "price": None,
                "image_url": "",
                "build_url": url,
                "configurations": {}
            }
            models.append(model_info)
            print(f"  - Added model: {car_name}")
            return models

    def get_model_info_from_trim_list(self, car_name: str, trims: List[Dict]) -> List[Dict]:
        """Get models from a list of trim dictionaries."""
        print(f"Processing {len(trims)} trims for {car_name}...")

        models = []
        for trim in trims:
            if not trim.get("link"):
                print(f"  Skipping {trim.get('model_name', 'Unknown')} - no link")
                continue

            model_info = {
                "model": f"{car_name} {trim.get('model_name', 'Unknown')}",
                "bodystyle": trim.get("body_style", "Standard"),
                "price": None,
                "image_url": "",
                "build_url": trim["link"],
                "configurations": {}
            }
            models.append(model_info)
            print(f"  - Added model: {model_info['model']}")

        return models

    def navigate_to_section(self, section_name: str) -> bool:
        """Navigate to a specific section using the main navigation - IMPROVED."""
        try:
            time.sleep(2)

            all_clickable = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button, a, [role='button'], [role='tab'], [data-testid], [class*='nav'], [class*='tab']"
            )

            print(f"  Looking for section: '{section_name}'")

            for element in all_clickable:
                try:
                    if not element.is_displayed():
                        continue

                    element_text = element.text.strip().upper()
                    element_aria = (element.get_attribute("aria-label") or "").upper()
                    element_data = (element.get_attribute("data-testid") or "").upper()

                    if (section_name.upper() in element_text or
                        section_name.upper() in element_aria or
                            section_name.upper() in element_data):

                        element_class = element.get_attribute("class") or ""
                        if any(active in element_class.lower() for active in ["active", "selected", "current"]):
                            print(f"  Already on section: {section_name}")
                            return True

                        try:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(1)
                            element.click()
                            print(f"  Navigated to: {section_name} (direct click)")
                            time.sleep(3)
                            return True
                        except:
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                print(f"  Navigated to: {section_name} (JS click)")
                                time.sleep(3)
                                return True
                            except:
                                continue
                except:
                    continue

            nav_selectors = [
                ".main-nav__list-item",
                ".nav-item",
                ".navigation-item",
                "[data-testid*='nav']",
                "nav li",
                "button[aria-label*='{}']".format(section_name.lower()),
                "button[aria-label*='{}']".format(section_name.upper())
            ]

            for selector in nav_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        print(f"  Found {len(items)} items with selector: {selector}")
                        for item in items:
                            try:
                                if not item.is_displayed():
                                    continue

                                item_text = item.text.strip().upper()
                                if section_name.upper() in item_text:
                                    item_class = item.get_attribute("class") or ""
                                    if any(active in item_class.lower() for active in ["active", "selected", "current"]):
                                        print(f"  Already on: {section_name}")
                                        return True

                                    clickable = None
                                    for tag in ["a", "button", "[role='button']", "[role='tab']"]:
                                        try:
                                            clickable = item.find_element(By.CSS_SELECTOR, tag)
                                            if clickable:
                                                break
                                        except:
                                            continue

                                    if clickable:
                                        try:
                                            clickable.click()
                                            print(f"  Navigated to: {section_name} (via selector)")
                                            time.sleep(3)
                                            return True
                                        except:
                                            try:
                                                self.driver.execute_script("arguments[0].click();", clickable)
                                                print(f"  Navigated to: {section_name} (via JS)")
                                                time.sleep(3)
                                                return True
                                            except:
                                                continue
                            except:
                                continue
                except:
                    continue

            print(f"  Could not find section: {section_name}")
            try:
                available_sections = []
                for elem in all_clickable[:50]:
                    try:
                        text = elem.text.strip()
                        if text and len(text) < 50:
                            available_sections.append(text)
                    except:
                        continue
                unique_sections = list(set(available_sections))
                print(f"  Available sections: {', '.join(unique_sections[:20])}")
            except:
                pass

            return False

        except Exception as e:
            print(f"  Error navigating to {section_name}: {e}")
            return False

    def _click_subnav_item(self, item_name: str) -> bool:
        """Click on a specific sub-navigation item."""
        try:
            time.sleep(2)
            subnav_selectors = [
                ".sub-nav__list-item",
                ".subnav-item",
                ".secondary-nav-item",
                "[data-testid*='subnav']",
                ".tabs li",
                ".tab-item"
            ]

            subnav_items = []
            for selector in subnav_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        subnav_items = items
                        break
                except:
                    continue

            if not subnav_items:
                all_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "a, button, [role='tab'], [role='button']")
                for element in all_elements:
                    try:
                        element_text = element.text.strip().upper()
                        if item_name.upper() in element_text:
                            element_classes = element.get_attribute("class") or ""
                            if any(disabled in element_classes.lower() for disabled in ["disabled", "unavailable"]):
                                return False
                            self.driver.execute_script("arguments[0].click();", element)
                            print(f"    Clicked on: {item_name} (via text match)")
                            time.sleep(2)
                            return True
                    except:
                        continue

                print(f"    Could not find subnav item: {item_name}")
                return False

            for item in subnav_items:
                try:
                    link_selectors = [".sub-nav__link", "a", "button", "[role='tab']", "[role='button']"]
                    link = None
                    for selector in link_selectors:
                        try:
                            link = item.find_element(By.CSS_SELECTOR, selector)
                            if link:
                                break
                        except:
                            continue

                    if not link:
                        continue

                    link_text = link.text.strip().upper()

                    if item_name.upper() in link_text:
                        link_classes = link.get_attribute("class") or ""
                        if any(disabled in link_classes.lower() for disabled in ["disabled", "unavailable", "sub-nav__link--disabled"]):
                            return False

                        item_classes = item.get_attribute("class") or ""
                        if any(active in item_classes.lower() or active in link_classes.lower()
                               for active in ["active", "selected", "current"]):
                            return True

                        self.driver.execute_script("arguments[0].click();", link)
                        print(f"    Clicked on: {item_name}")
                        time.sleep(2)
                        return True
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    continue

            print(f"    Could not find subnav item: {item_name}")
            return False

        except Exception as e:
            print(f"    Error clicking subnav item {item_name}: {e}")
            return False

    def scrape_exterior_colors(self) -> List[Dict]:
        """Scrape exterior colors section with ONLY full car screenshots."""
        colors = []

        try:
            if hasattr(self, '_color_processed'):
                delattr(self, '_color_processed')

            time.sleep(3)
            print("  Waiting for color options to load...")

            page_source = self.driver.page_source.lower()
            if 'color' not in page_source and 'exterior' not in page_source:
                print("  WARNING: No 'color' or 'exterior' text found on page")

            print("  Trying bundle-based approach...")
            color_bundle_selectors = [
                ".tray-bundle",
                ".option-bundle",
                ".color-bundle",
                "[data-testid*='color']",
                ".config-section",
                "section[class*='color']"
            ]

            color_bundles = []
            bundle_approach_successful = False

            for selector in color_bundle_selectors:
                try:
                    bundles = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if bundles:
                        color_bundles = bundles
                        print(f"    Found {len(color_bundles)} elements with selector: {selector}")
                        bundle_approach_successful = True
                        break
                except:
                    continue

            if bundle_approach_successful:
                print(f"  Found {len(color_bundles)} color categories using bundle approach")
                colors_from_bundles = self._process_color_bundles(color_bundles)
                colors.extend(colors_from_bundles)

            if not colors:
                print("  Bundle approach failed, trying direct element search...")
                color_elements = []

                try:
                    color_attr_elements = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "[data-id*='color'], [data-id*='COLOR'], [data-testid*='color'], [data-testid*='COLOR'], [id*='color'], [id*='COLOR']"
                    )
                    if color_attr_elements:
                        color_elements = color_attr_elements
                        print(f"    Found {len(color_elements)} elements with color in attributes")
                except Exception as e:
                    print(f"    Error in attribute search: {e}")

                if not color_elements:
                    try:
                        class_elements = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            ".color-option, .tray-block, .option-item, .config-item, [class*='color'], [class*='Color'], [class*='COLOR']"
                        )
                        if class_elements:
                            color_elements = class_elements
                            print(f"    Found {len(color_elements)} elements with color-related classes")
                    except Exception as e:
                        print(f"    Error in class search: {e}")

                if not color_elements:
                    try:
                        color_names = [
                            'white', 'black', 'gray', 'grey', 'silver', 'blue', 'red',
                            'green', 'yellow', 'brown', 'orange', 'purple', 'pink',
                            'pearl', 'metallic', 'chrome', 'graphite', 'midnight'
                        ]
                        for color_name in color_names:
                            try:
                                elements = self.driver.find_elements(
                                    By.XPATH,
                                    f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{color_name}')]"
                                )
                                for element in elements:
                                    parent = element
                                    for _ in range(3):
                                        try:
                                            parent = parent.find_element(By.XPATH, "..")
                                            parent_class = parent.get_attribute("class") or ""
                                            parent_tag = parent.tag_name.lower()
                                            if any(x in parent_class.lower() for x in ['option', 'tray', 'config', 'item', 'color']):
                                                color_elements.append(parent)
                                                break
                                        except:
                                            break
                            except:
                                continue
                        print(f"    Found {len(color_elements)} elements by color name matching")
                    except Exception as e:
                        print(f"    Error in color name matching: {e}")

                if not color_elements:
                    try:
                        sections = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            "section, div[class*='section'], div[class*='config'], div[class*='option'], div[role='tabpanel']"
                        )
                        for section in sections:
                            try:
                                section_text = section.text.lower()
                                if any(keyword in section_text for keyword in ['color', 'exterior', 'paint', 'finish']):
                                    items = section.find_elements(
                                        By.CSS_SELECTOR,
                                        "button, a, [role='button'], [data-id], [data-testid], [tabindex='0']"
                                    )
                                    for item in items:
                                        if item.is_displayed():
                                            color_elements.append(item)
                            except:
                                continue
                        print(f"    Found {len(color_elements)} elements in color sections")
                    except Exception as e:
                        print(f"    Error finding color sections: {e}")

                if color_elements:
                    print(f"  Processing {len(color_elements)} potential color elements...")
                    processed_colors = {}
                    for element in color_elements[:30]:
                        try:
                            color_info = self._extract_color_info_improved(element)
                            if color_info and color_info.get("name"):
                                color_name = color_info['name'].strip().lower()
                                if color_name not in processed_colors:
                                    processed_colors[color_name] = color_info
                                    print(f"    ✓ Found color: {color_info['name']} ({color_info.get('price', '$0')})")
                                    screenshot_url = self.capture_exterior_color_screenshot(color_info['name'])
                                    if screenshot_url:
                                        color_info["image_url"] = screenshot_url
                                        color_info["swatch_image"] = ""
                                        print(f"      ✓ Screenshot captured for: {color_info['name']}")
                        except Exception as e:
                            print(f"    Error processing element: {e}")
                            continue

                    colors.extend(list(processed_colors.values()))

            if not colors:
                print("  All approaches failed, trying emergency direct scrape...")
                colors = self._scrape_colors_directly()

            if not colors:
                print("  Trying emergency color scrape...")
                colors = self._emergency_color_scrape()

            if colors:
                unique_colors = {}
                for color in colors:
                    if 'name' in color:
                        color_key = f"{color['name'].lower()}_{color.get('category', '').lower()}"
                        if color_key not in unique_colors:
                            unique_colors[color_key] = color
                        else:
                            if len(str(color)) > len(str(unique_colors[color_key])):
                                unique_colors[color_key] = color

                colors = list(unique_colors.values())
                print(f"  Total unique colors found: {len(colors)}")

                for color in colors:
                    if not color.get("image_url"):
                        screenshot_url = self.capture_exterior_color_screenshot(color['name'])
                        if screenshot_url:
                            color["image_url"] = screenshot_url
                            color["swatch_image"] = ""
                            print(f"    ✓ Added screenshot for: {color['name']}")
            else:
                print("  No exterior colors found using any approach")

        except Exception as e:
            print(f"Error scraping exterior colors: {e}")
            import traceback
            traceback.print_exc()

        if colors:
            colors_with_screenshots = sum(1 for c in colors if c.get("image_url"))
            print(f"\n  ✓ Successfully captured {colors_with_screenshots}/{len(colors)} exterior color CAR SCREENSHOTS")
            print(f"  ✓ All images uploaded to Cloudinary")
        else:
            print("  ⚠ No exterior colors found")

        return colors

    def capture_exterior_color_screenshot(self, color_name: str) -> str:
        """Capture a screenshot of the current car with the selected exterior color and upload to Cloudinary."""
        try:
            print(f"    Capturing FULL CAR screenshot for exterior color: {color_name}")
            print(f"      Waiting for car visualization to load completely...")
            time.sleep(10)

            max_attempts = 20
            canvas_ready = False

            for attempt in range(max_attempts):
                try:
                    car_visual = self.driver.find_element(By.CSS_SELECTOR, "canvas, img[src*='vehicle'], img[src*='car'], [class*='cplayer']")
                    if car_visual and car_visual.is_displayed():
                        size = car_visual.size
                        if size['width'] > 300 and size['height'] > 200:
                            print(f"      Visualization ready: {size['width']}x{size['height']}")
                            canvas_ready = True
                            break
                except:
                    pass

                if attempt < max_attempts - 1:
                    print(f"      Waiting for visualization (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(3)

            if not canvas_ready:
                print(f"      Warning: Visualization may not be fully loaded")

            time.sleep(5)

            canvas_image = self._get_current_car_image_url(color_name)

            if not canvas_image:
                print("      Canvas capture failed, taking full screenshot...")
                screenshot = self.driver.get_screenshot_as_base64()
                canvas_image = f"data:image/png;base64,{screenshot}"

            if canvas_image:
                print(f"      Starting upload to Cloudinary...")
                cloudinary_url = self._upload_to_cloudinary(
                    canvas_image,
                    f"exterior_color_{color_name}",
                    is_base64=True,
                    category="exterior_colors"
                )

                if cloudinary_url:
                    print(f"      ✓ FULL CAR screenshot uploaded successfully")
                    print(f"      ✓ Cloudinary URL: {cloudinary_url}")
                    time.sleep(3)
                    return cloudinary_url
                else:
                    print(f"      ✗ Failed to upload screenshot to Cloudinary")
                    return ""
            else:
                print(f"      ✗ Could not capture screenshot")
                return ""

        except Exception as e:
            print(f"      Error capturing screenshot for {color_name}: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _upload_to_cloudinary(self, image_data, color_name, is_base64=True, category="exterior_colors") -> str:
        """Upload image to Cloudinary and return public URL."""
        if not self.cloudinary_enabled:
            print(f"        Cloudinary not enabled, skipping upload for {color_name}")
            return ""

        try:
            safe_name = "".join(c for c in color_name if c.isalnum() or c in ('-', '_')).replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            public_id = f"{self.cloudinary_folder}/{category}/{safe_name}_{timestamp}"

            print(f"        Uploading to Cloudinary: {public_id}")

            if is_base64:
                if image_data.startswith('data:image/png;base64,'):
                    image_data = image_data.split(',')[1]
                elif image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]

                try:
                    image_bytes = base64.b64decode(image_data)
                    print(f"        Decoded {len(image_bytes)} bytes from base64")
                except Exception as e:
                    print(f"        ✗ Failed to decode base64: {e}")
                    return ""

                print(f"        Uploading {len(image_bytes)} bytes...")
                upload_result = cloudinary.uploader.upload(
                    image_bytes,
                    public_id=public_id,
                    folder=self.cloudinary_folder,
                    resource_type="image",
                    overwrite=True,
                    invalidate=True,
                    timeout=120
                )
            else:
                try:
                    print(f"        Downloading image from URL...")
                    response = requests.get(image_data, timeout=30)
                    response.raise_for_status()
                    image_bytes = response.content
                    print(f"        Downloaded {len(image_bytes)} bytes")

                    print(f"        Uploading {len(image_bytes)} bytes...")
                    upload_result = cloudinary.uploader.upload(
                        image_bytes,
                        public_id=public_id,
                        folder=self.cloudinary_folder,
                        resource_type="image",
                        overwrite=True,
                        invalidate=True,
                        timeout=120
                    )
                except Exception as e:
                    print(f"        ✗ Error downloading image from URL: {e}")
                    return ""

            cloudinary_url = upload_result.get('secure_url', '')

            if cloudinary_url:
                print(f"        ✓ Upload successful!")
                print(f"        ✓ URL: {cloudinary_url}")
                time.sleep(2)
                return cloudinary_url
            else:
                print(f"        ✗ Failed to get Cloudinary URL from response")
                print(f"        Response: {upload_result}")
                return ""

        except Exception as e:
            print(f"        ✗ Cloudinary upload error for {color_name}: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _process_color_bundles(self, color_bundles: List[WebElement]) -> List[Dict]:
        """Process color bundles from first version approach."""
        colors = []

        for bundle in color_bundles:
            try:
                category = "UNKNOWN CATEGORY"
                category_selectors = [
                    ".tray-bundle__header-title__inner",
                    ".bundle-title",
                    "h3", "h4",
                    ".section-title",
                    "[class*='title']",
                    "[class*='header']"
                ]

                for selector in category_selectors:
                    try:
                        category_elem = bundle.find_element(By.CSS_SELECTOR, selector)
                        if category_elem:
                            category = category_elem.text.strip()
                            if category:
                                break
                    except:
                        continue

                print(f"    Processing category: {category}")

                color_blocks = bundle.find_elements(
                    By.CSS_SELECTOR, "[data-id], .color-option, .option-item, [data-testid], button, [role='button']")
                print(f"      Found {len(color_blocks)} color blocks")

                if not color_blocks:
                    continue

                color_groups = {}
                for block in color_blocks:
                    try:
                        color_id = block.get_attribute("data-id")
                        if not color_id:
                            try:
                                name_elem = block.find_element(
                                    By.CSS_SELECTOR, ".tray-block__line-text--description, .option-name, .color-name, span, div")
                                if name_elem:
                                    color_id = name_elem.text.strip().replace(" ", "_")
                            except:
                                continue

                        if color_id and color_id not in color_groups:
                            color_groups[color_id] = []
                        color_groups[color_id].append(block)
                    except:
                        continue

                print(f"      Grouped into {len(color_groups)} colors")

                for color_id, blocks in color_groups.items():
                    if not blocks or not color_id:
                        continue

                    try:
                        color_info = None
                        try:
                            color_info = self._extract_color_info(color_id, blocks, category)
                        except:
                            pass

                        if not color_info and blocks:
                            try:
                                color_info = self._extract_color_info_improved(blocks[0])
                                if color_info and 'category' not in color_info:
                                    color_info['category'] = category
                            except:
                                pass

                        if color_info:
                            screenshot_url = self.capture_exterior_color_screenshot(color_info['name'])
                            if screenshot_url:
                                color_info["image_url"] = screenshot_url
                                color_info["swatch_image"] = ""

                            colors.append(color_info)
                            print(f"      ✓ Extracted: {color_info['name']} ({color_info.get('price', '0')})")
                    except Exception as e:
                        print(f"      Error processing color {color_id}: {e}")
                        continue

            except Exception as e:
                print(f"    Error processing color bundle: {e}")
                continue

        return colors

    def _extract_color_info_improved(self, element) -> Dict:
        """Improved color extraction from any element."""
        color_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "image_url": "",
        }

        try:
            element_text = element.text.strip()
            if element_text:
                lines = [line.strip() for line in element_text.split('\n') if line.strip()]
                if lines:
                    color_info["name"] = lines[0]
                    for line in lines:
                        if '$' in line:
                            color_info["price"] = line
                            break

            if not color_info["name"]:
                for attr in ['aria-label', 'title', 'data-name', 'data-id', 'data-testid']:
                    attr_value = element.get_attribute(attr) or ""
                    if attr_value:
                        color_info["name"] = attr_value
                        break

            return color_info

        except Exception as e:
            print(f"    Error in improved extraction: {e}")
            return {}

    def _emergency_color_scrape(self) -> List[Dict]:
        """Emergency fallback for color scraping."""
        colors = []

        try:
            print("  Attempting emergency color scrape...")

            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.driver.save_screenshot(f"debug_page_{timestamp}.png")
                print(f"  Saved debug screenshot: debug_page_{timestamp}.png")
            except:
                pass

            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, button, a, li, span")

            print(f"  Scanning {len(all_elements)} elements for colors...")

            for element in all_elements[:100]:
                try:
                    if not element.is_displayed():
                        continue

                    text = element.text.strip()
                    if not text or len(text) > 50:
                        continue

                    text_lower = text.lower()
                    color_keywords = [
                        'white', 'black', 'gray', 'grey', 'silver', 'blue', 'red',
                        'green', 'yellow', 'brown', 'orange', 'purple', 'pink',
                        'metallic', 'pearl', 'gloss', 'matte', 'satin', 'finish'
                    ]

                    has_color_keyword = any(keyword in text_lower for keyword in color_keywords)
                    has_dollar_sign = '$' in text

                    if has_color_keyword or has_dollar_sign:
                        color_info = {
                            "name": text,
                            "price": "$0",
                            "swatch_image": "",
                            "image_url": ""
                        }

                        if has_dollar_sign:
                            price_match = re.search(r'\$\d+[\d,]*', text)
                            if price_match:
                                color_info["price"] = price_match.group()

                        screenshot_url = self.capture_exterior_color_screenshot(text)
                        if screenshot_url:
                            color_info["image_url"] = screenshot_url

                        colors.append(color_info)
                        print(f"    ⚠ Emergency found: {text}")

                except:
                    continue

        except Exception as e:
            print(f"  Emergency scrape error: {e}")

        return colors

    def _scrape_colors_directly(self) -> List[Dict]:
        """Scrape colors directly when no bundles are found."""
        colors = []

        try:
            color_selectors = [
                "[data-testid*='color']",
                ".color-option",
                ".option-item[aria-label*='color']",
                ".tray-block",
                ".config-item"
            ]

            color_elements = []
            for selector in color_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        color_elements = elements
                        break
                except:
                    continue

            print(f"  Found {len(color_elements)} color elements directly")

            for element in color_elements:
                try:
                    color_info = {
                        "name": "",
                        "price": "$0",
                        "swatch_image": "",
                        "image_url": ""
                    }

                    name_selectors = [
                        ".tray-block__line-text--description",
                        ".option-name",
                        ".color-name",
                        "[data-testid='block-desc']",
                        "span"
                    ]

                    for selector in name_selectors:
                        try:
                            name_elem = element.find_element(By.CSS_SELECTOR, selector)
                            if name_elem and name_elem.text.strip():
                                color_info["name"] = name_elem.text.strip()
                                break
                        except:
                            continue

                    if not color_info["name"]:
                        aria_label = element.get_attribute("aria-label") or ""
                        title = element.get_attribute("title") or ""
                        if aria_label:
                            color_info["name"] = aria_label
                        elif title:
                            color_info["name"] = title
                        else:
                            continue

                    price_selectors = [
                        ".tray-block__line--pricing .tray-block__line-text",
                        ".option-price",
                        ".price",
                        "[data-testid='block-price']"
                    ]

                    for selector in price_selectors:
                        try:
                            price_elem = element.find_element(By.CSS_SELECTOR, selector)
                            if price_elem:
                                price_text = price_elem.text.strip()
                                if price_text and "$" in price_text:
                                    color_info["price"] = price_text
                                break
                        except:
                            continue

                    screenshot_url = self.capture_exterior_color_screenshot(color_info["name"])
                    if screenshot_url:
                        color_info["image_url"] = screenshot_url

                    colors.append(color_info)
                    print(f"    ✓ Extracted directly: {color_info['name']} ({color_info['price']})")

                except Exception as e:
                    print(f"    Error extracting direct color: {e}")
                    continue

        except Exception as e:
            print(f"Error in direct color scraping: {e}")

        return colors

    def _extract_color_info(self, color_id: str, blocks: List, category: str) -> Optional[Dict]:
        """Extract color information from a group of blocks."""
        color_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "image_url": ""
        }

        for block in blocks:
            try:
                class_attr = block.get_attribute("class") or ""

                if "tray-block__section-content" in class_attr or "content" in class_attr.lower():
                    try:
                        name_selectors = [
                            ".tray-block__line-text--description",
                            ".option-name",
                            ".color-name",
                            "[data-testid='block-desc']",
                            "span"
                        ]
                        for selector in name_selectors:
                            try:
                                name_elem = block.find_element(By.CSS_SELECTOR, selector)
                                if name_elem and name_elem.text.strip():
                                    color_info["name"] = name_elem.text.strip()
                                    break
                            except:
                                continue
                    except:
                        pass

                    try:
                        price_selectors = [
                            ".tray-block__line--pricing .tray-block__line-text",
                            ".option-price",
                            ".price",
                            "[data-testid='block-price']"
                        ]
                        for selector in price_selectors:
                            try:
                                price_elem = block.find_element(By.CSS_SELECTOR, selector)
                                if price_elem:
                                    price_text = price_elem.text.strip()
                                    if price_text and "$" in price_text:
                                        color_info["price"] = price_text
                                    break
                            except:
                                continue
                    except:
                        pass

            except Exception as e:
                continue

        if not color_info["name"]:
            return None

        try:
            clickable_block = None
            try:
                clickable_block = self.driver.find_element(
                    By.CSS_SELECTOR, f"[data-id='{color_id}'] .tray-block__link, [data-id='{color_id}'] a, [data-id='{color_id}'] button")
            except:
                try:
                    all_links = self.driver.find_elements(
                        By.CSS_SELECTOR, ".tray-block__link, a, button, [role='button']")
                    for link in all_links:
                        try:
                            if color_info["name"] in link.get_attribute("aria-label") or color_info["name"] in link.text:
                                clickable_block = link
                                break
                        except:
                            continue
                except:
                    pass

            if clickable_block:
                is_selected = False
                try:
                    current_blocks = self.driver.find_elements(By.CSS_SELECTOR, f"[data-id='{color_id}']")
                    for block in current_blocks:
                        try:
                            block_classes = block.get_attribute("class") or ""
                            if any(selected in block_classes.lower() for selected in ["selected", "active", "current"]):
                                is_selected = True
                                break
                        except:
                            pass
                except:
                    pass

                is_first_processed_color = not hasattr(self, '_color_processed')
                if not hasattr(self, '_color_processed'):
                    self._color_processed = True

                if is_selected and is_first_processed_color:
                    print(f"      Capturing current selected color: {color_info['name']}")
                    time.sleep(2)
                else:
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", clickable_block)
                        time.sleep(2)
                        self.driver.execute_script("arguments[0].click();", clickable_block)
                        time.sleep(5)
                    except Exception as e:
                        print(f"      Error clicking color: {e}")
                        pass

                screenshot_url = self.capture_exterior_color_screenshot(color_info["name"])
                if screenshot_url:
                    color_info["image_url"] = screenshot_url

        except Exception as e:
            print(f"      Error capturing image for {color_info['name']}: {e}")

        return color_info

    def _get_current_car_image_url(self, color_name="") -> str:
        """Get the current car image URL by capturing the canvas as base64."""
        try:
            time.sleep(2)

            car_container_selectors = [
                ".cplayer-container",
                ".vehicle-container",
                ".car-container",
                ".visualization-container",
                "[data-testid*='car']",
                "[data-testid*='vehicle']",
                "[class*='cplayer']",
                "main",
                "section"
            ]

            for selector in car_container_selectors:
                try:
                    containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for container in containers:
                        try:
                            if container.is_displayed():
                                size = container.size
                                if size['width'] > 500 and size['height'] > 300:
                                    container_html = container.get_attribute("outerHTML").lower()
                                    if any(keyword in container_html for keyword in ['canvas', 'car', 'vehicle', 'visualization']):
                                        screenshot = container.screenshot_as_base64
                                        print(f"      Captured container screenshot: {size['width']}x{size['height']}")
                                        return f"data:image/png;base64,{screenshot}"
                                elif size['width'] > 800:
                                    screenshot = container.screenshot_as_base64
                                    print(f"      Captured wide container: {size['width']}x{size['height']}")
                                    return f"data:image/png;base64,{screenshot}"
                        except:
                            continue
                except:
                    continue

            canvas_selectors = [
                "canvas",
                ".cplayer--transition-in",
                ".cplayer--transition-out",
                "[data-layer*='color']",
                "[data-layer*='wheel']"
            ]

            for selector in canvas_selectors:
                try:
                    canvases = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for canvas in canvases:
                        try:
                            if canvas.is_displayed():
                                size = canvas.size
                                if size['width'] > 300 and size['height'] > 200:
                                    canvas_base64 = self.driver.execute_script("""
                                        try {
                                            var canvas = arguments[0];
                                            return canvas.toDataURL('image/png', 1.0);
                                        } catch(e) {
                                            return "";
                                        }
                                    """, canvas)

                                    if canvas_base64 and canvas_base64.startswith('data:image/png;base64,'):
                                        print(f"      Captured canvas image: {size['width']}x{size['height']}")
                                        return canvas_base64
                        except:
                            continue
                except:
                    continue

            try:
                screenshot = self.driver.get_screenshot_as_base64()
                print("      Fallback: Captured full page screenshot")
                return f"data:image/png;base64,{screenshot}"
            except:
                pass

            return ""

        except Exception as e:
            print(f"      Error capturing car image: {e}")
            return ""

    # =====================================================================
    # WHEELS SCRAPING METHODS
    # =====================================================================

    def scrape_wheels_section(self) -> Dict[str, List]:
        """Scrape wheels section - returns dict with 'wheel' and 'brakes' lists."""
        wheels_data = {
            "wheel": [],
            "brakes": []
        }

        try:
            time.sleep(3)
            print("  Looking for wheel options...")

            wheel_tray = None
            try:
                wheel_tray = self.driver.find_element(By.CSS_SELECTOR, 'div[data-tray-id="wheel_configuration"]')
                print("  Found wheel configuration tray")
            except:
                print("  Could not find wheel configuration tray")
                return wheels_data

            all_fieldsets = wheel_tray.find_elements(By.CSS_SELECTOR, 'fieldset')
            print(f"  Found {len(all_fieldsets)} fieldsets in wheel tray")

            brake_fieldsets = []
            wheel_fieldsets = []

            for fs in all_fieldsets:
                testid = (fs.get_attribute("data-testid") or "").upper()
                try:
                    legend_text = fs.find_element(By.TAG_NAME, "legend").text.strip().upper()
                except:
                    legend_text = ""

                is_brake = (
                    "BRAKE" in testid or
                    "CALIPER" in testid or
                    "BRAKE" in legend_text or
                    "CALIPER" in legend_text
                )

                if is_brake:
                    brake_fieldsets.append(fs)
                    print(f"    → Classified as BRAKES: testid='{testid}' legend='{legend_text}'")
                else:
                    wheel_fieldsets.append(fs)
                    print(f"    → Classified as WHEELS: testid='{testid}' legend='{legend_text}'")

            for fs in wheel_fieldsets:
                size_categories = fs.find_elements(
                    By.CSS_SELECTOR, 'div[data-testid="feature-categories-grid-test-id"]'
                )

                if size_categories:
                    for size_category in size_categories:
                        try:
                            size = ""
                            try:
                                size_elem = size_category.find_element(
                                    By.CSS_SELECTOR,
                                    'h3[data-testid="feature-categories-grid-subtitle-test-id"] span'
                                )
                                size = size_elem.text.strip()
                                print(f"  Processing wheel size category: {size}")
                            except:
                                pass

                            wheel_items = size_category.find_elements(
                                By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]'
                            )
                            print(f"    Found {len(wheel_items)} wheels in '{size}' category")

                            for item in wheel_items:
                                try:
                                    wheel_info = self._extract_wheel_info(item, size)
                                    if wheel_info and wheel_info.get("name"):
                                        wheels_data["wheel"].append(wheel_info)
                                        print(f"      ✓ Wheel: {wheel_info['name']} ({wheel_info.get('price', '$0')})")
                                except Exception as e:
                                    print(f"      Error extracting wheel: {e}")
                                    continue
                        except Exception as e:
                            print(f"  Error processing size category: {e}")
                            continue
                else:
                    wheel_items = fs.find_elements(
                        By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]'
                    )
                    print(f"  Found {len(wheel_items)} wheels (flat, no size sub-categories)")
                    for item in wheel_items:
                        try:
                            wheel_info = self._extract_wheel_info(item, "")
                            if wheel_info and wheel_info.get("name"):
                                wheels_data["wheel"].append(wheel_info)
                                print(f"      ✓ Wheel: {wheel_info['name']} ({wheel_info.get('price', '$0')})")
                        except Exception as e:
                            print(f"      Error extracting wheel: {e}")
                            continue

            if brake_fieldsets:
                print(f"  Processing {len(brake_fieldsets)} brake fieldset(s)")
                for fs in brake_fieldsets:
                    brake_items = fs.find_elements(
                        By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]'
                    )
                    print(f"    Found {len(brake_items)} brake items")
                    for item in brake_items:
                        try:
                            brake_info = self._extract_brake_info(item)
                            if brake_info and brake_info.get("name"):
                                wheels_data["brakes"].append(brake_info)
                                print(f"      ✓ Brake: {brake_info['name']}")
                        except Exception as e:
                            print(f"      Error extracting brake: {e}")
                            continue
            else:
                print("  No brake fieldsets classified — trying fallback selectors...")

                fallback_selectors = [
                    'fieldset[data-testid*="WHEEL_BRAKES"]',
                    'fieldset[data-testid*="BRAKES"]',
                    'fieldset[data-testid*="CALIPER"]',
                    '[data-testid*="brake"]',
                    '[data-testid*="caliper"]',
                ]

                for selector in fallback_selectors:
                    try:
                        sections = wheel_tray.find_elements(By.CSS_SELECTOR, selector)
                        if sections:
                            print(f"    Found brake section via fallback: '{selector}'")
                            for section in sections:
                                brake_items = section.find_elements(
                                    By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]'
                                )
                                for item in brake_items:
                                    try:
                                        brake_info = self._extract_brake_info(item)
                                        if brake_info and brake_info.get("name"):
                                            wheels_data["brakes"].append(brake_info)
                                            print(f"      ✓ Brake: {brake_info['name']}")
                                    except:
                                        continue
                            if wheels_data["brakes"]:
                                break
                    except:
                        continue

                if not wheels_data["brakes"]:
                    print("  Trying heuristic brake detection across all wheel items...")
                    all_items = wheel_tray.find_elements(
                        By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]'
                    )
                    for item in all_items:
                        try:
                            item_text = item.text.lower()
                            if any(k in item_text for k in ["brake", "caliper", "red caliper", "yellow caliper", "blue caliper"]):
                                brake_info = self._extract_brake_info(item)
                                if brake_info and brake_info.get("name"):
                                    wheels_data["wheel"] = [
                                        w for w in wheels_data["wheel"]
                                        if w.get("name") != brake_info.get("name")
                                    ]
                                    wheels_data["brakes"].append(brake_info)
                                    print(f"      ✓ Moved to brakes (heuristic): {brake_info['name']}")
                        except:
                            continue

            print(f"  Total wheels found: {len(wheels_data['wheel'])}")
            print(f"  Total brake options found: {len(wheels_data['brakes'])}")

        except Exception as e:
            print(f"Error scraping wheels: {e}")
            import traceback
            traceback.print_exc()

        return wheels_data

    def _extract_wheel_info(self, item, size_category) -> Optional[Dict]:
        """Extract wheel information from a wheel item."""
        wheel_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "image_url": ""
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    wheel_info["name"] = aria_label
            except:
                pass

            if not wheel_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    wheel_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    if self.cloudinary_enabled:
                        cloudinary_url = self._upload_to_cloudinary(
                            img_src,
                            f"wheel_swatch_{wheel_info['name']}",
                            is_base64=False,
                            category="wheel_swatches"
                        )
                        if cloudinary_url:
                            wheel_info["swatch_image"] = cloudinary_url
                    else:
                        wheel_info["swatch_image"] = img_src
            except:
                pass

            try:
                price_elem = feature_block.find_element(By.CSS_SELECTOR, f'div[data-testid="{testid}_feature_price"]')
                price_text = price_elem.text.strip()
                if price_text and "$" in price_text:
                    wheel_info["price"] = price_text
            except:
                pass

            try:
                if "feature-block--selected" in feature_block.get_attribute("class") or "":
                    wheel_info["is_selected"] = True
            except:
                pass

            if not wheel_info["name"]:
                wheel_info["name"] = f"{size_category} wheels"

            return wheel_info if wheel_info["name"] else None

        except Exception as e:
            print(f"      Error extracting wheel info: {e}")
            return None

    def _extract_brake_info(self, item) -> Optional[Dict]:
        """Extract brake caliper information."""
        brake_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "image_url": "",
            "type": "brake_calipers",
            "category": "brakes"
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    brake_info["name"] = aria_label
            except:
                pass

            if not brake_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    brake_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    if self.cloudinary_enabled:
                        cloudinary_url = self._upload_to_cloudinary(
                            img_src,
                            f"brake_swatch_{brake_info['name']}",
                            is_base64=False,
                            category="brake_swatches"
                        )
                        if cloudinary_url:
                            brake_info["swatch_image"] = cloudinary_url
                            brake_info["image_url"] = ""
                    else:
                        brake_info["swatch_image"] = img_src
            except:
                pass

            try:
                price_elem = feature_block.find_element(By.CSS_SELECTOR, f'div[data-testid="{testid}_feature_price"]')
                price_text = price_elem.text.strip()
                if price_text and "$" in price_text:
                    brake_info["price"] = price_text
            except:
                pass

            return brake_info if brake_info["name"] else None

        except Exception as e:
            return None

    def scrape_propulsion_section(self) -> List[Dict]:
        """Scrape engine section."""
        propulsion_options = []

        SECTION_HEADING_NAMES = {"engine", "propulsion", "power", "motor"}

        try:
            time.sleep(3)
            print("  Looking for engine options...")

            propulsion_keywords = ["ENGINE", "PROPULSION", "POWER",
                                   "MOTOR", "DIESEL", "PETROL", "ELECTRIC", "HYBRID", "PHEV"]

            for keyword in propulsion_keywords:
                try:
                    elements = self.driver.find_elements(
                        By.XPATH,
                        f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
                    )
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            print(f"  Clicked propulsion tab: {keyword}")
                            time.sleep(2)
                            break
                except:
                    continue

            propulsion_selectors = [
                "[data-id*='engine']", "[data-id*='ENGINE']",
                "[data-id*='propulsion']", "[data-id*='PROPULSION']",
                "[data-id*='motor']", ".engine-option", ".propulsion-option",
                ".power-option", "[data-testid*='engine']", "[data-testid*='propulsion']",
                ".tray-block[class*='engine']", ".tray-block[class*='propulsion']"
            ]

            propulsion_blocks = []
            for selector in propulsion_selectors:
                try:
                    blocks = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if blocks:
                        propulsion_blocks = blocks
                        print(f"    Found {len(propulsion_blocks)} elements with selector: {selector}")
                        break
                except:
                    continue

            if not propulsion_blocks:
                all_blocks = self.driver.find_elements(
                    By.CSS_SELECTOR, "[data-id], .option-item, .tray-block, .config-item")
                for block in all_blocks:
                    try:
                        text = block.text.lower()
                        if any(keyword in text for keyword in [
                            "engine", "diesel", "petrol", "gasoline", "electric",
                            "hybrid", "phev", "mhev", "turbo", "v6", "v8", "i4",
                            "horsepower", "hp", "kw", "torque", "liter", "litre",
                            "cc", "cyl", "cylinder"
                        ]):
                            propulsion_blocks.append(block)
                    except:
                        continue

            print(f"  Found {len(propulsion_blocks)} potential propulsion blocks")

            propulsion_groups = {}
            for block in propulsion_blocks:
                try:
                    propulsion_id = block.get_attribute("data-id")
                    if not propulsion_id:
                        try:
                            name_elem = block.find_element(
                                By.CSS_SELECTOR, ".tray-block__line-text--description, .option-name, span, div")
                            if name_elem:
                                propulsion_id = name_elem.text.strip().replace(" ", "_")
                        except:
                            continue

                    if propulsion_id and propulsion_id not in propulsion_groups:
                        propulsion_groups[propulsion_id] = []
                    propulsion_groups[propulsion_id].append(block)
                except:
                    continue

            print(f"  Grouped into {len(propulsion_groups)} propulsion options")

            for propulsion_id, blocks in propulsion_groups.items():
                if not blocks:
                    continue
                try:
                    propulsion_info = self._extract_propulsion_info(propulsion_id, blocks)
                    if propulsion_info:
                        if propulsion_info["name"].strip().lower() in SECTION_HEADING_NAMES:
                            print(f"    - Skipping section heading: '{propulsion_info['name']}'")
                            continue
                        propulsion_options.append(propulsion_info)
                        print(f"    ✓ Extracted engine option: {propulsion_info['name']} ({propulsion_info.get('price', '0')})")
                except Exception as e:
                    print(f"    Error processing propulsion {propulsion_id}: {e}")
                    continue

            if not propulsion_options:
                propulsion_options = self._alternative_propulsion_scrape()

            print(f"  Total: Found {len(propulsion_options)} engine options")

        except Exception as e:
            print(f"Error scraping propulsion: {e}")
            import traceback
            traceback.print_exc()

        return propulsion_options

    def _alternative_propulsion_scrape(self) -> List[Dict]:
        """Alternative method to scrape propulsion options."""
        propulsion_options = []

        try:
            print("  Trying alternative propulsion scrape...")

            sections = self.driver.find_elements(
                By.CSS_SELECTOR, "section, div[class*='section'], div[class*='config'], div[role='tabpanel']")

            for section in sections:
                try:
                    section_text = section.text.lower()
                    if any(keyword in section_text for keyword in [
                        "engine", "propulsion", "power", "motor", "diesel", "petrol", "electric"
                    ]):
                        items = section.find_elements(
                            By.CSS_SELECTOR,
                            ".tray-block, .option-item, button, [role='button'], [data-id]"
                        )

                        for item in items:
                            try:
                                if not item.is_displayed():
                                    continue

                                item_text = item.text.strip()
                                if not item_text:
                                    continue

                                has_engine_info = any(keyword in item_text.lower() for keyword in [
                                    "engine", "diesel", "petrol", "electric", "hybrid",
                                    "v6", "v8", "i4", "hp", "kw", "nm", "torque"
                                ])

                                if has_engine_info:
                                    propulsion_info = {
                                        "name": item_text.split('\n')[0] if '\n' in item_text else item_text,
                                        "price": "$0",
                                        "specs": self._parse_propulsion_specs(item_text)
                                    }

                                    price_match = re.search(r'(\$\d+[\d,\.]*)', item_text)
                                    if price_match:
                                        propulsion_info["price"] = price_match.group(1)

                                    try:
                                        img = item.find_element(By.TAG_NAME, "img")
                                        if img:
                                            src = img.get_attribute("src") or img.get_attribute("data-src")
                                            if src:
                                                propulsion_info["image_url"] = src
                                    except:
                                        pass

                                    if propulsion_info["name"].strip().lower() in {"engine", "propulsion", "power", "motor"}:
                                        print(f"    - Skipping section heading (alt): '{propulsion_info['name']}'")
                                        continue
                                    propulsion_options.append(propulsion_info)
                                    print(f"    ✓ Found engine option (alt): {propulsion_info['name']}")

                            except:
                                continue
                except:
                    continue

        except Exception as e:
            print(f"  Error in alternative propulsion scrape: {e}")

        return propulsion_options

    def _extract_propulsion_info(self, propulsion_id: str, blocks: List) -> Optional[Dict]:
        """Extract propulsion information from a group of blocks."""
        propulsion_info = {
            "name": "",
            "price": "$0",
            "image_url": "",
            "specs": {}
        }

        for block in blocks:
            try:
                name_selectors = [
                    ".tray-block__line-text--description",
                    ".option-name", ".engine-name", ".propulsion-name",
                    "[data-testid='block-desc']", "h3", "h4", "span"
                ]
                for selector in name_selectors:
                    try:
                        name_elem = block.find_element(By.CSS_SELECTOR, selector)
                        if name_elem and name_elem.text.strip():
                            propulsion_info["name"] = name_elem.text.strip()
                            break
                    except:
                        continue

                price_selectors = [
                    ".tray-block__line--pricing .tray-block__line-text",
                    ".option-price", ".price", "[data-testid='block-price']", ".pricing"
                ]
                for selector in price_selectors:
                    try:
                        price_elem = block.find_element(By.CSS_SELECTOR, selector)
                        if price_elem:
                            price_text = price_elem.text.strip()
                            if price_text and "$" in price_text:
                                propulsion_info["price"] = price_text
                            break
                    except:
                        continue

                img_selectors = [
                    ".tray-block-image__image", "img", "picture source",
                    "[src*='.jpg']", "[src*='.png']", "[src*='.svg']"
                ]
                for selector in img_selectors:
                    try:
                        img_elem = block.find_element(By.CSS_SELECTOR, selector)
                        if img_elem:
                            src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                            if src:
                                propulsion_info["image_url"] = src
                            break
                    except:
                        continue

                if propulsion_info["name"]:
                    propulsion_info["specs"] = self._parse_propulsion_specs(propulsion_info["name"])

            except:
                continue

        if propulsion_info["name"]:
            return propulsion_info

        return None

    def _parse_propulsion_specs(self, text: str) -> Dict:
        """Parse propulsion specifications from text."""
        specs = {}
        text_lower = text.lower()

        if "diesel" in text_lower:
            specs["fuel_type"] = "diesel"
        elif "petrol" in text_lower or "gasoline" in text_lower:
            specs["fuel_type"] = "petrol"
        elif "electric" in text_lower:
            specs["fuel_type"] = "electric"
        elif "hybrid" in text_lower:
            specs["fuel_type"] = "hybrid"
        elif "phev" in text_lower:
            specs["fuel_type"] = "plug-in_hybrid"

        if "v6" in text_lower or "v 6" in text_lower:
            specs["configuration"] = "V6"
        elif "v8" in text_lower or "v 8" in text_lower:
            specs["configuration"] = "V8"
        elif "i4" in text_lower or "inline-4" in text_lower:
            specs["configuration"] = "I4"
        elif "i6" in text_lower or "inline-6" in text_lower:
            specs["configuration"] = "I6"
        elif "i3" in text_lower or "inline-3" in text_lower:
            specs["configuration"] = "I3"

        hp_match = re.search(r'(\d+)\s*(hp|HP|horsepower|bhp)', text)
        if hp_match:
            specs["horsepower"] = f"{hp_match.group(1)} hp"

        kw_match = re.search(r'(\d+)\s*(kw|KW|kW)', text)
        if kw_match:
            specs["power"] = f"{kw_match.group(1)} kW"

        nm_match = re.search(r'(\d+)\s*(nm|NM|Nm|N·m)', text)
        if nm_match:
            specs["torque"] = f"{nm_match.group(1)} Nm"

        liter_match = re.search(r'(\d+\.?\d*)\s*(l|L|liter|litre)', text)
        if liter_match:
            specs["displacement"] = f"{liter_match.group(1)}L"

        cc_match = re.search(r'(\d+)\s*(cc|CC)', text)
        if cc_match:
            specs["displacement"] = f"{cc_match.group(1)} cc"

        cyl_match = re.search(r'(\d+)\s*(cyl|cylinder)', text, re.IGNORECASE)
        if cyl_match:
            specs["cylinders"] = cyl_match.group(1)

        return specs

    def scrape_options_section(self) -> List[Dict]:
        """Scrape options section - handles overlay structure."""
        options = []

        try:
            time.sleep(4)
            print("  Looking for options...")

            options_section = None
            try:
                options_section = self.driver.find_element(
                    By.CSS_SELECTOR,
                    'div[data-tray-id="options_configuration"]'
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", options_section)
                time.sleep(2)
            except:
                print("  Could not find options section")
                return []

            feature_basket_buttons = options_section.find_elements(
                By.CSS_SELECTOR,
                'button[data-testid="feature-basket-button-test-id"]'
            )

            if feature_basket_buttons:
                print(f"  Found {len(feature_basket_buttons)} feature basket buttons")
                print("  Opening feature basket overlay...")
                self.driver.execute_script("arguments[0].click();", feature_basket_buttons[0])
                time.sleep(3)

                print("  Extracting options from overlay...")

                overlay_sections = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'div[data-testid="feature-basket-overlay-section-item-test-id"]'
                )

                print(f"  Found {len(overlay_sections)} overlay sections")

                for section in overlay_sections:
                    try:
                        title_elem = section.find_element(
                            By.CSS_SELECTOR,
                            'h2[data-testid="feature-basket-overlay-block-group-heading-test-id"]'
                        )
                        section_title = title_elem.text.strip()
                        if '(' in section_title:
                            section_title = section_title.split('(')[0].strip()

                        print(f"  Processing section: {section_title}")

                        feature_blocks = section.find_elements(
                            By.CSS_SELECTOR,
                            'div[data-testid$="_feature"]'
                        )

                        for block in feature_blocks:
                            try:
                                option_info = self._extract_overlay_option_info(block, section_title)
                                if option_info and option_info.get("name"):
                                    options.append(option_info)
                                    print(f"    ✓ {option_info['name']} ({option_info['price']})")
                            except Exception as e:
                                continue

                    except Exception as e:
                        print(f"  Error processing overlay section: {e}")
                        continue

                try:
                    close_buttons = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'button[data-testid="feature-basket-overlay-close-button-test-id"]'
                    )
                    if close_buttons:
                        self.driver.execute_script("arguments[0].click();", close_buttons[0])
                        time.sleep(2)
                except:
                    pass

            else:
                print("  No feature basket buttons found")
                options = self._extract_options_directly()

            unique_options = []
            seen_names = set()
            for opt in options:
                name_lower = opt["name"].lower()
                if name_lower not in seen_names:
                    seen_names.add(name_lower)
                    unique_options.append(opt)

            print(f"  Total unique options found: {len(unique_options)}")
            return unique_options

        except Exception as e:
            print(f"Error scraping options: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_overlay_option_info(self, block, section_title) -> Optional[Dict]:
        """Extract option information from an overlay feature block."""
        option_info = {
            "name": "",
            "price": "$0",
            "image_url": "",
            "description": "",
            "category": section_title,
            "is_selected": False,
            "option_id": ""
        }

        try:
            testid = block.get_attribute("data-testid") or ""
            if testid and testid.endswith("_feature"):
                option_info["option_id"] = testid.replace("_feature", "")

            try:
                link = block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    option_info["name"] = aria_label
            except:
                pass

            if not option_info["name"]:
                try:
                    heading = block.find_element(By.CSS_SELECTOR, 'span[data-testid$="_feature_heading"]')
                    option_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                sub_heading = block.find_element(By.CSS_SELECTOR, 'span[data-testid$="_feature_sub_heading"]')
                option_info["description"] = sub_heading.text.strip()
            except:
                pass

            try:
                price_elem = block.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature_price"]')
                price_text = price_elem.text.strip()
                if price_text and "$" in price_text:
                    option_info["price"] = price_text
            except:
                pass

            try:
                img = block.find_element(By.CSS_SELECTOR, 'img[data-testid$="_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    if self.cloudinary_enabled and img_src:
                        cloudinary_url = self._upload_to_cloudinary(
                            img_src,
                            f"option_{option_info['name']}",
                            is_base64=False,
                            category="options"
                        )
                        if cloudinary_url:
                            option_info["image_url"] = cloudinary_url
                        else:
                            option_info["image_url"] = img_src
                    else:
                        option_info["image_url"] = img_src
            except:
                pass

            try:
                block_class = block.get_attribute("class") or ""
                if "feature-block--selected" in block_class:
                    option_info["is_selected"] = True
                try:
                    input_elem = block.find_element(By.CSS_SELECTOR, 'input[data-testid$="_input"]')
                    if input_elem.get_attribute("checked") == "true":
                        option_info["is_selected"] = True
                except:
                    pass
            except:
                pass

            try:
                block.find_element(By.CSS_SELECTOR, '[data-testid$="_suggested"]')
                option_info["is_recommended"] = True
            except:
                pass

            return option_info if option_info["name"] else None

        except Exception as e:
            print(f"      Error extracting overlay option info: {e}")
            return None

    def _extract_options_directly(self) -> List[Dict]:
        """Extract options directly from the page if overlay not found."""
        options = []

        try:
            feature_blocks = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[data-testid$="_feature"]'
            )

            print(f"  Found {len(feature_blocks)} feature blocks directly on page")

            for block in feature_blocks:
                try:
                    category = "Options"
                    try:
                        parent = block
                        for _ in range(5):
                            parent = parent.find_element(By.XPATH, "..")
                            parent_text = parent.text
                            if any(keyword in parent_text.upper() for keyword in
                                   ["EXTERIOR", "INTERIOR", "SAFETY", "TECH", "LOADSPACE", "INFOTAINMENT"]):
                                category = parent_text.split('\n')[0]
                                break
                    except:
                        pass

                    option_info = self._extract_overlay_option_info(block, category)
                    if option_info and option_info.get("name"):
                        options.append(option_info)
                        print(f"    ✓ Found option: {option_info['name']}")

                except Exception as e:
                    continue

        except Exception as e:
            print(f"  Error in direct option extraction: {e}")

        return options

    def _emergency_option_search(self) -> List[Dict]:
        """Emergency search for options when normal methods fail."""
        options = []

        try:
            print("  Starting emergency option search...")

            all_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div, button, a, li, section, [data-testid], [data-id], [class*='item']"
            )

            print(f"  Scanning {len(all_elements)} elements...")

            option_keywords = [
                "pack", "package", "feature", "option", "system", "assist", "camera",
                "sensor", "tech", "technology", "audio", "sound", "navigation", "media",
                "climate", "heated", "cooled", "ventilated", "massage", "memory",
                "safety", "security", "assistance", "comfort", "convenience",
                "performance", "sport", "handling", "suspension", "brake",
                "light", "lighting", "led", "headlight", "taillight",
                "tow", "towing", "hitch", "trailer", "roof", "sunroof",
                "panoramic", "glass", "moonroof", "keyless", "remote", "start"
            ]

            found_count = 0
            for element in all_elements[:300]:
                try:
                    if not element.is_displayed():
                        continue

                    text = element.text.strip()
                    if not text or len(text) > 150:
                        continue

                    text_lower = text.lower()

                    is_option = any(keyword in text_lower for keyword in option_keywords)
                    has_price = '$' in text

                    is_basic = any(keyword in text_lower for keyword in [
                        "color", "paint", "wheel", "rim", "tire",
                        "engine", "propulsion", "diesel", "petrol", "electric", "hybrid"
                    ])

                    if (is_option or has_price) and not is_basic:
                        option_info = {
                            "name": text.split('\n')[0] if '\n' in text else text,
                            "price": "$0",
                            "description": "",
                            "image_url": ""
                        }

                        if has_price:
                            price_match = re.search(r'(\$\d+[\d,\.]*)', text)
                            if price_match:
                                option_info["price"] = price_match.group(1)

                        name_lower = option_info["name"].lower()
                        if any(keyword in name_lower for keyword in ["tech", "technology", "audio", "navigation"]):
                            option_info["category"] = "technology"
                        elif any(keyword in name_lower for keyword in ["safety", "security", "assist"]):
                            option_info["category"] = "safety"
                        elif any(keyword in name_lower for keyword in ["comfort", "climate", "heated"]):
                            option_info["category"] = "comfort"
                        elif any(keyword in name_lower for keyword in ["pack", "package"]):
                            option_info["category"] = "packages"

                        options.append(option_info)
                        found_count += 1

                        if found_count <= 10:
                            print(f"    ⚡ Emergency option found: {option_info['name']} ({option_info['price']})")

                        if found_count >= 30:
                            print(f"    Reached limit of 30 options")
                            break

                except:
                    continue

            print(f"  Emergency search found {len(options)} options")

        except Exception as e:
            print(f"  Error in emergency option search: {e}")

        return options

    def scrape_accessories_section(self) -> List[Dict]:
        """Scrape accessories section with working overlay scraper."""
        accessories = []

        try:
            time.sleep(3)
            print("  Looking for accessories...")

            accessories_section = None
            try:
                accessories_section = self.driver.find_element(
                    By.CSS_SELECTOR,
                    'div[data-tray-id="accessories"]'
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", accessories_section)
                time.sleep(2)
            except:
                print("  Could not find accessories section")
                return []

            feature_basket_buttons = accessories_section.find_elements(
                By.CSS_SELECTOR,
                'button[data-testid="feature-basket-button-test-id"]'
            )

            if feature_basket_buttons:
                print(f"  Found {len(feature_basket_buttons)} feature basket buttons")

                for button_idx, button in enumerate(feature_basket_buttons):
                    try:
                        try:
                            category_elem = button.find_element(
                                By.CSS_SELECTOR,
                                'span[data-testid="feature-basket-block-group-heading-test-id"]'
                            )
                            category = category_elem.text.strip()
                        except:
                            category = f"Accessories {button_idx + 1}"

                        print(f"  Opening {category} overlay...")
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)

                        feature_sections = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            'div[data-testid="feature-basket-overlay-section-item-test-id"]'
                        )

                        for section in feature_sections:
                            try:
                                section_header = section.find_element(
                                    By.CSS_SELECTOR,
                                    'h2[data-testid="feature-basket-overlay-block-group-heading-test-id"]'
                                )
                                section_category = section_header.text.strip()
                                section_category = section_category.split('selected')[0].strip()
                            except:
                                section_category = category

                            feature_blocks = section.find_elements(
                                By.CSS_SELECTOR,
                                'div[data-testid$="_feature"][data-href]'
                            )

                            for block in feature_blocks:
                                try:
                                    name_elem = block.find_element(
                                        By.CSS_SELECTOR,
                                        'span[data-testid$="_feature_heading"]'
                                    )
                                    name = name_elem.text.strip()

                                    if not name or len(name) < 3:
                                        continue

                                    price = "$0"
                                    try:
                                        price_elem = block.find_element(
                                            By.CSS_SELECTOR,
                                            'div[data-testid$="_feature_price"]'
                                        )
                                        price = price_elem.text.strip()
                                    except:
                                        pass

                                    image_url = ""
                                    try:
                                        img_elem = block.find_element(
                                            By.CSS_SELECTOR,
                                            'img[data-testid$="_feature_img"]'
                                        )
                                        image_url = img_elem.get_attribute('src') or ""
                                    except:
                                        pass

                                    description = ""
                                    try:
                                        desc_elem = block.find_element(
                                            By.CSS_SELECTOR,
                                            'span[data-testid$="_feature_sub_heading"]'
                                        )
                                        description = desc_elem.text.strip()
                                    except:
                                        pass

                                    is_recommended = False
                                    try:
                                        block.find_element(By.CSS_SELECTOR, '[data-testid$="_suggested"]')
                                        is_recommended = True
                                    except:
                                        pass

                                    accessory_info = {
                                        "name": name,
                                        "price": price,
                                        "image_url": image_url,
                                        "category": section_category,
                                        "description": description,
                                        "is_recommended": is_recommended
                                    }

                                    duplicate = any(
                                        existing["name"].lower() == name.lower()
                                        for existing in accessories
                                    )

                                    if not duplicate:
                                        accessories.append(accessory_info)
                                        rec_marker = "★" if is_recommended else ""
                                        print(f"    ✓ {rec_marker} {name} ({price}) - {section_category}")

                                except Exception as e:
                                    continue

                        try:
                            close_buttons = self.driver.find_elements(
                                By.CSS_SELECTOR,
                                'button[data-testid="feature-basket-overlay-close-button-test-id"]'
                            )
                            if close_buttons:
                                self.driver.execute_script("arguments[0].click();", close_buttons[0])
                                time.sleep(2)
                        except:
                            pass

                    except Exception as e:
                        print(f"  Error processing button {button_idx + 1}: {e}")
                        continue

            else:
                print("  No feature basket buttons, checking for suggested accessories...")

                try:
                    suggested_section = accessories_section.find_element(
                        By.CSS_SELECTOR,
                        'div._suggested-features__container_vh37w_22'
                    )

                    feature_blocks = suggested_section.find_elements(
                        By.CSS_SELECTOR,
                        'div[data-testid$="_feature"][data-href]'
                    )

                    print(f"  Found {len(feature_blocks)} suggested accessories")

                    for block in feature_blocks:
                        try:
                            name_elem = block.find_element(
                                By.CSS_SELECTOR,
                                'span[data-testid$="_feature_heading"]'
                            )
                            name = name_elem.text.strip()

                            if not name or len(name) < 3:
                                continue

                            price = "$0"
                            try:
                                price_elem = block.find_element(
                                    By.CSS_SELECTOR,
                                    'div[data-testid$="_feature_price"]'
                                )
                                price = price_elem.text.strip()
                            except:
                                pass

                            image_url = ""
                            try:
                                img_elem = block.find_element(
                                    By.CSS_SELECTOR,
                                    'img[data-testid$="_feature_img"]'
                                )
                                image_url = img_elem.get_attribute('src') or ""
                            except:
                                pass

                            accessory_info = {
                                "name": name,
                                "price": price,
                                "image_url": image_url,
                                "category": "Suggested Accessories",
                                "description": "",
                                "is_recommended": True
                            }

                            accessories.append(accessory_info)
                            print(f"    ✓ ★ {name} ({price})")

                        except Exception as e:
                            continue
                except Exception as e:
                    print(f"  Error scraping suggested accessories: {e}")

            unique_accessories = []
            seen_names = set()
            for acc in accessories:
                if acc["name"].lower() not in seen_names:
                    seen_names.add(acc["name"].lower())
                    unique_accessories.append(acc)

            print(f"  Total unique accessories found: {len(unique_accessories)}")

        except Exception as e:
            print(f"Error scraping accessories: {e}")
            import traceback
            traceback.print_exc()

        return unique_accessories

    def _scrape_fieldset(self, fieldset) -> List[Dict]:
        """Scrapes blocks within a fieldset container."""
        items = []
        try:
            blocks = fieldset.find_elements(
                By.CSS_SELECTOR, "div[data-testid$='_feature'], div[class*='feature-block_']")
            seen = set()
            for block in blocks:
                data = self._extract_item_from_block(block)
                if data and data["name"] and data["name"] not in seen:
                    if len(data["name"]) < 3:
                        continue
                    items.append(data)
                    seen.add(data["name"])
        except Exception as e:
            print(f"    ! Error scraping fieldset: {e}")
        return items

    def _scrape_tray(self, tray_id: str) -> Dict[str, Any]:
        """Scrapes a specific tray returning grouped items."""
        results = {}
        print(f"  - Scraping tray contents: {tray_id}...")

        try:
            selector = f"div[data-tray-id='{tray_id}']"
            try:
                tray = self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                try:
                    tray = self.driver.find_element(By.ID, tray_id)
                except:
                    print(f"    x Tray element not found in DOM.")
                    return {}

            fieldsets = tray.find_elements(By.TAG_NAME, "fieldset")

            if not fieldsets:
                items = self._scrape_fieldset(tray)
                if items:
                    results["General"] = items

            for fs in fieldsets:
                group_name = "Options"
                try:
                    group_name = fs.find_element(By.TAG_NAME, "legend").text.strip()
                except:
                    try:
                        group_name = fs.find_element(By.CSS_SELECTOR, "h3, h4").text.strip()
                    except:
                        pass

                if not group_name:
                    group_name = "Options"

                items = self._scrape_fieldset(fs)
                if items:
                    if group_name in results:
                        results[group_name].extend(items)
                    else:
                        results[group_name] = items
                    print(f"    + Found {len(items)} items in group '{group_name}'")

        except Exception as e:
            print(f"    ! Error in tray scrape: {e}")

        return results

    def _scrape_exterior_fieldset(self, fieldset) -> List[Dict]:
        """
        Scrape exterior pack / side-step items using the EXACT HTML structure
        from the Land Rover configurator.

        Each item is a <li data-testid="feature-grid-item-test-id"> OR a
        <li class="*tray-list-item*"> containing a div[data-testid$="_feature"].

        Extracts:
          name        – from aria-label on the <a> link, or the heading <span>
          price       – from div[data-testid$="_feature_price"]
          image_url   – from img[data-testid$="_feature_img"] (uploaded to Cloudinary)
          is_selected – True when the feature-block has --selected class
          is_recommended – True when the _suggested pill is present
        """
        items = []
        seen = set()

        try:
            # Support both grid-item li (wheels style) and tray-list-item li (packs style)
            li_elements = fieldset.find_elements(
                By.CSS_SELECTOR,
                "li[data-testid='feature-grid-item-test-id'], "
                "li[class*='tray-list-item']"
            )

            # Fallback: grab feature blocks directly if no li wrappers
            if not li_elements:
                li_elements = fieldset.find_elements(
                    By.CSS_SELECTOR, "div[data-testid$='_feature']"
                )

            for li in li_elements:
                try:
                    # Locate the feature block div (may BE the li itself for fallback)
                    try:
                        block = li.find_element(By.CSS_SELECTOR, "div[data-testid$='_feature']")
                    except:
                        block = li

                    testid = block.get_attribute("data-testid") or ""

                    item = {
                        "name": "",
                        "price": "$0",
                        "image_url": "",
                        "is_selected": False,
                        "is_recommended": False,
                    }

                    # ── Name: prefer aria-label on the <a> link ───────────────
                    try:
                        link = block.find_element(By.CSS_SELECTOR, "a[data-testid$='_link']")
                        item["name"] = (link.get_attribute("aria-label") or "").strip()
                    except:
                        pass

                    # Fallback: heading span
                    if not item["name"]:
                        try:
                            hdg = block.find_element(
                                By.CSS_SELECTOR,
                                "span[data-testid$='_feature_heading'] span, "
                                "span[data-testid$='_feature_heading']"
                            )
                            item["name"] = hdg.text.strip()
                        except:
                            pass

                    if not item["name"] or item["name"] in seen:
                        continue
                    seen.add(item["name"])

                    # ── Price ─────────────────────────────────────────────────
                    try:
                        price_el = block.find_element(
                            By.CSS_SELECTOR, "div[data-testid$='_feature_price']"
                        )
                        pt = price_el.text.strip()
                        if pt:
                            item["price"] = pt
                    except:
                        pass

                    # ── Image ─────────────────────────────────────────────────
                    # Selector: img[data-testid$="_feature_img"] — exact from HTML
                    try:
                        img_el = block.find_element(
                            By.CSS_SELECTOR, "img[data-testid$='_feature_img']"
                        )
                        img_src = (img_el.get_attribute("src") or "").strip()
                        if not img_src:
                            img_src = (img_el.get_attribute("data-src") or "").strip()
                        if img_src:
                            if self.cloudinary_enabled:
                                # Sanitise name for Cloudinary public_id
                                safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', item['name'])[:60]
                                cl_url = self._upload_to_cloudinary(
                                    img_src,
                                    safe_name,
                                    is_base64=False,
                                    category="exterior_packs"
                                )
                                item["image_url"] = cl_url if cl_url else img_src
                            else:
                                item["image_url"] = img_src
                    except:
                        pass

                    # ── Selected state ────────────────────────────────────────
                    # The site uses CSS modules so classes are mangled:
                    # e.g. "_feature-block--selected_bzvz1_118"
                    # Check both the class substring AND the input checked attr.
                    try:
                        block_cls = block.get_attribute("class") or ""
                        # CSS module class contains "--selected" as a substring
                        if "--selected" in block_cls:
                            item["is_selected"] = True
                        else:
                            # Fall back to checking the input element's checked attribute
                            inp = block.find_element(
                                By.CSS_SELECTOR,
                                "input[data-testid$='_input']"
                            )
                            # In Selenium, a present `checked` attr returns "" or "true";
                            # absent returns None.
                            checked_val = inp.get_attribute("checked")
                            item["is_selected"] = checked_val is not None
                    except:
                        pass

                    # ── Recommended pill ──────────────────────────────────────
                    try:
                        block.find_element(By.CSS_SELECTOR, "[data-testid$='_suggested']")
                        item["is_recommended"] = True
                    except:
                        pass

                    items.append(item)
                    rec = " ★" if item["is_recommended"] else ""
                    sel = " [selected]" if item["is_selected"] else ""
                    print(f"      ✓ {item['name']} ({item['price']}){rec}{sel}")

                except Exception as e:
                    print(f"      ! Error reading exterior item: {e}")
                    continue

        except Exception as e:
            print(f"    ! Error in _scrape_exterior_fieldset: {e}")

        return items

    def _scrape_exterior_tray(self) -> Dict[str, List]:
        """
        Scrape ALL non-color fieldsets inside the exterior tray using the
        exact HTML structure (`data-testid` on fieldset identifies the group).

        Returns a dict keyed by category:
          exterior_packs, side_steps, roof_type, glass, headlights, …
        """
        result = {
            "exterior_packs": [],
            "side_steps": [],
            "roof_type": [],
            "glass": [],
            "headlights": [],
        }

        # Map of keywords found in the fieldset data-testid / legend → bucket
        BUCKET_MAP = [
            # (keywords_in_testid_or_legend,   bucket_key)
            (["EXTERIOR_PACKS", "EXT_PACK", "EXTERIOR PACK", "EXTERIOR PACKS"],  "exterior_packs"),
            (["EXT_OPTIONS",    "SIDE_STEP", "SIDE STEP", "SIDE STEPS"],          "side_steps"),
            (["ROOF_TYPE",      "ROOF TYPE", "ROOF STYLE"],                        "roof_type"),
            (["GLASS",          "WINDOW",    "GLAZING"],                            "glass"),
            (["HEADLIGHT",      "HEADLAMP",  "FRONT LIGHT"],                       "headlights"),
        ]

        # Colour-related testids/legends — skip these, handled separately
        COLOR_SKIP = ["PAINT", "COLOUR", "COLOR", "ROOF_COLOUR", "ROOF_COLOR"]

        try:
            tray = self.driver.find_element(
                By.CSS_SELECTOR, "div[data-tray-id='exterior']"
            )
            fieldsets = tray.find_elements(By.TAG_NAME, "fieldset")
            print(f"  _scrape_exterior_tray: found {len(fieldsets)} fieldsets")

            for fs in fieldsets:
                testid  = (fs.get_attribute("data-testid") or "").upper()
                try:
                    legend = fs.find_element(By.CSS_SELECTOR,
                        "legend[data-testid='tray-group-legend-test-Id'], legend"
                    ).text.strip().upper()
                except:
                    legend = ""

                combined = testid + " " + legend

                # Skip colour fieldsets
                if any(skip in combined for skip in COLOR_SKIP):
                    print(f"    Skipping colour fieldset: testid='{testid}' legend='{legend}'")
                    continue

                # Find matching bucket
                bucket = None
                for keywords, key in BUCKET_MAP:
                    if any(kw in combined for kw in keywords):
                        bucket = key
                        break

                if bucket is None:
                    # Unknown non-colour fieldset — skip for now
                    print(f"    Unknown exterior fieldset (skipped): testid='{testid}' legend='{legend}'")
                    continue

                print(f"  Scraping exterior fieldset → '{bucket}': testid='{testid}' legend='{legend}'")
                items = self._scrape_exterior_fieldset(fs)
                if items:
                    result[bucket].extend(items)
                    print(f"    → {len(items)} items in '{bucket}'")

        except Exception as e:
            print(f"  ! Error in _scrape_exterior_tray: {e}")
            import traceback
            traceback.print_exc()

        # Remove empty buckets
        return {k: v for k, v in result.items() if v}

    # =====================================================================
    # ROOF COLOR SCRAPING METHODS
    # =====================================================================

    def scrape_roof_colors(self) -> List[Dict]:
        """Scrape roof colors specifically."""
        roof_colors = []

        try:
            print("  Looking for roof colors...")
            time.sleep(2)

            roof_keywords = ["ROOF", "ROOF COLOR", "CONTRAST ROOF",
                             "SECOND COLOR", "DUAL-TONE", "CONTRAST"]

            for keyword in roof_keywords:
                try:
                    if self.navigate_to_section(keyword) or self._click_subnav_item(keyword):
                        print(f"  Found {keyword} section")
                        time.sleep(3)
                        break
                except:
                    continue

            roof_color_selectors = [
                "[data-id*='roof']", "[data-id*='ROOF']",
                "[data-id*='contrast']", ".roof-color-option",
                ".contrast-roof-option", "[data-testid*='roof']",
                "[data-testid*='ROOF']", ".tray-block[class*='roof']",
                ".tray-block[class*='contrast']",
                "[aria-label*='roof']", "[aria-label*='ROOF']"
            ]

            roof_color_blocks = []
            for selector in roof_color_selectors:
                try:
                    blocks = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if blocks:
                        roof_color_blocks = blocks
                        print(f"    Found {len(roof_color_blocks)} elements with selector: {selector}")
                        break
                except:
                    continue

            if not roof_color_blocks:
                all_blocks = self.driver.find_elements(
                    By.CSS_SELECTOR, "[data-id], .option-item, .tray-block, .config-item")
                for block in all_blocks:
                    try:
                        text = block.text.lower()
                        if any(keyword in text for keyword in [
                            "roof", "contrast", "contrasting", "second color", "dual",
                            "two-tone", "different roof", "roof in"
                        ]):
                            roof_color_blocks.append(block)
                    except:
                        continue

            print(f"  Found {len(roof_color_blocks)} potential roof color blocks")

            processed_roof_colors = {}
            for block in roof_color_blocks:
                try:
                    roof_info = self._extract_roof_color_info(block)

                    if roof_info and roof_info.get("name"):
                        clean_name = roof_info["name"].strip().lower()
                        if clean_name not in processed_roof_colors:
                            screenshot_url = self.capture_exterior_color_screenshot(f"roof_{roof_info['name']}")
                            if screenshot_url:
                                roof_info["image_url"] = screenshot_url
                            processed_roof_colors[clean_name] = roof_info
                            print(f"    ✓ Found roof color: {roof_info['name']} ({roof_info.get('price', '0')})")
                except Exception as e:
                    print(f"    Error processing roof color block: {e}")
                    continue

            roof_colors = list(processed_roof_colors.values())

            if not roof_colors:
                print("  No specific roof colors found, checking if regular colors can be used as roof colors...")
                all_colors = self.scrape_exterior_colors()
                for color in all_colors:
                    color_name_lower = color.get("name", "").lower()
                    if any(keyword in color_name_lower for keyword in
                           ["white", "black", "gray", "grey", "silver", "chrome", "gloss"]):
                        roof_colors.append(color)

                if roof_colors:
                    print(f"    Using {len(roof_colors)} regular colors as potential roof colors")

            print(f"  Total roof colors found: {len(roof_colors)}")

        except Exception as e:
            print(f"Error scraping roof colors: {e}")
            import traceback
            traceback.print_exc()

        return roof_colors

    def _extract_roof_color_info(self, block) -> Optional[Dict]:
        """Extract roof color information from a block."""
        roof_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "image_url": "",
            "type": "roof_color"
        }

        try:
            name_selectors = [
                ".tray-block__line-text--description",
                ".option-name", ".roof-name", ".color-name",
                "[data-testid='block-desc']", "span", "div"
            ]

            for selector in name_selectors:
                try:
                    name_elem = block.find_element(By.CSS_SELECTOR, selector)
                    if name_elem and name_elem.text.strip():
                        roof_info["name"] = name_elem.text.strip()
                        break
                except:
                    continue

            if not roof_info["name"]:
                for attr in ['aria-label', 'title', 'data-name', 'data-id']:
                    attr_value = block.get_attribute(attr) or ""
                    if attr_value:
                        roof_info["name"] = attr_value
                        break

            price_selectors = [
                ".tray-block__line--pricing .tray-block__line-text",
                ".option-price", ".price", "[data-testid='block-price']", ".pricing"
            ]

            for selector in price_selectors:
                try:
                    price_elem = block.find_element(By.CSS_SELECTOR, selector)
                    if price_elem:
                        price_text = price_elem.text.strip()
                        if price_text and "$" in price_text:
                            roof_info["price"] = price_text
                        break
                except:
                    continue

            img_selectors = [
                ".tray-block-image__image", "img", "picture source",
                "[src*='.jpg']", "[src*='.png']", "[src*='.webp']"
            ]

            for selector in img_selectors:
                try:
                    img_elem = block.find_element(By.CSS_SELECTOR, selector)
                    if img_elem:
                        src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                        if src:
                            roof_info["swatch_image"] = src
                        break
                except:
                    continue

            if roof_info["swatch_image"] and self.cloudinary_enabled and roof_info["swatch_image"].startswith('http'):
                try:
                    cloudinary_url = self._upload_to_cloudinary(
                        roof_info["swatch_image"],
                        f"swatch_roof_{roof_info['name']}",
                        is_base64=False,
                        category="roof_swatches"
                    )
                    if cloudinary_url:
                        roof_info["swatch_image"] = cloudinary_url
                except:
                    pass

            try:
                if block.is_displayed() and block.is_enabled():
                    is_selected = False
                    block_class = block.get_attribute("class") or ""
                    if any(selected in block_class.lower() for selected in ["selected", "active", "current"]):
                        is_selected = True
                        print(f"      Roof color '{roof_info['name']}' is already selected")

                    if not is_selected:
                        try:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", block)
                            time.sleep(1)
                            block.click()
                            time.sleep(2)
                        except:
                            self.driver.execute_script("arguments[0].click();", block)
                            time.sleep(2)

                    car_image = self._get_current_car_image_url(f"roof_{roof_info['name']}")
                    if car_image:
                        if car_image.startswith('data:image/png;base64,'):
                            cloudinary_url = self._upload_to_cloudinary(
                                car_image,
                                f"roof_color_{roof_info['name']}",
                                is_base64=True,
                                category="roof_colors"
                            )
                            if cloudinary_url:
                                roof_info["image_url"] = cloudinary_url
            except:
                pass

            return roof_info if roof_info["name"] else None

        except Exception as e:
            print(f"    Error extracting roof color info: {e}")
            return None

    def _find_roof_color_options(self) -> List[Dict]:
        """Find roof color options on the current page."""
        roof_colors = []

        try:
            roof_selectors = [
                "[data-id*='roof-color']", "[data-testid*='roof-color']",
                "[class*='roof-color']", "[aria-label*='roof color']",
                "[title*='roof color']"
            ]

            for selector in roof_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            if element.is_displayed():
                                roof_info = self._extract_roof_color_info(element)
                                if roof_info and roof_info.get("name"):
                                    duplicate = any(
                                        existing["name"].lower() == roof_info["name"].lower()
                                        for existing in roof_colors
                                    )
                                    if not duplicate:
                                        roof_colors.append(roof_info)
                                        print(f"      Found roof color: {roof_info['name']}")
                        except:
                            continue
                except:
                    continue

            all_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div, button, [role='button'], [data-testid], [data-id], .option-item"
            )

            for element in all_elements[:100]:
                try:
                    if not element.is_displayed():
                        continue

                    text = element.text.lower()
                    if any(keyword in text for keyword in [
                        "contrast roof", "roof color", "roof in", "second color",
                        "dual-tone", "two-tone", "contrasting"
                    ]):
                        roof_info = self._extract_roof_color_info(element)
                        if roof_info and roof_info.get("name"):
                            duplicate = any(
                                existing["name"].lower() == roof_info["name"].lower()
                                for existing in roof_colors
                            )
                            if not duplicate:
                                roof_colors.append(roof_info)
                                print(f"      Found roof color by text: {roof_info['name']}")
                except:
                    continue

        except Exception as e:
            print(f"    Error finding roof color options: {e}")

        return roof_colors

    # =====================================================================
    # INTERIOR SCRAPING METHODS
    # =====================================================================

    def scrape_interior_section(self) -> Dict[str, Any]:
        """Scrape interior section with proper HTML structure handling."""
        print("\n=== SCRAPING INTERIOR ===")

        interior_data = {
            "trims": [],
            "controls": [],
            "headlining": [],
            "finishers": [],
            "interior_upgrade": []
        }

        try:
            if not (self._navigate_to_tray("interior") or
                    self.navigate_to_section("INTERIOR") or
                    self.navigate_to_section("TRIM") or
                    self.navigate_to_section("INSIDE")):
                print("  Could not navigate to interior section")
                return interior_data

            time.sleep(3)

            interior_tray = None
            try:
                interior_tray = self.driver.find_element(By.CSS_SELECTOR, 'div[data-tray-id="interior"]')
                print("  Found interior tray")
            except:
                print("  Could not find interior tray by data-tray-id")
                return interior_data

            fieldsets = interior_tray.find_elements(By.CSS_SELECTOR, 'fieldset[data-testid^="trays-group-tray-group-interior-content-block-group-"]')
            print(f"  Found {len(fieldsets)} interior categories")

            for fieldset in fieldsets:
                try:
                    legend = fieldset.find_element(By.CSS_SELECTOR, 'legend[data-testid="tray-group-legend-test-Id"]')
                    category_name = legend.text.strip()
                    print(f"  Processing category: {category_name}")

                    data_testid = fieldset.get_attribute("data-testid") or ""

                    if "TRIM" in data_testid:
                        trims = self._process_interior_trims(fieldset)
                        interior_data["trims"].extend(trims)
                        print(f"    Found {len(trims)} trim options")

                    elif "SEAT_UPGRADE" in data_testid or "Interior Upgrade" in category_name:
                        upgrades = self._process_interior_upgrades(fieldset)
                        interior_data["interior_upgrade"].extend(upgrades)
                        print(f"    Found {len(upgrades)} interior upgrade options")

                    elif "FINISH_CONTROLS" in data_testid or "Controls" in category_name:
                        controls = self._process_interior_controls(fieldset)
                        interior_data["controls"].extend(controls)
                        print(f"    Found {len(controls)} control options")

                    elif "HEADLINING" in data_testid or "Headlining" in category_name:
                        headlining = self._process_interior_headlining(fieldset)
                        interior_data["headlining"].extend(headlining)
                        print(f"    Found {len(headlining)} headlining options")

                    elif "FINISH_COLOUR" in data_testid or "Finishers" in category_name:
                        finishers = self._process_interior_finishers(fieldset)
                        interior_data["finishers"].extend(finishers)
                        print(f"    Found {len(finishers)} finisher options")

                except Exception as e:
                    print(f"  Error processing fieldset: {e}")
                    continue

            if not any(interior_data.values()):
                print("  No categories found with fieldset method, trying alternative...")
                interior_data = self._alternative_interior_scrape(interior_tray)

            print(f"\n  Interior scraping complete:")
            print(f"    Trims: {len(interior_data['trims'])} options")
            print(f"    Controls: {len(interior_data['controls'])} options")
            print(f"    Headlining: {len(interior_data['headlining'])} options")
            print(f"    Finishers: {len(interior_data['finishers'])} options")
            print(f"    Interior Upgrade: {len(interior_data['interior_upgrade'])} options")

        except Exception as e:
            print(f"Error scraping interior: {e}")
            import traceback
            traceback.print_exc()

        return interior_data

    def _process_interior_trims(self, fieldset) -> List[Dict]:
        """Process interior trim options."""
        trims = []

        try:
            material_categories = fieldset.find_elements(By.CSS_SELECTOR, 'div[data-testid="feature-categories-grid-test-id"]')

            for material_div in material_categories:
                try:
                    material_name = ""
                    try:
                        material_elem = material_div.find_element(By.CSS_SELECTOR, 'h3[data-testid="feature-categories-grid-subtitle-test-id"] span')
                        material_name = material_elem.text.strip()
                    except:
                        pass

                    trim_items = material_div.find_elements(By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]')

                    for item in trim_items:
                        try:
                            trim_info = self._extract_interior_trim_info(item, material_name)
                            if trim_info and trim_info.get("name"):
                                trims.append(trim_info)
                        except Exception as e:
                            continue

                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Error processing trims: {e}")

        return trims

    def _extract_interior_trim_info(self, item, material_category) -> Dict:
        """Extract interior trim information from a trim item."""
        trim_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "interior_image_url": "",
            "category": "trim",
            "material": material_category,
            "description": ""
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    trim_info["name"] = aria_label
            except:
                pass

            if not trim_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    trim_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                desc = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_sub_heading"]')
                trim_info["description"] = desc.text.strip()
            except:
                pass

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    trim_info["swatch_image"] = img_src
            except:
                pass

            try:
                if "feature-block--selected" in feature_block.get_attribute("class") or "":
                    trim_info["is_selected"] = True
            except:
                pass

            if trim_info["swatch_image"] and self.cloudinary_enabled and trim_info["swatch_image"].startswith('http'):
                try:
                    cloudinary_url = self._upload_to_cloudinary(
                        trim_info["swatch_image"],
                        f"swatch_trim_{trim_info['name']}",
                        is_base64=False,
                        category="interior_swatches"
                    )
                    if cloudinary_url:
                        trim_info["swatch_image"] = cloudinary_url
                except:
                    pass

            return trim_info

        except Exception as e:
            print(f"      Error extracting trim info: {e}")
            return {}

    def _process_interior_upgrades(self, fieldset) -> List[Dict]:
        """Process interior upgrade options."""
        upgrades = []

        try:
            upgrade_items = fieldset.find_elements(By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]')

            for item in upgrade_items:
                try:
                    upgrade_info = self._extract_interior_upgrade_info(item)
                    if upgrade_info and upgrade_info.get("name"):
                        upgrades.append(upgrade_info)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Error processing upgrades: {e}")

        return upgrades

    def _process_interior_controls(self, fieldset) -> List[Dict]:
        """Process interior control options."""
        controls = []

        try:
            control_items = fieldset.find_elements(By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]')

            for item in control_items:
                try:
                    control_info = self._extract_interior_control_info(item)
                    if control_info and control_info.get("name"):
                        controls.append(control_info)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Error processing controls: {e}")

        return controls

    def _extract_interior_control_info(self, item) -> Dict:
        """Extract interior control information."""
        control_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "description": "",
            "type": "controls"
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    control_info["name"] = aria_label
            except:
                pass

            if not control_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    control_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    control_info["swatch_image"] = img_src
            except:
                pass

            if control_info["swatch_image"] and self.cloudinary_enabled and control_info["swatch_image"].startswith('http'):
                try:
                    cloudinary_url = self._upload_to_cloudinary(
                        control_info["swatch_image"],
                        f"swatch_control_{control_info['name']}",
                        is_base64=False,
                        category="control_swatches"
                    )
                    if cloudinary_url:
                        control_info["swatch_image"] = cloudinary_url
                except:
                    pass

            return control_info

        except Exception as e:
            return {}

    def _process_interior_headlining(self, fieldset) -> List[Dict]:
        """Process interior headlining options."""
        headlining = []

        try:
            headlining_items = fieldset.find_elements(By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]')

            for item in headlining_items:
                try:
                    headlining_info = self._extract_interior_headlining_info(item)
                    if headlining_info and headlining_info.get("name"):
                        headlining.append(headlining_info)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Error processing headlining: {e}")

        return headlining

    def _extract_interior_headlining_info(self, item) -> Dict:
        """Extract interior headlining information."""
        headlining_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "description": "",
            "type": "headlining"
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    headlining_info["name"] = aria_label
            except:
                pass

            if not headlining_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    headlining_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    headlining_info["swatch_image"] = img_src
            except:
                pass

            if headlining_info["swatch_image"] and self.cloudinary_enabled and headlining_info["swatch_image"].startswith('http'):
                try:
                    cloudinary_url = self._upload_to_cloudinary(
                        headlining_info["swatch_image"],
                        f"swatch_headlining_{headlining_info['name']}",
                        is_base64=False,
                        category="headlining_swatches"
                    )
                    if cloudinary_url:
                        headlining_info["swatch_image"] = cloudinary_url
                except:
                    pass

            return headlining_info

        except Exception as e:
            return {}

    def _process_interior_finishers(self, fieldset) -> List[Dict]:
        """Process interior finisher options."""
        finishers = []

        try:
            finisher_items = fieldset.find_elements(By.CSS_SELECTOR, 'li[data-testid="feature-grid-item-test-id"]')

            for item in finisher_items:
                try:
                    finisher_info = self._extract_interior_finisher_info(item)
                    if finisher_info and finisher_info.get("name"):
                        finishers.append(finisher_info)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Error processing finishers: {e}")

        return finishers

    def _extract_interior_finisher_info(self, item) -> Dict:
        """Extract interior finisher information."""
        finisher_info = {
            "name": "",
            "price": "$0",
            "swatch_image": "",
            "description": "",
            "type": "finisher",
            "material": ""
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    finisher_info["name"] = aria_label
            except:
                pass

            if not finisher_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    finisher_info["name"] = heading.text.strip()
                except:
                    pass

            name_lower = finisher_info["name"].lower()
            if "walnut" in name_lower:
                finisher_info["material"] = "wood"
            elif "grand black" in name_lower:
                finisher_info["material"] = "wood"
            elif "chrome" in name_lower:
                finisher_info["material"] = "metal"
            elif "carbon" in name_lower:
                finisher_info["material"] = "carbon"

            try:
                img = feature_block.find_element(By.CSS_SELECTOR, f'img[data-testid="{testid}_feature_img"]')
                img_src = img.get_attribute("src") or ""
                if img_src:
                    finisher_info["swatch_image"] = img_src
            except:
                pass

            if finisher_info["swatch_image"] and self.cloudinary_enabled and finisher_info["swatch_image"].startswith('http'):
                try:
                    cloudinary_url = self._upload_to_cloudinary(
                        finisher_info["swatch_image"],
                        f"swatch_finisher_{finisher_info['name']}",
                        is_base64=False,
                        category="finisher_swatches"
                    )
                    if cloudinary_url:
                        finisher_info["swatch_image"] = cloudinary_url
                except:
                    pass

            return finisher_info

        except Exception as e:
            return {}

    def _extract_interior_upgrade_info(self, item) -> Optional[Dict]:
        """Extract interior upgrade information."""
        upgrade_info = {
            "name": "",
            "price": "$0",
            "description": "",
            "image_url": "",
            "type": "interior_upgrade",
            "features": []
        }

        try:
            feature_block = item.find_element(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')
            testid = feature_block.get_attribute("data-testid") or ""

            try:
                link = feature_block.find_element(By.CSS_SELECTOR, 'a[data-testid$="_link"]')
                aria_label = link.get_attribute("aria-label") or ""
                if aria_label:
                    upgrade_info["name"] = aria_label
            except:
                pass

            if not upgrade_info["name"]:
                try:
                    heading = feature_block.find_element(By.CSS_SELECTOR, f'span[data-testid="{testid}_feature_heading"]')
                    upgrade_info["name"] = heading.text.strip()
                except:
                    pass

            try:
                price_elem = feature_block.find_element(By.CSS_SELECTOR, f'div[data-testid="{testid}_feature_price"]')
                price_text = price_elem.text.strip()
                if price_text and "$" in price_text:
                    upgrade_info["price"] = price_text
            except:
                pass

            try:
                testid_prefix = testid.split('_')[0]
                input_elem = feature_block.find_element(By.CSS_SELECTOR, f'input[id="{testid_prefix}"]')
                if input_elem.get_attribute("checked") == "true":
                    upgrade_info["is_selected"] = True
            except:
                pass

            return upgrade_info if upgrade_info["name"] else None

        except Exception as e:
            return None

    def _alternative_interior_scrape(self, interior_tray) -> Dict[str, Any]:
        """Alternative method to scrape interior when fieldset approach fails."""
        interior_data = {
            "trims": [],
            "controls": [],
            "headlining": [],
            "finishers": [],
            "interior_upgrade": []
        }

        try:
            feature_blocks = interior_tray.find_elements(By.CSS_SELECTOR, 'div[data-testid$="_feature"]')

            for block in feature_blocks:
                try:
                    parent = block
                    category = "unknown"

                    for _ in range(5):
                        try:
                            parent = parent.find_element(By.XPATH, "..")
                            parent_text = parent.text.lower()

                            if "trim" in parent_text:
                                category = "trims"
                            elif "upgrade" in parent_text:
                                category = "interior_upgrade"
                            elif "control" in parent_text:
                                category = "controls"
                            elif "headlining" in parent_text:
                                category = "headlining"
                            elif "finisher" in parent_text or "finish" in parent_text:
                                category = "finishers"
                            break
                        except:
                            break

                    if category == "trims":
                        trim_info = self._extract_interior_trim_info(block, "")
                        if trim_info and trim_info.get("name"):
                            interior_data["trims"].append(trim_info)
                    elif category == "interior_upgrade":
                        upgrade_info = self._extract_interior_upgrade_info(block)
                        if upgrade_info and upgrade_info.get("name"):
                            interior_data["interior_upgrade"].append(upgrade_info)
                    elif category == "controls":
                        control_info = self._extract_interior_control_info(block)
                        if control_info and control_info.get("name"):
                            interior_data["controls"].append(control_info)
                    elif category == "headlining":
                        headlining_info = self._extract_interior_headlining_info(block)
                        if headlining_info and headlining_info.get("name"):
                            interior_data["headlining"].append(headlining_info)
                    elif category == "finishers":
                        finisher_info = self._extract_interior_finisher_info(block)
                        if finisher_info and finisher_info.get("name"):
                            interior_data["finishers"].append(finisher_info)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"  Error in alternative interior scrape: {e}")

        return interior_data

    # =====================================================================
    # AGGRESSIVE SEARCH FALLBACKS
    # =====================================================================

    def _aggressive_accessory_search(self) -> List[Dict]:
        """Aggressive search for accessories when normal methods fail."""
        accessories = []

        try:
            print("  Starting aggressive accessory search...")

            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.driver.save_screenshot(f"aggressive_search_{timestamp}.png")
            except:
                pass

            all_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div, button, a, li, section, article, [data-testid], [data-id], .option-item, .tray-block"
            )

            print(f"  Scanning {len(all_elements)} elements...")

            accessory_keywords = [
                "step", "liner", "mat", "cover", "protector", "guard", "kit", "pack",
                "towing", "tow", "rack", "box", "bag", "charger", "cable", "cam",
                "dash", "screen", "film", "bar", "rail", "bracket", "mount",
                "holder", "hook", "cleaner", "brush", "organizer", "tray", "bin",
                "net", "strap", "tie", "light", "lamp", "bulb", "led", "deployable",
                "quilted", "cross", "spare", "pre-conditioning", "cruise control",
                "side step", "loadspace", "roof", "floor", "boot", "trunk", "rubber",
                "plastic", "metal", "alloy", "aluminum", "steel", "chrome"
            ]

            found_count = 0
            for element in all_elements[:500]:
                try:
                    if not element.is_displayed():
                        continue

                    text = element.text.strip()
                    if not text or len(text) > 150:
                        continue

                    text_lower = text.lower()

                    is_accessory = any(keyword in text_lower for keyword in accessory_keywords)
                    has_price = '$' in text
                    has_pattern = any(pattern in text_lower for pattern in
                                      [" kit", " pack", " liner", " mat", " cover", " protector"])

                    if is_accessory or has_price or has_pattern:
                        accessory_info = {
                            "name": text.split('\n')[0] if '\n' in text else text,
                            "price": "$0",
                            "description": "",
                            "image_url": ""
                        }

                        if has_price:
                            price_match = re.search(r'(\$\d+[\d,\.]*)', text)
                            if price_match:
                                accessory_info["price"] = price_match.group()

                        try:
                            img = element.find_element(By.TAG_NAME, "img")
                            src = img.get_attribute("src") or img.get_attribute("data-src")
                            if src:
                                accessory_info["image_url"] = src
                        except:
                            pass

                        accessories.append(accessory_info)
                        found_count += 1

                        if found_count <= 10:
                            print(f"    ⚡ Aggressive found: {accessory_info['name']} ({accessory_info['price']})")

                        if found_count >= 30:
                            print(f"    Reached limit of 30 accessories")
                            break

                except:
                    continue

            print(f"  Aggressive search found {len(accessories)} potential accessories")

        except Exception as e:
            print(f"  Error in aggressive accessory search: {e}")

        return accessories

    def _find_exterior_subsection(self, keywords):
        """Find exterior subsection by keywords."""
        items = []

        if isinstance(keywords, str):
            keywords = [keywords]

        try:
            headers = self.driver.find_elements(
                By.CSS_SELECTOR, "h2, h3, h4, h5, h6, [class*='title'], [class*='header']")

            for header in headers:
                try:
                    header_text = header.text.lower()
                    if any(keyword in header_text for keyword in keywords):
                        parent = header
                        for _ in range(3):
                            try:
                                parent = parent.find_element(By.XPATH, "..")
                                option_items = parent.find_elements(
                                    By.CSS_SELECTOR,
                                    ".tray-block, .option-item, [data-id], [data-testid], button, [role='button']"
                                )
                                for item in option_items:
                                    try:
                                        if item.is_displayed():
                                            item_info = self._extract_color_info_improved(item)
                                            if item_info and item_info.get("name"):
                                                items.append(item_info)
                                    except:
                                        continue
                                break
                            except:
                                break
                except:
                    continue

            if not items:
                all_items = self.driver.find_elements(
                    By.CSS_SELECTOR, ".tray-block, .option-item, [data-id], [data-testid]")

                for item in all_items:
                    try:
                        if item.is_displayed():
                            item_text = item.text.lower()
                            if any(keyword in item_text for keyword in keywords):
                                item_info = self._extract_color_info_improved(item)
                                if item_info and item_info.get("name"):
                                    items.append(item_info)
                    except:
                        continue

        except Exception as e:
            print(f"    Error finding exterior subsection: {e}")

        return items

    # =====================================================================
    # CANVAS HELPER
    # =====================================================================

    def _get_canvas_hash(self, canvas_el, quality=0.5) -> Optional[str]:
        """Get a hash of the current canvas content at given quality (JPEG)."""
        try:
            b64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/jpeg', arguments[1]);",
                canvas_el, quality
            )
            if b64 and "base64," in b64:
                return hashlib.md5(b64.encode()).hexdigest()
        except Exception:
            pass
        return None

    # =====================================================================
    # RELOAD + RESELECT COLOR HELPER  ← NEW
    # =====================================================================

    def _reload_and_reselect_color(
        self,
        build_url: str,
        color_name: str,
        color_index: int,
        all_color_infos: List[Dict],
    ) -> bool:
        """
        Reload the build page, navigate back to the exterior/color section,
        then click the swatch identified by `color_name` (matched by aria-label
        or heading text).  Returns True if the swatch was successfully clicked.

        `all_color_infos` is the list of {name, price, category} dicts already
        extracted so we can match the correct swatch after reload.
        """
        print(f"      ♻ Reloading page to get a fresh render for: {color_name}")

        try:
            self.driver.get(build_url)
            time.sleep(10)   # allow full JS boot

            # Navigate back to exterior / color section
            nav_ok = (
                self._navigate_to_tray("exterior") or
                self.navigate_to_section("EXTERIOR") or
                self.navigate_to_section("COLOR") or
                self.navigate_to_section("PAINT")
            )
            if not nav_ok:
                print(f"      ♻ Could not re-navigate to exterior after reload")
                return False

            time.sleep(3)

            # Locate the exterior tray
            try:
                exterior_tray = self.driver.find_element(
                    By.CSS_SELECTOR, "div[data-tray-id='exterior']"
                )
            except:
                print(f"      ♻ Could not find exterior tray after reload")
                return False

            # Locate the paint/colour fieldset
            try:
                color_fieldset = exterior_tray.find_element(
                    By.CSS_SELECTOR,
                    "fieldset[data-testid*='PAINT_COLOUR'], "
                    "fieldset[data-testid*='PAINT'], "
                    "fieldset[data-testid*='COLOR'], "
                    "fieldset[data-testid*='COLOUR']"
                )
            except:
                color_fieldset = exterior_tray

            # Get all swatch list-items
            color_swatches = color_fieldset.find_elements(
                By.CSS_SELECTOR, "li[data-testid='feature-grid-item-test-id']"
            )
            print(f"      ♻ Found {len(color_swatches)} swatches after reload")

            # Find the matching swatch by name
            target_swatch = None
            for swatch in color_swatches:
                try:
                    fb = swatch.find_element(
                        By.CSS_SELECTOR, "div[data-testid$='_feature']"
                    )
                    # Try aria-label on the link
                    swatch_name = ""
                    try:
                        lnk = fb.find_element(By.CSS_SELECTOR, "a[data-testid$='_link']")
                        swatch_name = lnk.get_attribute("aria-label") or ""
                    except:
                        pass
                    if not swatch_name:
                        try:
                            hdg = fb.find_element(By.CSS_SELECTOR, "span[data-testid$='_feature_heading']")
                            swatch_name = hdg.text.strip()
                        except:
                            pass

                    if swatch_name.lower() == color_name.lower():
                        target_swatch = swatch
                        break
                except:
                    continue

            # Fallback: use positional index
            if target_swatch is None and 0 <= color_index < len(color_swatches):
                print(f"      ♻ Name match failed — using index {color_index}")
                target_swatch = color_swatches[color_index]

            if target_swatch is None:
                print(f"      ♻ Could not locate swatch for '{color_name}' after reload")
                return False

            # Scroll + click the swatch
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", target_swatch
            )
            time.sleep(0.5)

            clicked = False
            for click_sel in [
                "a[data-testid$='_link']",
                "div[data-testid$='_feature']",
            ]:
                try:
                    el = target_swatch.find_element(By.CSS_SELECTOR, click_sel)
                    self.driver.execute_script("arguments[0].click();", el)
                    clicked = True
                    print(f"      ♻ Clicked swatch '{color_name}' via {click_sel}")
                    break
                except:
                    continue

            if not clicked:
                self.driver.execute_script("arguments[0].click();", target_swatch)
                clicked = True
                print(f"      ♻ Clicked swatch '{color_name}' via li element")

            return clicked

        except Exception as e:
            print(f"      ♻ Error during reload-reselect for '{color_name}': {e}")
            import traceback
            traceback.print_exc()
            return False

    # =====================================================================
    # MASTER SCRAPER
    # =====================================================================

    def scrape_model_configurations(self, model_info: Dict) -> Dict:
        """Master scraper combining tray-based scraping with aggressive fallback navigation."""
        model_name = model_info.get("model") or model_info.get("model")
        print(f"\n=== SCRAPING MODEL CONFIGURATIONS: {model_name} ===")

        if not model_info.get("build_url"):
            print("No build URL found")
            return {}

        build_url = model_info["build_url"]   # keep for reload logic
        self.driver.get(build_url)

        # ── Clear session state between trims ──────────────────────────────
        try:
            self.driver.delete_all_cookies()
        except Exception as e:
            print(f"  Warning: Could not clear cookies: {e}")

        try:
            self.driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception as e:
            print(f"  Warning: Could not clear storage: {e}")

        time.sleep(10)

        config = {
            "engine": [],
            "exterior": {},
            "wheels": {"wheel": [], "brakes": []},
            "interior": {},
            "packs": [],
            "options": [],
            "accessories": [],
        }

        try:
            print(f"Page title: {self.driver.title}")
            print(f"Current URL: {self.driver.current_url}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f"initial_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source[:50000])
        except Exception:
            pass

        # -------------------------------------------------
        # 1. PROPULSION / ENGINE
        # -------------------------------------------------
        print("\n=== SCRAPING PROPULSION ===")

        propulsion = None

        if self._navigate_to_tray("engine") or \
                self.navigate_to_section("PROPULSION") or \
                self.navigate_to_section("ENGINE") or \
                self.navigate_to_section("POWER") or \
                self.navigate_to_section("MOTOR"):
            propulsion = self.scrape_propulsion_section()

        if not propulsion:
            propulsion = self.scrape_propulsion_section()

        if propulsion:
            config["engine"] = propulsion
            print(f"  Found {len(propulsion)} propulsion options")

        # -------------------------------------------------
        # 2. EXTERIOR
        # -------------------------------------------------
        print("\n=== SCRAPING EXTERIOR ===")

        exterior_data = {
            "colors": [],
            "roof_color": [],
            "roof_type": [],
            "exterior_packs": [],
            "side_steps": [],
            "glass": [],
            "headlights": []
        }

        if self._navigate_to_tray("exterior") or \
                self.navigate_to_section("EXTERIOR") or \
                self.navigate_to_section("COLOR") or \
                self.navigate_to_section("PAINT"):

            print("  Successfully navigated to exterior section")
            time.sleep(3)

            print("  Scraping exterior colors — reload-per-color strategy...")

            try:
                # ── STEP 1: Collect ALL color metadata WITHOUT clicking ─────
                #    We do one clean pass to read names/prices from the DOM,
                #    then reload the page for each color individually.
                exterior_tray = self.driver.find_element(
                    By.CSS_SELECTOR, "div[data-tray-id='exterior']"
                )

                try:
                    color_fieldset = exterior_tray.find_element(
                        By.CSS_SELECTOR,
                        "fieldset[data-testid*='PAINT_COLOUR'], "
                        "fieldset[data-testid*='PAINT'], "
                        "fieldset[data-testid*='COLOR'], "
                        "fieldset[data-testid*='COLOUR']"
                    )
                    print("    Found color fieldset")
                except:
                    color_fieldset = exterior_tray
                    print("    Using full exterior tray as color container")

                color_swatches = color_fieldset.find_elements(
                    By.CSS_SELECTOR, "li[data-testid='feature-grid-item-test-id']"
                )
                print(f"    Found {len(color_swatches)} color swatches")

                # ── Extract metadata from each swatch (no clicking yet) ─────
                all_color_infos: List[Dict] = []
                for swatch_item in color_swatches:
                    info = {"name": "", "price": "$0", "category": "", "image_url": ""}
                    try:
                        fb = swatch_item.find_element(
                            By.CSS_SELECTOR, "div[data-testid$='_feature']"
                        )
                        testid = fb.get_attribute("data-testid") or ""

                        try:
                            lnk = fb.find_element(By.CSS_SELECTOR, "a[data-testid$='_link']")
                            info["name"] = lnk.get_attribute("aria-label") or ""
                        except:
                            pass

                        if not info["name"]:
                            try:
                                hdg = fb.find_element(
                                    By.CSS_SELECTOR, "span[data-testid$='_feature_heading']"
                                )
                                info["name"] = hdg.text.strip()
                            except:
                                pass

                        try:
                            sub = fb.find_element(
                                By.CSS_SELECTOR, "span[data-testid$='_feature_sub_heading']"
                            )
                            info["category"] = sub.text.strip()
                        except:
                            pass

                        try:
                            pe = fb.find_element(
                                By.CSS_SELECTOR, "div[data-testid$='_feature_price']"
                            )
                            pt = pe.text.strip()
                            if pt:
                                info["price"] = pt
                        except:
                            pass

                    except Exception as e:
                        print(f"    Warning: could not read swatch metadata: {e}")

                    if info["name"]:
                        all_color_infos.append(info)
                        print(f"    Metadata collected: {info['name']} ({info['price']})")

                print(f"\n  Starting per-color reload loop ({len(all_color_infos)} colors)...")

                # ── Tunable timing constants ──────────────────────────────────
                # Reduce these if your connection / machine is faster.
                PAGE_LOAD_POLL   = 0.4   # seconds between page-ready polls
                PAGE_LOAD_MAX    = 12    # max seconds to wait for page ready
                NAV_POLL         = 0.3   # seconds between nav-ready polls
                NAV_MAX          = 6     # max seconds to wait for tray to appear
                STABLE_POLL      = 0.4   # seconds between canvas hash polls
                STABLE_MAX       = 12    # max seconds to wait for stable canvas
                REQUIRED_STABLE  = 2     # consecutive identical hashes = done
                FALLBACK_SLEEP   = 4     # sleep when no canvas is found

                # ── STEP 2: For each color — reload page, click swatch,
                #            wait for stable canvas, capture & upload ─────────
                self._last_color_canvas = None   # reset between trims

                for color_idx, color_info in enumerate(all_color_infos):
                    color_name = color_info["name"]
                    print(f"\n  [{color_idx + 1}/{len(all_color_infos)}] Processing: {color_name}")

                    # ── Reload the page fresh for every color ────────────────
                    print(f"    ♻ Reloading page for: {color_name}")
                    self.driver.get(build_url)

                    # Smart wait: poll until document.readyState == 'complete'
                    # AND the nav/tray skeleton is in the DOM — no fixed sleep.
                    page_ready = False
                    for _t in range(int(PAGE_LOAD_MAX / PAGE_LOAD_POLL)):
                        time.sleep(PAGE_LOAD_POLL)
                        try:
                            state = self.driver.execute_script("return document.readyState")
                            if state == "complete":
                                # Also require at least one navigation link present
                                nav_els = self.driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "li[data-navigation-id], nav a, .scrolling-navigation-list-item__cta"
                                )
                                if nav_els:
                                    page_ready = True
                                    print(f"      Page ready in {(_t+1)*PAGE_LOAD_POLL:.1f}s")
                                    break
                        except:
                            pass
                    if not page_ready:
                        print(f"      ⚠ Page ready timeout — continuing anyway")

                    # ── Navigate back to exterior/color section ──────────────
                    nav_ok = (
                        self._navigate_to_tray("exterior") or
                        self.navigate_to_section("EXTERIOR") or
                        self.navigate_to_section("COLOR") or
                        self.navigate_to_section("PAINT")
                    )
                    if not nav_ok:
                        print(f"    ♻ Could not re-navigate to exterior — skipping {color_name}")
                        exterior_data["colors"].append(color_info)
                        continue

                    # Smart wait: poll until the exterior tray + swatches are in DOM
                    tray_ready = False
                    for _t in range(int(NAV_MAX / NAV_POLL)):
                        time.sleep(NAV_POLL)
                        try:
                            tray_el = self.driver.find_element(
                                By.CSS_SELECTOR, "div[data-tray-id='exterior']"
                            )
                            swatches_check = tray_el.find_elements(
                                By.CSS_SELECTOR, "li[data-testid='feature-grid-item-test-id']"
                            )
                            if swatches_check:
                                tray_ready = True
                                print(f"      Tray ready in {(_t+1)*NAV_POLL:.1f}s ({len(swatches_check)} swatches)")
                                break
                        except:
                            pass
                    if not tray_ready:
                        print(f"      ⚠ Tray ready timeout — continuing anyway")

                    # ── Re-locate the fieldset & swatches ───────────────────
                    try:
                        ext_tray = self.driver.find_element(
                            By.CSS_SELECTOR, "div[data-tray-id='exterior']"
                        )
                        try:
                            c_fieldset = ext_tray.find_element(
                                By.CSS_SELECTOR,
                                "fieldset[data-testid*='PAINT_COLOUR'], "
                                "fieldset[data-testid*='PAINT'], "
                                "fieldset[data-testid*='COLOR'], "
                                "fieldset[data-testid*='COLOUR']"
                            )
                        except:
                            c_fieldset = ext_tray

                        fresh_swatches = c_fieldset.find_elements(
                            By.CSS_SELECTOR, "li[data-testid='feature-grid-item-test-id']"
                        )
                    except Exception as e:
                        print(f"    ♻ Could not re-locate swatches after reload: {e}")
                        exterior_data["colors"].append(color_info)
                        continue

                    # ── Find matching swatch by name ─────────────────────────
                    target_swatch = None
                    for sw in fresh_swatches:
                        try:
                            fb2 = sw.find_element(
                                By.CSS_SELECTOR, "div[data-testid$='_feature']"
                            )
                            sw_name = ""
                            try:
                                lnk2 = fb2.find_element(
                                    By.CSS_SELECTOR, "a[data-testid$='_link']"
                                )
                                sw_name = lnk2.get_attribute("aria-label") or ""
                            except:
                                pass
                            if not sw_name:
                                try:
                                    hdg2 = fb2.find_element(
                                        By.CSS_SELECTOR,
                                        "span[data-testid$='_feature_heading']"
                                    )
                                    sw_name = hdg2.text.strip()
                                except:
                                    pass

                            if sw_name.lower() == color_name.lower():
                                target_swatch = sw
                                break
                        except:
                            continue

                    # Positional fallback
                    if target_swatch is None and color_idx < len(fresh_swatches):
                        print(f"    ♻ Name match failed — using positional index {color_idx}")
                        target_swatch = fresh_swatches[color_idx]

                    if target_swatch is None:
                        print(f"    ♻ Cannot find swatch for '{color_name}' — skipping")
                        exterior_data["colors"].append(color_info)
                        continue

                    # ── Click the swatch ─────────────────────────────────────
                    clicked = False
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            target_swatch
                        )

                        for click_sel in [
                            "a[data-testid$='_link']",
                            "div[data-testid$='_feature']",
                        ]:
                            try:
                                el = target_swatch.find_element(By.CSS_SELECTOR, click_sel)
                                self.driver.execute_script("arguments[0].click();", el)
                                clicked = True
                                print(f"    Clicked swatch via {click_sel}")
                                break
                            except:
                                continue

                        if not clicked:
                            self.driver.execute_script("arguments[0].click();", target_swatch)
                            clicked = True
                            print(f"    Clicked swatch via li element")

                    except Exception as e:
                        print(f"    Failed to click swatch for '{color_name}': {e}")

                    if not clicked:
                        print(f"    Skipping canvas capture — could not click")
                        exterior_data["colors"].append(color_info)
                        continue

                    # ─────────────────────────────────────────────────────────
                    # CANVAS WAIT: stabilise-only
                    # Since we reload every time, no "change vs previous color"
                    # detection needed — just wait for the hash to stop moving.
                    # ─────────────────────────────────────────────────────────
                    print(f"    Waiting for canvas to stabilise for '{color_name}'...")

                    canvas_element = None
                    for canvas_sel in [
                        "canvas[class*='cplayer__canvas']",
                        "canvas[class*='contain']",
                        "canvas[class*='vehicle']",
                        "canvas"
                    ]:
                        try:
                            ce = self.driver.find_element(By.CSS_SELECTOR, canvas_sel)
                            if ce.is_displayed():
                                canvas_element = ce
                                break
                        except:
                            continue

                    stable_hash = None
                    if canvas_element:
                        stable_count = 0
                        last_hash    = None
                        waited2      = 0

                        while waited2 < STABLE_MAX:
                            time.sleep(STABLE_POLL)
                            waited2 += STABLE_POLL

                            # Skip while any loading/transition indicator is live
                            try:
                                spinners = self.driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "[class*='loading'], [class*='spinner'], "
                                    "[aria-busy='true'], [class*='transition']"
                                )
                                if any(s.is_displayed() for s in spinners):
                                    stable_count = 0
                                    continue
                            except:
                                pass

                            current_hash = self._get_canvas_hash(canvas_element)
                            if not current_hash:
                                stable_count = 0
                                continue

                            if current_hash == last_hash:
                                stable_count += 1
                                if stable_count >= REQUIRED_STABLE:
                                    stable_hash = current_hash
                                    print(f"      ✓ Canvas stable in {waited2:.1f}s")
                                    break
                            else:
                                stable_count = 0

                            last_hash = current_hash

                        if not stable_hash:
                            print(f"      ⚠ Canvas did not stabilise in {STABLE_MAX}s — capturing best frame")
                    else:
                        print(f"      ⚠ No canvas found — sleeping {FALLBACK_SLEEP}s")
                        time.sleep(FALLBACK_SLEEP)

                    # ─────────────────────────────────────────────────────────
                    # CAPTURE canvas (with retries)
                    # ─────────────────────────────────────────────────────────
                    canvas_data = None
                    max_retries = 3

                    for retry in range(max_retries):
                        try:
                            # Method 1: screenshot_as_png on canvas element
                            for canvas_sel in [
                                "canvas[class*='cplayer__canvas']",
                                "canvas[class*='contain']",
                                "canvas[class*='vehicle']",
                                "canvas",
                            ]:
                                try:
                                    canvas_el = self.driver.find_element(
                                        By.CSS_SELECTOR, canvas_sel
                                    )
                                    if canvas_el.is_displayed():
                                        w = canvas_el.size.get("width", 0)
                                        h = canvas_el.size.get("height", 0)
                                        if w > 100 and h > 100:
                                            canvas_data = canvas_el.screenshot_as_png
                                            print(f"      Canvas captured via screenshot_as_png ({w}x{h})")
                                            break
                                except:
                                    continue

                            if canvas_data:
                                break

                            # Method 2: toDataURL via JS
                            for canvas_sel in [
                                "canvas[class*='cplayer__canvas']",
                                "canvas[class*='contain']",
                                "canvas[class*='vehicle']",
                                "canvas",
                            ]:
                                try:
                                    canvas_el = self.driver.find_element(
                                        By.CSS_SELECTOR, canvas_sel
                                    )
                                    b64 = self.driver.execute_script(
                                        "return arguments[0].toDataURL('image/png');",
                                        canvas_el
                                    )
                                    if b64 and "base64," in b64:
                                        canvas_data = base64.b64decode(b64.split(",")[1])
                                        print(f"      Canvas captured via toDataURL")
                                        break
                                except:
                                    continue

                            if canvas_data:
                                break

                            # Method 3: full page screenshot (last resort)
                            if retry == max_retries - 1:
                                try:
                                    canvas_data = base64.b64decode(
                                        self.driver.get_screenshot_as_base64()
                                    )
                                    print(f"      ⚠ Fell back to full page screenshot")
                                    break
                                except:
                                    pass

                            if retry < max_retries - 1:
                                print(f"      Retry {retry + 1}/{max_retries} — waiting 1s...")
                                time.sleep(1)

                        except Exception as e:
                            print(f"      Error on retry {retry + 1}: {e}")
                            if retry < max_retries - 1:
                                time.sleep(1)

                    # ─────────────────────────────────────────────────────────
                    # CROP: 2 cm from top, left, right (not bottom) @ 96 DPI
                    # ─────────────────────────────────────────────────────────
                    if canvas_data:
                        try:
                            img = Image.open(io.BytesIO(canvas_data))
                            img_w, img_h = img.size

                            crop_px = 76  # 2 cm at 96 DPI

                            left   = crop_px
                            top    = crop_px
                            right  = img_w - crop_px
                            bottom = img_h  # no crop on bottom

                            if right > left and bottom > top:
                                img = img.crop((left, top, right, bottom))
                                buf = io.BytesIO()
                                img.save(buf, format="PNG")
                                canvas_data = buf.getvalue()
                                print(f"      Cropped canvas to ({left},{top},{right},{bottom})")
                            else:
                                print(f"      ⚠ Crop dimensions invalid, skipping crop")
                        except Exception as e:
                            print(f"      ⚠ Canvas crop failed: {e}")

                    # (no cross-color hash comparison needed — each iteration reloads)

                    # ─────────────────────────────────────────────────────────
                    # UPLOAD to Cloudinary
                    # ─────────────────────────────────────────────────────────
                    if canvas_data and self.cloudinary_enabled:
                        try:
                            safe_name = "".join(
                                c for c in color_name
                                if c.isalnum() or c in ("-", "_", " ")
                            ).replace(" ", "_")
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            public_id = (
                                f"{self.cloudinary_folder}/exterior_colors/"
                                f"{safe_name}_{ts}"
                            )
                            upload_result = cloudinary.uploader.upload(
                                canvas_data,
                                public_id=public_id,
                                resource_type="image",
                                overwrite=True,
                            )
                            url = upload_result.get("secure_url", "")
                            if url:
                                color_info["image_url"] = url
                                print(f"      ✓ Uploaded to Cloudinary: {url}")
                            else:
                                print(f"      ✗ Cloudinary returned no URL")
                        except Exception as e:
                            print(f"      ✗ Cloudinary upload error: {e}")
                    elif canvas_data:
                        color_info["image_url"] = (
                            "data:image/png;base64,"
                            + base64.b64encode(canvas_data).decode()
                        )

                    # ── Sort into body colour vs roof colour ─────────────────
                    name_lower = color_name.lower()
                    if any(k in name_lower for k in
                           ['roof', 'contrast', 'contrasting', 'dual', 'two-tone']):
                        exterior_data["roof_color"].append(color_info)
                    else:
                        exterior_data["colors"].append(color_info)

                    print(f"      ✓ Done: {color_name}")

                # end per-color loop
                print(f"\n  Color loop complete. "
                      f"Body: {len(exterior_data['colors'])}, "
                      f"Roof: {len(exterior_data['roof_color'])}")

            except Exception as e:
                print(f"  Error in color swatch loop: {e}")
                import traceback
                traceback.print_exc()

            # -------------------------------------------------
            # After the color loop the page has been reloaded to
            # the last color's state.  Re-navigate to exterior so
            # the remaining tray scraping works correctly.
            # -------------------------------------------------
            nav_ok = (
                self._navigate_to_tray("exterior") or
                self.navigate_to_section("EXTERIOR") or
                self.navigate_to_section("COLOR") or
                self.navigate_to_section("PAINT")
            )
            if nav_ok:
                time.sleep(3)

            # ── Scrape exterior_packs, side_steps, glass, headlights, roof_type
            #    using the dedicated method that matches the exact HTML structure.
            print("  Scraping exterior sub-sections (packs, side steps, glass, etc.)...")
            ext_tray_data = self._scrape_exterior_tray()

            for bucket_key in ("exterior_packs", "side_steps", "roof_type", "glass", "headlights"):
                if ext_tray_data.get(bucket_key):
                    exterior_data[bucket_key] = ext_tray_data[bucket_key]
                    print(f"    ✓ {bucket_key}: {len(ext_tray_data[bucket_key])} item(s)")

            # ── Fallbacks for sections not yet populated ─────────────────────
            if not exterior_data["colors"]:
                print("  ⚠ No colors captured, using legacy fallback...")
                colors = self.scrape_exterior_colors()
                if colors:
                    exterior_data["colors"] = colors

            if not exterior_data["roof_color"]:
                roof_colors = self.scrape_roof_colors()
                if roof_colors:
                    exterior_data["roof_color"] = roof_colors

            if not exterior_data["glass"]:
                glass_options = self._find_exterior_subsection("glass")
                if glass_options:
                    exterior_data["glass"] = glass_options

            if not exterior_data["headlights"]:
                headlight_options = self._find_exterior_subsection(["headlight", "headlamp", "light"])
                if headlight_options:
                    exterior_data["headlights"] = headlight_options

            if not exterior_data["exterior_packs"]:
                pack_options = self._find_exterior_subsection("pack")
                if pack_options:
                    exterior_data["exterior_packs"] = pack_options

        else:
            print("  Could not navigate to exterior section, using fallback...")
            colors = self.scrape_exterior_colors()
            if colors:
                exterior_data["colors"] = colors
            roof_colors = self.scrape_roof_colors()
            if roof_colors:
                exterior_data["roof_color"] = roof_colors

        exterior_data = {k: v for k, v in exterior_data.items() if v}
        config["exterior"] = exterior_data

        # -------------------------------------------------
        # 3. WHEELS
        # -------------------------------------------------
        print("\n=== SCRAPING WHEELS ===")

        wheels_data = {"wheel": [], "brakes": []}
        wheel_found = False

        if self._navigate_to_tray("wheel_configuration"):
            print("  Found wheel_configuration tray")
            wheel_found = True
            time.sleep(3)
        elif self._navigate_to_tray("wheels"):
            print("  Found wheels tray")
            wheel_found = True
            time.sleep(3)
        elif self._navigate_to_tray("wheel"):
            print("  Found wheel tray")
            wheel_found = True
            time.sleep(3)
        elif self.navigate_to_section("WHEELS"):
            print("  Navigated to WHEELS section")
            wheel_found = True
            time.sleep(3)
        elif self.navigate_to_section("WHEEL"):
            print("  Navigated to WHEEL section")
            wheel_found = True
            time.sleep(3)
        else:
            for wheel_keyword in ["RIM", "RIMS", "TYRE", "TYRES", "TIRE", "TIRES"]:
                if self.navigate_to_section(wheel_keyword):
                    print(f"  Navigated to {wheel_keyword} section")
                    wheel_found = True
                    time.sleep(3)
                    break

        if wheel_found:
            print("  Wheel section found, starting scraping...")
            wheels_data = self.scrape_wheels_section()

            if not wheels_data.get("wheel") and not wheels_data.get("brakes"):
                print("  No wheels found with first method, trying tray scrape...")
                wheel_tray_data = (self._scrape_tray("wheels") or
                                   self._scrape_tray("wheel_configuration") or
                                   self._scrape_tray("wheel"))
                if wheel_tray_data:
                    for category, items in wheel_tray_data.items():
                        for item in items:
                            item_name_lower = item.get("name", "").lower()
                            if any(keyword in item_name_lower for keyword in ["wheel", "rim", "tire", "tyre", "inch", '"', "style"]):
                                wheels_data["wheel"].append(item)
                            elif "brake" in item_name_lower:
                                wheels_data["brakes"].append(item)
                    if wheels_data["wheel"] or wheels_data["brakes"]:
                        print(f"  Found {len(wheels_data['wheel'])} wheels and {len(wheels_data['brakes'])} brakes from tray data")
        else:
            print("  Could not navigate to wheels section, trying direct scraping...")
            wheels_data = self.scrape_wheels_section()

            if not wheels_data.get("wheel") and not wheels_data.get("brakes"):
                print("  Trying to find wheels in current page...")
                try:
                    all_sections = self.driver.find_elements(
                        By.CSS_SELECTOR, "section, div[class*='section'], div[class*='tray']")
                    for section in all_sections:
                        try:
                            section_text = section.text.lower()
                            if 'wheel' in section_text or 'rim' in section_text or 'tire' in section_text or 'tyre' in section_text:
                                print("  Found potential wheel section in page")
                                wheel_items = section.find_elements(
                                    By.CSS_SELECTOR,
                                    ".tray-block, .option-item, [data-id], [data-testid], button, [role='button']"
                                )
                                for item in wheel_items[:20]:
                                    try:
                                        text = item.text.strip()
                                        if text and any(keyword in text.lower() for keyword in ["wheel", "rim", "inch", '"', "style"]):
                                            wheel_info = self._extract_wheel_info(item, "")
                                            if wheel_info and wheel_info.get("name"):
                                                wheels_data["wheel"].append(wheel_info)
                                    except:
                                        continue
                                if wheels_data["wheel"]:
                                    print(f"  Found {len(wheels_data['wheel'])} wheels from page section")
                                    break
                        except:
                            continue
                except Exception as e:
                    print(f"  Error in alternative wheel search: {e}")

        if wheels_data["wheel"] or wheels_data["brakes"]:
            config["wheels"] = wheels_data
            print(f"  ✓ Total wheels: {len(wheels_data['wheel'])}")
            print(f"  ✓ Total brake options: {len(wheels_data['brakes'])}")
        else:
            print("  ⚠ No wheels or brakes found — section will be omitted from JSON")

        # -------------------------------------------------
        # 4. INTERIOR
        # -------------------------------------------------
        print("\n=== SCRAPING INTERIOR ===")

        interior_data = self.scrape_interior_section()
        if interior_data:
            config["interior"] = interior_data
            print(f"  Interior data collected successfully")

        # -------------------------------------------------
        # 5. PACKS
        # -------------------------------------------------
        print("\n=== SCRAPING PACKS ===")

        if self._navigate_to_tray("packs"):
            packs_data = self._scrape_tray("packs")
            if packs_data:
                packs_list = []
                for category, items in packs_data.items():
                    for item in items:
                        item["category"] = category
                        packs_list.append(item)
                config["packs"] = packs_list
                print(f"  Found {len(packs_list)} packs")

        # -------------------------------------------------
        # 6. OPTIONS
        # -------------------------------------------------
        print("\n=== SCRAPING OPTIONS ===")

        option_section_names = [
            "OPTIONS", "FEATURES", "PACKAGES",
            "TECHNOLOGY", "SAFETY", "COMFORT", "CONVENIENCE"
        ]

        options = None

        if self._navigate_to_tray("options_configuration"):
            options = self.scrape_options_section()
            if options:
                print(f"  Found {len(options)} options from overlay scraper")

        if not options:
            for section in option_section_names:
                if self.navigate_to_section(section):
                    time.sleep(3)
                    options = self.scrape_options_section()
                    if options:
                        break

        if not options:
            options = self._emergency_option_search()

        if options:
            config["options"] = options
            print(f"  Found {len(options)} options")

        # -------------------------------------------------
        # 7. ACCESSORIES
        # -------------------------------------------------
        print("\n=== SCRAPING ACCESSORIES ===")

        accessory_sections = [
            "ACCESSORIES", "ACCESSORY", "ADD-ONS", "ADDONS",
            "OPTIONAL", "EXTRAS", "SUGGESTED"
        ]

        accessories = None

        if self._navigate_to_tray("accessories"):
            accessories = self.scrape_accessories_section()

        if not accessories:
            for section in accessory_sections:
                if self.navigate_to_section(section):
                    time.sleep(3)
                    accessories = self.scrape_accessories_section()
                    if accessories:
                        break

        if not accessories:
            accessories = self.scrape_accessories_section()

        if not accessories:
            accessories = self._aggressive_accessory_search()

        if accessories:
            config["accessories"] = accessories
            print(f"  Found {len(accessories)} accessories")

        # -------------------------------------------------
        # PRUNE EMPTY SECTIONS & SUBSECTIONS
        # -------------------------------------------------
        wheels = config.get("wheels", {})
        wheels = {k: v for k, v in wheels.items() if v}
        if wheels:
            config["wheels"] = wheels
        else:
            config.pop("wheels", None)

        config["exterior"] = {k: v for k, v in config.get("exterior", {}).items() if v}
        if not config["exterior"]:
            config.pop("exterior", None)

        config["interior"] = {k: v for k, v in config.get("interior", {}).items() if v}
        if not config["interior"]:
            config.pop("interior", None)

        for section in ["engine", "packs", "options", "accessories"]:
            if not config.get(section):
                config.pop(section, None)

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------
        print("\n=== SCRAPING COMPLETE ===")

        total_exterior = sum(
            len(config.get('exterior', {}).get(key, []))
            for key in ['colors', 'roof_color', 'exterior_packs', 'side_steps', 'glass', 'roof_type', 'headlights']
        )

        total_interior = sum(
            len(config.get('interior', {}).get(key, []))
            for key in ['trims', 'controls', 'headlining', 'finishers', 'interior_upgrade']
        )

        wheels_count = len(config.get("wheels", {}).get("wheel", []))
        brakes_count = len(config.get("wheels", {}).get("brakes", []))

        print(
            f"Engine={len(config.get('engine', []))} | "
            f"Exterior={total_exterior} items | "
            f"Wheels={wheels_count} | "
            f"Brakes={brakes_count} | "
            f"Interior={total_interior} | "
            f"Packs={len(config.get('packs', []))} | "
            f"Options={len(config.get('options', []))} | "
            f"Accessories={len(config.get('accessories', []))}"
        )

        saved_sections = list(config.keys())
        print(f"\n  Sections saved to JSON ({len(saved_sections)}): {', '.join(saved_sections)}")

        if "exterior" in config:
            print("\n  Exterior Breakdown:")
            for category, items in config['exterior'].items():
                print(f"    {category}: {len(items)} items")

        if "interior" in config:
            print("\n  Interior Breakdown:")
            for category, items in config['interior'].items():
                print(f"    {category}: {len(items)} items")

        return config

    # =====================================================================
    # MAIN SCRAPE_ALL - PER-TRIM SAVING
    # =====================================================================

    def scrape_all(self, url: str, car_name: str, start_from_model: int = 0) -> Dict:
        """Scrape all models and their configurations."""
        print(f"Starting scrape for {car_name}...")

        if isinstance(url, dict) and "trims" in url:
            models = self.get_model_info_from_trim_list(car_name, url["trims"])
        else:
            models = self.get_model_info(url, car_name)

        if not models:
            print("No models found!")
            return {}

        print(f"  Total trims to scrape: {len(models)}")
        for i, m in enumerate(models):
            print(f"    [{i+1}] {m['model']}")

        all_data = {
            "car_name": car_name,
            "total_trims": len(models),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "models": [],
        }

        car_base = car_name.replace(' ', '_')

        for i in range(start_from_model, len(models)):
            model = models[i]
            trim_name = model['model']
            trim_base = trim_name.replace(' ', '_').replace('/', '-')

            print(f"\n{'='*60}")
            print(f"  Scraping trim {i + 1}/{len(models)}: {trim_name}")
            print(f"{'='*60}")

            # Close any extra tabs
            try:
                while len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                print(f"  Browser tabs cleaned up — {len(self.driver.window_handles)} tab(s) active")
            except Exception as e:
                print(f"  Warning: Tab cleanup failed: {e}")

            try:
                configurations = self.scrape_model_configurations(model)
                model["configurations"] = configurations
                model["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                model["status"] = "success"

                trim_filename = f"{car_base}__trim_{i+1}__{trim_base}.json"
                with open(trim_filename, "w", encoding="utf-8") as f:
                    json.dump(model, f, indent=2, ensure_ascii=False)
                print(f"\n  ✅ Trim saved  →  {trim_filename}")

                all_data["models"].append(model)
                combined_filename = f"{car_base}_ALL_TRIMS.json"
                with open(combined_filename, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                print(f"  ✅ Combined file updated  →  {combined_filename}")
                print(f"  Progress: {i + 1 - start_from_model}/{len(models) - start_from_model} trims done")

            except Exception as e:
                print(f"\n  ✗ Error scraping trim '{trim_name}': {e}")
                import traceback
                traceback.print_exc()

                failed_model = dict(model)
                failed_model["configurations"] = {}
                failed_model["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                failed_model["status"] = "failed"
                failed_model["error"] = str(e)

                fail_filename = f"{car_base}__trim_{i+1}__{trim_base}__FAILED.json"
                try:
                    with open(fail_filename, "w", encoding="utf-8") as f:
                        json.dump(failed_model, f, indent=2, ensure_ascii=False)
                    print(f"  ⚠  Failure record saved  →  {fail_filename}")
                except Exception:
                    pass

                all_data["models"].append(failed_model)
                combined_filename = f"{car_base}_ALL_TRIMS.json"
                try:
                    with open(combined_filename, "w", encoding="utf-8") as f:
                        json.dump(all_data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

                # Attempt browser restart if crashed
                try:
                    self.driver.current_url
                except Exception:
                    print("  ⚠ Browser appears to have crashed — attempting restart...")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    try:
                        from selenium.webdriver.chrome.options import Options
                        chrome_options = Options()
                        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        chrome_options.add_experimental_option('useAutomationExtension', False)
                        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                        chrome_options.add_argument("--start-maximized")
                        chrome_options.add_argument("--disable-infobars")
                        chrome_options.add_argument("--disable-notifications")
                        self.driver = webdriver.Chrome(options=chrome_options)
                        self.wait = WebDriverWait(self.driver, 30)
                        self.driver.execute_script(
                            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        print("  ✅ Browser restarted successfully")
                    except Exception as restart_err:
                        print(f"  ✗ Browser restart failed: {restart_err}")
                        print("  Stopping scraper — cannot continue without browser")
                        break

                continue

        success_count = sum(1 for m in all_data["models"] if m.get("status") == "success")
        fail_count = len(all_data["models"]) - success_count
        print(f"\n{'='*60}")
        print(f"  Scraping complete for: {car_name}")
        print(f"  ✅ Successful trims : {success_count}")
        print(f"  ❌ Failed trims     : {fail_count}")
        print(f"  Combined file       : {car_base}_ALL_TRIMS.json")
        print(f"{'='*60}\n")

        return all_data


# =====================================================================
# URL CONFIGURATION & ENTRY POINTS
# =====================================================================

def get_landrover_urls():
    """Return the updated URL structure for Land Rover vehicles."""
    return {
        "Range Rover": {
            "trims": [
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-std/ipr/personalise/bodystyle/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover (Made in India)",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-std-kd/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover SE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-std-se/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover HSE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-std-hse/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover Autobiography",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-ab/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover SV",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-sv/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Standard Wheelbase",
                #     "model_name": "Range Rover SV Black",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-svb/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-std/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover SE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-std-se/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover HSE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-std-hse/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover HSE (Made in India)",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-std-hse-kd/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover Autobiography",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-ab_a-lwb/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover Autobiography (Made in India)",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-ab-kd_a-lwb/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover SV",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-sv/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover SV 4 Seat",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-sv4/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover SV Black",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-svb/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase",
                #     "model_name": "Range Rover SV Black 4 seat",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb_a-svb4/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase Seven Seats",
                #     "model_name": "Range Rover",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb-7_a-std/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase Seven Seats",
                #     "model_name": "Range Rover SE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb-7_a-std-se/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase Seven Seats",
                #     "model_name": "Range Rover HSE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-lwb-7_a-std-hse/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "body_style": "Long Wheelbase Seven Seats",
                #     "model_name": "Range Rover Autobiography",
                #     "link": "https://www.rangerover.com/lr/en_xi/l460_k26/4cj1x/a-ab_a-lwb-7/ipr/personalise/model/?_gl=1*17tuq9r*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3Njk3NDAkajU3JGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # }
            ]
        },
        "Range Rover Sport": {
            "trims": [
                # {
                #     "model_name": "Range Rover Sport",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-std/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SmtGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport S",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-std-s/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport SE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-std-se/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport Dynamic SE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-dyn-se/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport Dynamic HSE",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-dyn-hse/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport Autobiography",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-ab/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport SV",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-sv-0/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                # {
                #     "model_name": "Range Rover Sport SV Black",
                #     "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-sv-2/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                # },
                {
                    "model_name": "Range Rover Sport SV Carbon",
                    "link": "https://www.rangerover.com/lr/en_xi/l461_k26/4cj1s/a-sv-3/ipr/personalise/model/?_gl=1*w1lnib*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3Njk2NTkkbzQkZzEkdDE3Njc3NzAyMjMkajYwJGwwJGg4MDU0MTY1Mzk.*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
                },
            ]
        },
        # "Range Rover Velar": {
        #     "trims": [
        #         {
        #             "model_name": "Range Rover Velar S",
        #             "link": "https://www.rangerover.com/lr/en_xi/l560_k265/4cj1j/ipr/personalise/model/?_gl=1*163qdkg*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzIyNjYkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #         {
        #             "model_name": "Range Rover Velar Dynamic SE",
        #             "link": "https://www.rangerover.com/lr/en_xi/l560_k265/4cj1j/a-vdyn/ipr/personalise/model/?_gl=1*163qdkg*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzIyNjYkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #         {
        #             "model_name": "Range Rover Velar Autobiography",
        #             "link": "https://www.rangerover.com/lr/en_xi/l560_k265/4cj1j/a-sa/ipr/personalise/model/?_gl=1*163qdkg*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzIyNjYkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #     ]
        # },
        # "Range Rover Evoque": {
        #     "trims": [
        #         {
        #             "model_name": "Range Rover Evoque S",
        #             "link": "https://www.rangerover.com/lr/en_xi/l551_k265/4cj1k/ipr/personalise/model/?_gl=1*piwge3*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzMwODMkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #         {
        #             "model_name": "Range Rover Evoque Dynamic SE",
        #             "link": "https://www.rangerover.com/lr/en_xi/l551_k265/4cj1k/a-rdyn/ipr/personalise/model/?_gl=1*piwge3*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzMwODMkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #         {
        #             "model_name": "Range Rover Evoque Autobiography",
        #             "link": "https://www.rangerover.com/lr/en_xi/l551_k265/4cj1k/a-autobiography/ipr/personalise/model/?_gl=1*piwge3*_gcl_au*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*FPAU*NTg3MTA1Mzk4LjE3Njc2ODIxODU.*_ga*MjIzMzMyODgwLjE3Njc2ODIxODU.*_ga_64JSG6TR69*czE3Njc3NzIyMDQkbzUkZzEkdDE3Njc3NzMwODMkajYwJGwwJGgyMDMwNjg1MjUy*_fplc*R0xhRGJub2drJTJCWHRaYlYwc0V0RnlTY0VRZnkxRVZFY1AlMkZjRmo0YzdvJTJCRWQ2YllqRmFkdk11Z2NWVnJkTmdwbHZDUXd2ZEpQVUt2Q2ZNSVo0dyUyRiUyRmpncmx1SktGN2N2NU4zYnNvJTJGamNSZVljS3ZVTyUyRiUyRlZ6cWZhJTJGS3JBN2lBJTNEJTNE"
        #         },
        #     ]
        # },
        # "Defender OCTA": {
        #     "trims": [
        #         {
        #             "body_style": "Defender OCTA",
        #             "model_name": "Defender OCTA",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-p635-110_a-sv-110_a-sv1/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender OCTA",
        #             "model_name": "Defender OCTA Black",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-p635-110_a-sv-110_a-sv3/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 90",
        #             "model_name": "Defender S",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-90_a-d200-i6_a-l663-s/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 90",
        #             "model_name": "Defender X-Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-90_a-d200-i6_a-xdyn-se/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 90",
        #             "model_name": "Defender X-Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-90_a-d250_a-xdyn-hse/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 90",
        #             "model_name": "Defender X",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-90_a-d350_a-x/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 90",
        #             "model_name": "Defender V8",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-90_a-p525_a-sv8/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender S",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-d200-i6-110_a-l663-s/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender X-Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-d200-i6-110_a-xdyn-se/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender X-Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-d250-110_a-xdyn-hse/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender X",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-d350-110_a-x/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender Trophy Edition in Keswick Green",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-d350-110_a-le17/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender V8",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-p525-110_a-sv8/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 110",
        #             "model_name": "Defender 525 Ultimate Edition",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-110_a-le19_a-p525-110/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender S",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-d250-130_a-l663-s/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender X-Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-d250-130_a-xdyn-se/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender X-Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-d250-130_a-xdyn-hse/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender X",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-d350-130_a-x/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender V8",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-p500-130_a-sv8/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender 130",
        #             "model_name": "Defender Outbound",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-130_a-d350-130_a-le13/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 90",
        #             "model_name": "Defender Hard Top S",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-com-s_a-d200-i6_a-ht-90/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 90",
        #             "model_name": "Defender Hard Top X-Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d250_a-ht-90_a-xdcom-se/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 90",
        #             "model_name": "Defender Hard Top X-Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d250_a-ht-90_a-xdcom-hse/ipr/personalise/bodystyle/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 90",
        #             "model_name": "Defender Hard Top X",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d350_a-ht-90_a-xcom/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 110",
        #             "model_name": "Defender Hard Top S",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-com-s_a-d250-110_a-ht-110/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 110",
        #             "model_name": "Defender Hard Top X-Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d250-110_a-ht-110_a-xdcom-se/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 110",
        #             "model_name": "Defender Hard Top X-Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d250-110_a-ht-110_a-xdcom-hse/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Defender Hard Top 110",
        #             "model_name": "Defender Hard Top X",
        #             "link": "https://www.landrover.com/lr/en_xi/l663_k26/4cj1q/a-d350-110_a-ht-110_a-xcom/ipr/personalise/model/"
        #         }
        #     ]
        # },
        # "Discovery": {
        #     "trims": [
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery S",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-d250_a-std_a-std-wb_d/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery Dynamic SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-d250_a-std-wb_a-vdyn_d/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery Gemini",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-d250_a-le10_a-std-wb_d/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery Dynamic HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-d250_a-std-wb_a-vdyn-hse_d/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery Metropolitian Edition",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-le7_a-p360_a-std-wb_p/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery",
        #             "model_name": "Discovery Tempest",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cm76/a-le9_a-p360_a-std-wb_p/a-rec-1_n-041cr_n-1au/ipr/personalise/model/"
        #         },
        #         {
        #             "body_style": "Discovery Commercial",
        #             "model_name": "Discovery Commercial SE",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cq9x/a-com-wb/ipr/personalise/bodystyle/"
        #         },
        #         {
        #             "body_style": "Discovery Commercial",
        #             "model_name": "Discovery Commercial Dynamin HSE",
        #             "link": "https://www.landrover.com/lr/en_xi/l462_k26/4cq9x/a-com-wb_a-rdyn-com/ipr/personalise/bodystyle/"
        #         }
        #     ]
        # },
        # "Discovery Sport": {
        #     "trims": [
        #         {
        #             "model_name": "Discovery Sport Dynamic S",
        #             "link": "https://www.landrover.com/lr/en_xi/l550_k265/4cm9w/ipr/personalise/"
        #         },
        #         {
        #             "model_name": "Discovery Sport Landmark",
        #             "link": "https://www.landrover.com/lr/en_xi/l550_k265/4cm9w/a-rdyn-se/ipr/personalise/model/"
        #         },
        #         {
        #             "model_name": "Discovery Sport Metropolitan",
        #             "link": "https://www.landrover.com/lr/en_xi/l550_k265/4cm9w/a-rdyn-hse/ipr/personalise/model/"
        #         },
        #     ]
        # }
    }


def main():
    """Main function to run the scraper for ALL vehicles."""
    all_urls = get_landrover_urls()

    cloudinary_config = {
        'cloud_name': "dsmkxcczo",
        'api_key': "395956489484953",
        'api_secret': "rMIXWeYnZI7-ir834KFjEpf0dWI",
        'folder': 'landrover'
    }

    scraper = LandRoverScraper(
        headless=False,
        cloudinary_config=cloudinary_config
    )

    all_results = {}

    try:
        total_vehicles = len(all_urls)
        print(f"\n{'='*60}")
        print(f"Starting to scrape {total_vehicles} vehicles")
        print(f"{'='*60}\n")

        for vehicle_index, (vehicle_name, vehicle_data) in enumerate(all_urls.items(), 1):
            print(f"\n{'='*60}")
            print(f"[{vehicle_index}/{total_vehicles}] Processing: {vehicle_name}")
            print(f"Total trims/models: {len(vehicle_data['trims'])}")
            print(f"{'='*60}\n")

            try:
                data = scraper.scrape_all(vehicle_data, vehicle_name)

                if data:
                    all_results[vehicle_name] = {
                        "data": data,
                        "models_count": len(data.get("models", [])),
                        "status": "success"
                    }
                else:
                    print(f"✗ No data scraped for {vehicle_name}")
                    all_results[vehicle_name] = {
                        "status": "failed",
                        "error": "No data returned"
                    }

            except Exception as e:
                print(f"✗ Error scraping {vehicle_name}: {e}")
                all_results[vehicle_name] = {
                    "status": "error",
                    "error": str(e)
                }
                import traceback
                traceback.print_exc()
                continue

        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE - GENERATING SUMMARY")
        print(f"{'='*60}\n")

        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_vehicles": total_vehicles,
            "successful": sum(1 for v in all_results.values() if v.get("status") == "success"),
            "failed": sum(1 for v in all_results.values() if v.get("status") != "success"),
            "vehicles": {}
        }

        for vehicle_name, result in all_results.items():
            if result.get("status") == "success":
                summary["vehicles"][vehicle_name] = {
                    "status": "success",
                    "models_scraped": result.get("models_count", 0),
                }
            else:
                summary["vehicles"][vehicle_name] = {
                    "status": result.get("status"),
                    "error": result.get("error")
                }

        summary_filename = "ALL_VEHICLES_SUMMARY.json"
        with open(summary_filename, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print("FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total Vehicles: {summary['total_vehicles']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"\nDetailed summary saved to: {summary_filename}")
        print(f"{'='*60}\n")

        for vehicle_name, info in summary["vehicles"].items():
            status_symbol = "✓" if info["status"] == "success" else "✗"
            if info["status"] == "success":
                print(f"{status_symbol} {vehicle_name}: {info['models_scraped']} models")
            else:
                print(f"{status_symbol} {vehicle_name}: {info['status']} - {info.get('error', 'Unknown error')}")

        print()

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"CRITICAL ERROR: {e}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("\nScraper closed. Done!")


if __name__ == "__main__":
    main()