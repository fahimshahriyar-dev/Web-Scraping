import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# Set to True if you don't want to see the browser
HEADLESS = False

def get_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--log-level=3")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(180) 
    return driver

def safe_click(driver, elem):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", elem)
        return True
    except:
        try:
            elem.click()
            return True
        except:
            return False

def wait_for_loading(driver):
    """Waits for spinners to disappear"""
    try:
        WebDriverWait(driver, 4).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loader-wrapper, .loading, .spinner"))
        )
        time.sleep(1.0)
    except: pass

def extract_price(card_or_driver):
    selectors = [
        ".sdp-vehicle-selector-card-stats__value",
        ".sdp-configurator-trim-selector-card-enhanced__container-vehicle-details-stat-value",
        ".summary-footer-price",
        ".vehicle-price",
        ".stat-value",
        ".gcss-typography-utility-heading-6" 
    ]
    
    for sel in selectors:
        try:
            elements = card_or_driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                txt = el.text.strip()
                if "$" in txt:
                    clean_val = re.sub(r'[^\d]', '', txt)
                    if clean_val and int(clean_val) > 15000: 
                        return txt
        except:
            continue
    return "N/A"

def extract_image(card):
    try:
        imgs = card.find_elements(By.TAG_NAME, "img")
        for img in imgs:
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if src and "mediaserver" in src:
                if "width=" in src: 
                    src = re.sub(r'width=\d+', 'width=1400', src)
                return src
    except: pass
    return "N/A"

def get_header_text(driver):
    selectors = [
        ".bmo-top-navigation__vehicle-display-value span",
        ".sdp-configurator-trim-enhanced-view__container-headline",
        "h1"
    ]
    for sel in selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, sel)
            txt = elem.text.strip()
            if txt and "RAM" in txt.upper():
                return txt
        except: continue
    return None

def clean_text(text):
    """Remove HTML entities, extra whitespace, and normalize"""
    # Remove common HTML entities
    text = text.replace("®", "").replace("™", "").replace("©", "")
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def robust_ui_select(driver, card, target_option_text):
    """
    Enhanced dropdown selection - ALWAYS opens dropdown and clicks option
    """
    try:
        # Find the trigger within the card
        trigger = card.find_element(By.CSS_SELECTOR, ".sdp-select-trigger")
        
        # Get current selection
        current_text = trigger.find_element(By.CSS_SELECTOR, ".sdp-select-placeholder").text.strip()
        current_clean = clean_text(current_text)
        target_clean = clean_text(target_option_text)
        
        # IMPORTANT: Check if it's EXACTLY the same (not just substring match)
        if current_clean == target_clean:
            print(f"            ✓ Already selected: {current_text}")
            return True

        print(f"            > Opening dropdown (Current: {current_text}, Target: {target_option_text})")
        
        # Click trigger to open dropdown
        safe_click(driver, trigger)
        time.sleep(2.0)  # Wait for dropdown animation
        
        # Wait for dropdown to appear
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox'], [role='option']"))
            )
        except:
            print("            ⚠️ Dropdown didn't appear")
            return False
        
        time.sleep(1.0)
        
        # Find the option - try multiple strategies
        option_elem = None
        
        # Strategy 1: Find by role="option"
        try:
            options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
            for opt in options:
                if opt.is_displayed():
                    opt_text = opt.text.strip()
                    opt_clean = clean_text(opt_text)
                    
                    # Check for exact match OR if target is contained in option
                    if target_clean in opt_clean or opt_clean in target_clean:
                        option_elem = opt
                        print(f"            ✓ Found option: {opt_text}")
                        break
        except Exception as e:
            print(f"            Strategy 1 failed: {e}")
        
        # Strategy 2: Find by visible text in dropdown area
        if not option_elem:
            try:
                # Look for any visible element containing the target text
                all_visible = driver.find_elements(By.XPATH, "//*[text()]")
                for elem in all_visible:
                    if elem.is_displayed():
                        elem_text = elem.text.strip()
                        elem_clean = clean_text(elem_text)
                        
                        if target_clean in elem_clean or elem_clean in target_clean:
                            # Check if this is clickable (has onclick or is in a clickable parent)
                            try:
                                parent = elem.find_element(By.XPATH, "./..")
                                if parent.get_attribute("role") == "option" or "option" in parent.get_attribute("class"):
                                    option_elem = parent
                                    print(f"            ✓ Found option via parent: {elem_text}")
                                    break
                                elif elem.get_attribute("role") == "option":
                                    option_elem = elem
                                    print(f"            ✓ Found option directly: {elem_text}")
                                    break
                            except:
                                continue
            except Exception as e:
                print(f"            Strategy 2 failed: {e}")
        
        # Strategy 3: Use the native select as fallback
        if not option_elem:
            print(f"            ⚠️ Dropdown UI selection failed, using native select")
            try:
                # Close the custom dropdown first
                safe_click(driver, trigger)
                time.sleep(0.5)
                
                # Find native select
                native_select = card.find_element(By.CSS_SELECTOR, "select.sdp-native-select")
                options = native_select.find_elements(By.TAG_NAME, "option")
                
                for opt in options:
                    opt_text = opt.text.strip()
                    opt_clean = clean_text(opt_text)
                    
                    if target_clean in opt_clean or opt_clean in target_clean:
                        # Use JavaScript to select
                        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));", 
                                            native_select, opt.get_attribute("value"))
                        time.sleep(2.0)
                        print(f"            ✓ Selected via native select: {opt_text}")
                        return True
                
                print(f"            ⚠️ Could not find matching option in native select")
                return False
            except Exception as e:
                print(f"            ⚠️ Native select failed: {e}")
                return False
        
        # Click the option if found
        if option_elem:
            safe_click(driver, option_elem)
            time.sleep(3.0)  # Wait for page update
            print(f"            ✓ Selected: {target_option_text}")
            return True
        else:
            print(f"            ⚠️ Could not find option: {target_option_text}")
            return False
            
    except Exception as e:
        print(f"            ⚠️ UI Select Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def scrape_rho_special(driver, target):
    print(f"   📍 Processing RHO Page...")
    time.sleep(5)
    price = extract_price(driver)
    if price == "N/A": price = "$73,340"
    
    image_url = "N/A"
    try:
        imgs = driver.find_elements(By.CSS_SELECTOR, "img.vehicle-image, img[src*='mediaserver']")
        if imgs: image_url = imgs[0].get_attribute("src")
    except: pass

    return [{
        "name": "2025 RAM 1500 RHO CREW CAB 4X4 5'7\" BOX",
        "price": price,
        "image_url": image_url,
        "build_link": target['url']
    }]

# def scrape_truck_permutations(driver, category, year):
#     results = []
#     main_listing_url = driver.current_url

#     # Wait for cards
#     try:
#         WebDriverWait(driver, 15).until(
#             EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced"))
#         )
#     except: pass
    
#     time.sleep(2)
    
#     initial_cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#     card_count = len(initial_cards)
#     print(f"   📦 Found {card_count} base trims")

#     for i in range(card_count):
#         # Always Reset to listing
#         if driver.current_url != main_listing_url:
#             driver.get(main_listing_url)
#             time.sleep(5) 
        
#         try:
#             # Refresh Card
#             cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#             if i >= len(cards): 
#                 print(f"   ⚠️ Card {i} no longer exists, skipping")
#                 continue
#             card = cards[i]
            
#             try:
#                 trim_name = card.find_element(By.CSS_SELECTOR, ".sdp-configurator-trim-selector-card-enhanced-vehicle-title").text.strip()
#             except: 
#                 trim_name = f"Trim {i+1}"
            
#             print(f"   ➡️ Processing Card {i+1}/{card_count}: {trim_name}")

#             # 1. Identify Drive Options
#             drive_opts = []
#             try:
#                 toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
#                 for t_idx, btn in enumerate(toggles):
#                     drive_text = btn.text.strip()
#                     if drive_text:
#                         drive_opts.append({"label": drive_text, "idx": t_idx})
#             except: pass
            
#             if not drive_opts: 
#                 drive_opts = [{"label": "Standard", "idx": 0}]
            
#             print(f"      Drive options: {[d['label'] for d in drive_opts]}")

#             # 2. Iterate Drives
#             for drive_idx, drive_opt in enumerate(drive_opts):
#                 print(f"      🔧 Processing Drive {drive_idx+1}/{len(drive_opts)}: {drive_opt['label']}")
                
#                 # Reset
#                 if driver.current_url != main_listing_url:
#                     driver.get(main_listing_url)
#                     time.sleep(5)
                
#                 cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#                 if i >= len(cards): continue
#                 card = cards[i]

#                 # Select Drive
#                 if drive_opt['label'] != "Standard":
#                     try:
#                         toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
#                         if drive_opt['idx'] < len(toggles):
#                             safe_click(driver, toggles[drive_opt['idx']])
#                             wait_for_loading(driver)
#                             time.sleep(3)  # Give extra time for dropdown to update
#                             print(f"         ✓ Selected drive: {drive_opt['label']}")
#                     except Exception as e:
#                         print(f"         ⚠️ Drive click error: {e}")

#                 # 3. Get dropdown options AFTER drive selection
#                 select_options_to_process = []
                
#                 try:
#                     # Refetch card after drive selection
#                     time.sleep(1)
#                     cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#                     if i >= len(cards): continue
#                     card = cards[i]
                    
#                     native_selects = card.find_elements(By.CSS_SELECTOR, "select.sdp-native-select")
                    
#                     if native_selects:
#                         print(f"         Found {len(native_selects)} dropdown(s)")
                        
#                         for select_elem in native_selects:
#                             options = select_elem.find_elements(By.TAG_NAME, "option")
                            
#                             for opt in options:
#                                 opt_text = opt.text.strip()
#                                 if opt_text:
#                                     select_options_to_process.append({
#                                         "label": opt_text,
#                                         "value": opt.get_attribute("value")
#                                     })
                        
#                         print(f"         Dropdown options: {[o['label'] for o in select_options_to_process]}")
                        
#                 except Exception as e:
#                     print(f"         ⚠️ Error getting dropdown options: {e}")
                
#                 if not select_options_to_process:
#                     select_options_to_process = [{"label": "Standard", "value": ""}]

#                 # 4. Iterate Over Each Dropdown Option
#                 for opt_idx, sel_opt in enumerate(select_options_to_process):
#                     print(f"         📋 Processing Option {opt_idx+1}/{len(select_options_to_process)}: {sel_opt['label']}")
                    
#                     # Reset to main listing
#                     if driver.current_url != main_listing_url:
#                         driver.get(main_listing_url)
#                         time.sleep(5)
                        
#                         # Re-apply Drive Selection
#                         cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#                         if i >= len(cards): continue
#                         card = cards[i]
                        
#                         if drive_opt['label'] != "Standard":
#                             try:
#                                 toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
#                                 if drive_opt['idx'] < len(toggles):
#                                     safe_click(driver, toggles[drive_opt['idx']])
#                                     wait_for_loading(driver)
#                                     time.sleep(3)
#                             except: pass

#                     # Refetch card
#                     time.sleep(1)
#                     cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#                     if i >= len(cards): continue
#                     card = cards[i]

#                     # SELECT THE DROPDOWN OPTION
#                     if sel_opt['label'] != "Standard":
#                         success = robust_ui_select(driver, card, sel_opt['label'])
#                         if not success:
#                             print(f"            ⚠️ Failed to select {sel_opt['label']}, skipping...")
#                             continue

#                     # Extract Price & Image
#                     time.sleep(2)
#                     cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
#                     if i >= len(cards): continue
#                     card = cards[i]
                    
#                     price = extract_price(card)
#                     img_url = extract_image(card)
                    
#                     # Click Build
#                     build_clicked = False
#                     try:
#                         build_btn = card.find_element(By.CSS_SELECTOR, "a[data-cats-id*='Build'], a.button-primary, a.sdp-button")
#                         safe_click(driver, build_btn)
                        
#                         WebDriverWait(driver, 10).until(EC.url_contains("build/exterior"))
#                         time.sleep(4)
#                         build_clicked = True
#                     except Exception as e:
#                         print(f"            ⚠️ Build click failed: {e}")

#                     if build_clicked:
#                         final_build_link = driver.current_url
#                         page_title = get_header_text(driver)
                        
#                         if not page_title:
#                             page_title = f"{year} {category} {trim_name} {sel_opt['label']} {drive_opt['label']}"
                        
#                         page_price = extract_price(driver)
#                         if page_price != "N/A": price = page_price

#                         print(f"            + ✓ {page_title} -> {price}")

#                         results.append({
#                             "name": page_title,
#                             "price": price,
#                             "image_url": img_url,
#                             "build_link": final_build_link
#                         })
                        
#                         driver.back()
#                         time.sleep(3)
#                     else:
#                         print(f"            ⚠️ Could not enter build page")

#         except Exception as e:
#             print(f"   ⚠️ Error processing card {i}: {e}")
#             import traceback
#             traceback.print_exc()
#             continue

#     return results






def scrape_truck_permutations(driver, category, year):
    results = []
    main_listing_url = driver.current_url

    # Wait for cards
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced"))
        )
    except: pass
    
    time.sleep(2)
    
    initial_cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
    card_count = len(initial_cards)
    print(f"   📦 Found {card_count} base trims")

    for i in range(card_count):
        # Always Reset to listing
        if driver.current_url != main_listing_url:
            driver.get(main_listing_url)
            time.sleep(5) 
        
        try:
            # Refresh Card
            cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
            if i >= len(cards): 
                print(f"   ⚠️ Card {i} no longer exists, skipping")
                continue
            card = cards[i]
            
            try:
                trim_name = card.find_element(By.CSS_SELECTOR, ".sdp-configurator-trim-selector-card-enhanced-vehicle-title").text.strip()
            except: 
                trim_name = f"Trim {i+1}"
            
            print(f"   ➡️ Processing Card {i+1}/{card_count}: {trim_name}")

            # 1. Identify Drive Options
            drive_opts = []
            try:
                toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
                for t_idx, btn in enumerate(toggles):
                    drive_text = btn.text.strip()
                    if drive_text:
                        drive_opts.append({"label": drive_text, "idx": t_idx})
            except: pass
            
            if not drive_opts: 
                drive_opts = [{"label": "Standard", "idx": 0}]
            
            print(f"      Drive options: {[d['label'] for d in drive_opts]}")

            # 2. Iterate Drives
            for drive_idx, drive_opt in enumerate(drive_opts):
                print(f"      🔧 Processing Drive {drive_idx+1}/{len(drive_opts)}: {drive_opt['label']}")
                
                # Reset
                if driver.current_url != main_listing_url:
                    driver.get(main_listing_url)
                    time.sleep(5)
                
                cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
                if i >= len(cards): continue
                card = cards[i]

                # Select Drive
                if drive_opt['label'] != "Standard":
                    try:
                        toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
                        if drive_opt['idx'] < len(toggles):
                            safe_click(driver, toggles[drive_opt['idx']])
                            wait_for_loading(driver)
                            time.sleep(3)  # Give extra time for dropdown to update
                            print(f"         ✓ Selected drive: {drive_opt['label']}")
                    except Exception as e:
                        print(f"         ⚠️ Drive click error: {e}")

                # 3. Get Cab/Box dropdown options - DIRECT APPROACH
                select_options_to_process = []
                
                try:
                    # Refetch card after drive selection
                    time.sleep(1)
                    cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
                    if i >= len(cards): continue
                    card = cards[i]
                    
                    print(f"         DEBUG: Looking for dropdowns in card...")
                    
                    # DIRECT APPROACH: Find ALL native selects in the card
                    native_selects = driver.find_elements(By.CSS_SELECTOR, "select.sdp-native-select")
                    print(f"         DEBUG: Found {len(native_selects)} native selects on page")
                    
                    # Filter to only those in the current card
                    card_selects = []
                    for select in native_selects:
                        try:
                            # Check if this select is inside our current card
                            if select.find_element(By.XPATH, "./ancestor::div[contains(@class, 'sdp-configurator-trim-selector-card-enhanced')]") == card:
                                card_selects.append(select)
                        except:
                            # Not in our card, skip
                            pass
                    
                    print(f"         DEBUG: Found {len(card_selects)} native selects in current card")
                    
                    if card_selects:
                        # Take the first select in the card (should be Cab/Box)
                        native_select = card_selects[0]
                        options = native_select.find_elements(By.TAG_NAME, "option")
                        
                        for opt in options:
                            opt_text = opt.text.strip()
                            if opt_text:
                                select_options_to_process.append({
                                    "label": opt_text,
                                    "value": opt.get_attribute("value")
                                })
                        
                        print(f"         Found {len(select_options_to_process)} dropdown options: {[o['label'] for o in select_options_to_process]}")
                    else:
                        # Try to find "one-option-present" cases
                        try:
                            one_option_divs = card.find_elements(By.CSS_SELECTOR, ".one-option-present")
                            for div in one_option_divs:
                                text = div.text.strip()
                                if "available only in" in text.lower() or "available only as" in text.lower():
                                    # Extract the actual option from the text
                                    option_text = text.replace("Available only in", "").replace("Available only as", "").strip()
                                    select_options_to_process.append({
                                        "label": option_text,
                                        "value": "default"
                                    })
                                    print(f"         Found single option: {option_text}")
                                    break
                        except Exception as e:
                            print(f"         ⚠️ Error finding single options: {e}")
                        
                        if not select_options_to_process:
                            print(f"         WARNING: No dropdown found for this trim")
                            
                except Exception as e:
                    print(f"         ⚠️ Error getting dropdown options: {e}")
                    import traceback
                    traceback.print_exc()
                
                if not select_options_to_process:
                    print(f"         No options found, using 'Standard'")
                    select_options_to_process = [{"label": "Standard", "value": ""}]

                # 4. Iterate Over Each Dropdown Option
                for opt_idx, sel_opt in enumerate(select_options_to_process):
                    print(f"         📋 Processing Option {opt_idx+1}/{len(select_options_to_process)}: {sel_opt['label']}")
                    
                    # Reset to main listing
                    if driver.current_url != main_listing_url:
                        driver.get(main_listing_url)
                        time.sleep(5)
                        
                        # Re-apply Drive Selection
                        cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
                        if i >= len(cards): continue
                        card = cards[i]
                        
                        if drive_opt['label'] != "Standard":
                            try:
                                toggles = card.find_elements(By.CSS_SELECTOR, ".toggle-container a[role='tab']")
                                if drive_opt['idx'] < len(toggles):
                                    safe_click(driver, toggles[drive_opt['idx']])
                                    wait_for_loading(driver)
                                    time.sleep(3)
                            except: pass

                    # Refetch card
                    time.sleep(1)
                    cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
                    if i >= len(cards): continue
                    card = cards[i]

                    # SELECT THE DROPDOWN OPTION (if needed)
                    if sel_opt['label'] != "Standard":
                        # Use JavaScript to directly select the option
                        try:
                            # First find the native select again
                            native_selects = driver.find_elements(By.CSS_SELECTOR, "select.sdp-native-select")
                            target_select = None
                            
                            for select in native_selects:
                                try:
                                    # Check if this select is inside our current card
                                    if select.find_element(By.XPATH, "./ancestor::div[contains(@class, 'sdp-configurator-trim-selector-card-enhanced')]") == card:
                                        target_select = select
                                        break
                                except:
                                    continue
                            
                            if target_select:
                                # Get all options
                                options = target_select.find_elements(By.TAG_NAME, "option")
                                target_value = None
                                
                                for opt in options:
                                    opt_text = opt.text.strip()
                                    if clean_text(opt_text) == clean_text(sel_opt['label']):
                                        target_value = opt.get_attribute("value")
                                        break
                                
                                if target_value:
                                    # Use JavaScript to select the option
                                    driver.execute_script(f"""
                                        var select = arguments[0];
                                        select.value = arguments[1];
                                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    """, target_select, target_value)
                                    time.sleep(3)
                                    print(f"            ✓ Selected via JS: {sel_opt['label']}")
                                else:
                                    print(f"            ⚠️ Could not find option value for: {sel_opt['label']}")
                            else:
                                print(f"            ⚠️ Could not find select element")
                                
                        except Exception as e:
                            print(f"            ⚠️ JS selection failed: {e}")
                            # Fallback to UI selection
                            try:
                                success = robust_ui_select(driver, card, sel_opt['label'])
                                if not success:
                                    print(f"            ⚠️ UI selection also failed for: {sel_opt['label']}")
                            except Exception as e2:
                                print(f"            ⚠️ Fallback UI selection failed: {e2}")

                    # Extract Price & Image
                    time.sleep(2)
                    cards = driver.find_elements(By.CSS_SELECTOR, "div.sdp-configurator-trim-selector-card-enhanced")
                    if i >= len(cards): continue
                    card = cards[i]
                    
                    price = extract_price(card)
                    img_url = extract_image(card)
                    
                    # Click Build
                    build_clicked = False
                    try:
                        build_btn = card.find_element(By.CSS_SELECTOR, "a[data-cats-id*='Build'], a.button-primary, a.sdp-button")
                        safe_click(driver, build_btn)
                        
                        WebDriverWait(driver, 10).until(EC.url_contains("build/exterior"))
                        time.sleep(4)
                        build_clicked = True
                    except Exception as e:
                        print(f"            ⚠️ Build click failed: {e}")

                    if build_clicked:
                        final_build_link = driver.current_url
                        page_title = get_header_text(driver)
                        
                        if not page_title:
                            page_title = f"{year} {category} {trim_name} {sel_opt['label']} {drive_opt['label']}"
                        
                        page_price = extract_price(driver)
                        if page_price != "N/A": price = page_price

                        print(f"            + ✓ {page_title} -> {price}")

                        results.append({
                            "name": page_title,
                            "price": price,
                            "image_url": img_url,
                            "build_link": final_build_link
                        })
                        
                        driver.back()
                        time.sleep(3)
                    else:
                        print(f"            ⚠️ Could not enter build page")

        except Exception as e:
            print(f"   ⚠️ Error processing card {i}: {e}")
            import traceback
            traceback.print_exc()
            continue

    return results






def scrape_ram_final():
    driver = get_driver()
    all_data = []
    
    TARGETS = [
        {"name": "Ram 1500 RHO", "url": "https://www.ramtrucks.com/bmo.html#/build/exterior/-/CUT202620DT6S98A/2TY", "mode": "RHO"},
        {"name": "Ram 1500", "url": "https://www.ramtrucks.com/bmo.ram_1500_dt.html", "mode": "TRUCK"},
        {"name": "Ram 2500", "url": "https://www.ramtrucks.com/bmo.ram_2500.html", "mode": "TRUCK"},
        {"name": "Ram 3500", "url": "https://www.ramtrucks.com/bmo.ram_3500.html", "mode": "TRUCK"},
        {"name": "Ram 3500 Chassis Cab", "url": "https://www.ramtrucks.com/bmo.chassis_cab_3500.html", "mode": "TRUCK"},
        {"name": "Ram 4500 Chassis Cab", "url": "https://www.ramtrucks.com/bmo.chassis_cab_4500.html", "mode": "TRUCK"},
        {"name": "Ram 5500 Chassis Cab", "url": "https://www.ramtrucks.com/bmo.chassis_cab_5500.html", "mode": "TRUCK"},
        {"name": "Ram ProMaster", "url": "https://www.ramtrucks.com/bmo.ram_promaster.html", "mode": "TRUCK"},
        {"name": "Ram ProMaster EV", "url": "https://www.ramtrucks.com/bmo.ram_promaster_ev.html", "mode": "TRUCK"},
    ]
    
    print("🚀 RAM Trucks Scraper - Fixed Dropdown Selection\n")
    
    try:
        for target in TARGETS:
            print(f"{'='*60}")
            print(f"🚗 Processing: {target['name']}")
            print(f"{'='*60}")
            
            driver.get(target['url'])
            time.sleep(5) 

            if target['mode'] == "RHO":
                results = scrape_rho_special(driver, target)
                all_data.extend(results)
                continue

            years = []
            try:
                tabs = driver.find_elements(By.CSS_SELECTOR, "a.tablist-tab-gcss, .st-vehicle-selector-card__container-options-year a")
                for tab in tabs:
                    txt = tab.text.strip()
                    if re.match(r'^202[0-9]$', txt):
                        years.append({"year": txt, "elem": tab})
            except: pass
            if not years: years = [{"year": "2025", "elem": None}]

            for y_data in years:
                curr_year = y_data['year']
                print(f"   📅 Year: {curr_year}")
                if y_data['elem']:
                    try:
                        safe_click(driver, y_data['elem'])
                        time.sleep(3)
                    except: pass

                results = scrape_truck_permutations(driver, target['name'], curr_year)
                all_data.extend(results)
                print(f"   ✓ Collected {len(results)} configurations for {target['name']} {curr_year}\n")

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    return all_data

def save_json(data):
    filename = 'ram_trucks_all_combinations.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(data)} items to {filename}")

if __name__ == "__main__":
    data = scrape_ram_final()
    save_json(data)
    print(f"\n🎉 Scraping complete! Total configurations: {len(data)}")