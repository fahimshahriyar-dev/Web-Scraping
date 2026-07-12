import json
import time
import logging
import re
import csv
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    USE_WDM = True
except ImportError:
    USE_WDM = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Performance tuning
_FAST_MODE = False          # set True for shorter waits, fewer image captures
_image_captures_done = 0    # global counter for image capture tracking
MAX_IMAGE_CAPTURES = 15     # max car image captures per trim (0 = unlimited)

# ══════════════════════════════════════════════════════════════════════════════
#  COMPLETE MODEL / TRIM INVENTORY
#  LIVE model/trim data from https://models.porsche.com/en-US/model-start  (2026-05-31)
# ══════════════════════════════════════════════════════════════════════════════
# NOTE: 718 is no longer on the US configurator — page redirects to Porsche Finder
#       (used cars).  Removed entirely.
#
# Trim configurator codes marked with TODO need verification.
# Run:  python ultimate_porsche.py --models <MODEL> --discover  to verify codes.
MODEL_TRIMS = {
    "911": {
        "trims": [
            ("911 Carrera S",            "9921S2")
        ],
    }
}

# ══════════════════════════════════════════════════════════════════════════════
#  PRICES verified from https://models.porsche.com/en-US/model-start  (2026-05-31)
#  Prices are MSRP "From $X" as shown on the website.
# ══════════════════════════════════════════════════════════════════════════════
MODEL_TRIMS = {
    "911": {
        "trims": [
            ("911 Carrera",              "9921B2"),
            ("911 Carrera T",            "992182"),
            ("911 Carrera S",            "9921S2"),
            ("911 Carrera 4S",           "9924S2"),
            ("911 Carrera GTS",          "992142"),
            ("911 Carrera 4 GTS",        "992442"),
            ("911 Carrera Cabriolet",    "9923B2"),
            ("911 Carrera T Cabriolet",  "992382"),
            ("911 Carrera S Cabriolet",  "9923S2"),
            ("911 Carrera 4S Cabriolet", "9926S2"),
            ("911 Carrera GTS Cabriolet","992342"),
            ("911 Carrera 4 GTS Cabriolet","992642"),
            ("911 Targa 4S",             "9925S2"),
            ("911 Targa 4 GTS",          "992542"),
            ("911 Turbo S",              "992452"),
            ("911 Turbo S Cabriolet",    "992652"),
            ("911 GT3",                  "992812"),
            ("911 GT3 with Touring Package","992822"),
            ("911 GT3 S/C",              "992892"),
            ("911 Spirit 70",            "992352"),
        ],
    },
    "Taycan": {
        "trims": [
            ("Taycan",                   "Y1AAI1"),
            ("Taycan Black Edition",     "Y1AGI1"),
            ("Taycan 4",                 "Y1ABN1"),
            ("Taycan 4 Black Edition",   "Y1AHN1"),
            ("Taycan 4S",                "Y1ADJ1"),
            ("Taycan 4S Black Edition",  "Y1AJJ1"),
            ("Taycan GTS",               "Y1ADK1"),
            ("Taycan Turbo",             "Y1AFL1"),
            ("Taycan Turbo S",           "Y1AFM1"),
            ("Taycan Turbo GT",          "Y1AFT1"),
            ("Taycan Turbo GT with Weissach Package","Y1AFP1"),
            ("Taycan GTS Sport Turismo", "Y1CDK1"),
            ("Taycan 4 Cross Turismo",   "Y1BBN1"),
            ("Taycan 4S Cross Turismo",  "Y1BDJ1"),
            ("Taycan Turbo Cross Turismo",  "Y1BFL1"),
            ("Taycan Turbo S Cross Turismo","Y1BFM1"),
        ],
    },
    "Panamera": {
        "trims": [
            ("Panamera",                 "YAAAA1"),
            ("Panamera 4",               "YAABA1"),
            ("Panamera 4 E-Hybrid",      "YAABE1"),
            ("Panamera 4S E-Hybrid",     "YAADZ1"),
            ("Panamera GTS",             "YAADG1"),
            ("Panamera Turbo E-Hybrid",  "YAAFF1"),
            ("Panamera Turbo S E-Hybrid","YAAFH1"),
        ],
    },
    "Macan": {
        "trims": [
            ("Macan",                    "95BAU1"),   # gasoline — discovered live
            ("Macan T",                  "95BAN1"),   # gasoline
            ("Macan S",                  "TODO_MACAN_S_GAS"),
            ("Macan GTS",                "TODO_MACAN_GTS_GAS"),
            ("Macan Electric",           "XABAA1"),
            ("Macan 4 Electric",         "XABBB1"),
            ("Macan 4S Electric",        "XABDC1"),
            ("Macan GTS Electric",       "XABDE1"),
            ("Macan Turbo Electric",     "XABFD1"),
        ],
    },
    "Cayenne": {
        "trims": [
            ("Cayenne Electric",         "X1AAA1"),
            ("Cayenne S Electric",       "TODO_CAYENNE_S_EV"),
            ("Cayenne Turbo Electric",   "X1ACD1"),
            ("Cayenne Coupe Electric",   "TODO_CAYENNE_CP_EV"),
            ("Cayenne S Coupe Electric", "TODO_CAYENNE_SCP_EV"),
            ("Cayenne Turbo Coupe Electric","TODO_CAYENNE_TCP_EV"),
            ("Cayenne",                  "9YAAI1"),
            ("Cayenne E-Hybrid",         "9YAAV1"),
            ("Cayenne S",                "9YABJ1"),
            ("Cayenne S E-Hybrid",       "9YABN1"),
            ("Cayenne GTS",              "9YABS1"),
            ("Cayenne Turbo E-Hybrid",   "9YACT1"),
            ("Cayenne Coupe",            "9YBAI1"),
            ("Cayenne E-Hybrid Coupe",   "9YBAV1"),
            ("Cayenne S Coupe",          "9YBBJ1"),
            ("Cayenne S E-Hybrid Coupe", "9YBBN1"),
            ("Cayenne GTS Coupe",        "9YBBS1"),
            ("Cayenne Turbo E-Hybrid Coupe","9YBCT1"),
            ("Cayenne Turbo GT",         "TODO_CAYENNE_TURBO_GT"),
        ],
    },
}

def get_car_data():
    """Generate CAR_DATA dict from MODEL_TRIMS + TRIM_PRICES.

    Each model has:
      "base_image": ""  (to be filled by scraped PRS image URL)
      "trims": [{"name": ..., "link": ..., "price": ..., "image": ""}, ...]
    """
    car_data = {}
    for model_name, model_info in MODEL_TRIMS.items():
        model_prices = TRIM_PRICES.get(model_name, {})
        trims_out = []
        for trim_name, code in model_info["trims"]:
            if code and not code.startswith("TODO_"):
                link = f"https://configurator.porsche.com/en-US/mode/model/{code}"
            else:
                link = ""
            price = model_prices.get(trim_name, "")
            trims_out.append({
                "name": trim_name,
                "link": link,
                "price": price,
                "image": "",
            })
        car_data[model_name] = {
            "base_image": "",
            "trims": trims_out,
        }
    return car_data


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION REGISTRY — same data-testid / container pattern across all trims
# ══════════════════════════════════════════════════════════════════════════════
SECTIONS = [
    {
        "key": "wheels",
        "btn_testid": "section-section-wheels-button",
        "container_id": "section-wheels-toggle-container",
        "strategy": "wheels",
    },
    {
        "key": "exterior_colors",
        "btn_testid": "section-section-exterior-color-button",
        "container_id": "section-exterior-color-toggle-container",
        "strategy": "flat_with_expand",
    },
    {
        "key": "interior_colors_and_material",
        "btn_testid": "section-section-interior-color-button",
        "container_id": "section-interior-color-toggle-container",
        "strategy": "interior_colors",
    },
    {
        "key": "seats",
        "btn_testid": "section-section-interior-seats-button",
        "container_id": "section-interior-seats-toggle-container",
        "strategy": "flat",
    },
    {
        "key": "packages",
        "btn_testid": "section-section-individualization-packages-button",
        "container_id": "section-individualization-packages-toggle-container",
        "strategy": "flat",
    },
    {
        "key": "exterior",
        "btn_testid": "section-section-individualization-exterior-button",
        "container_id": "section-individualization-exterior-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "interior",
        "btn_testid": "section-section-individualization-interior-button",
        "container_id": "section-individualization-interior-toggle-container",
        "strategy": "interior",
    },
    {
        "key": "technology",
        "btn_testid": "section-section-individualization-technology-button",
        "container_id": "section-individualization-technology-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "vehicle_accessories",
        "btn_testid": "section-section-vehicle-accessories-button",
        "container_id": "section-vehicle-accessories-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "delivery_experience",
        "btn_testid": "section-section-individualization-delivery-button",
        "container_id": "section-individualization-delivery-toggle-container",
        "strategy": "flat",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
#  DRIVER FACTORY
# ══════════════════════════════════════════════════════════════════════════════
def build_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if USE_WDM:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=opts
        )
    else:
        driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def safe_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'});", el)
    time.sleep(0.5)
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)


def dismiss_overlays(driver, timeout=15):
    log.info("Waiting for cookie banner (up to %ds)...", timeout)

    JS_SHADOW_CLICK = """
        function deepQuery(root, selector) {
            var queue = [root];
            while (queue.length) {
                var node = queue.shift();
                var found = node.querySelectorAll(selector);
                if (found.length) return Array.from(found);
                var all = node.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    if (all[i].shadowRoot) queue.push(all[i].shadowRoot);
                }
            }
            return [];
        }

        var buttons = deepQuery(document, 'uc-p-button.accept');
        if (!buttons.length) {
            buttons = deepQuery(document, 'uc-p-button[variant="primary"]');
        }

        for (var i = 0; i < buttons.length; i++) {
            var host = buttons[i];
            if (host.shadowRoot) {
                var inner = host.shadowRoot.querySelector('button');
                if (inner) { inner.click(); return 'shadow-inner:' + i; }
            }
            host.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            return 'host-dispatch:' + i;
        }
        return null;
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = driver.execute_script(JS_SHADOW_CLICK)
            if result:
                time.sleep(1.5)
                log.info("Cookie banner dismissed via shadow-DOM walk (%s)", result)
                return
        except Exception as e:
            log.debug("Shadow-walk attempt error: %s", e)
        time.sleep(0.5)

    log.debug("Shadow-walk timed out after %ds — trying fallback tiers", timeout)

    for sel in [
        "uc-p-button.accept",
        "uc-p-button[variant='primary']",
        "#onetrust-accept-btn-handler",
        "button[data-testid='uc-accept-all-button']",
        "button.accept-all-button",
        "[aria-label*='Accept all']",
        "[aria-label*='accept all']",
    ]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                safe_click(driver, btn)
                time.sleep(1.5)
                log.info("Cookie banner dismissed via CSS selector (%s)", sel)
                return
        except NoSuchElementException:
            pass

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                result = driver.execute_script(JS_SHADOW_CLICK)
                if result:
                    time.sleep(1.5)
                    log.info("Cookie banner dismissed inside iframe via shadow-walk (%s)", result)
                    driver.switch_to.default_content()
                    return
                for sel in ["uc-p-button.accept", "uc-p-button[variant='primary']"]:
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, sel)
                        if btn.is_displayed():
                            safe_click(driver, btn)
                            time.sleep(1.5)
                            log.info("Cookie banner dismissed in iframe via CSS (%s)", sel)
                            driver.switch_to.default_content()
                            return
                    except NoSuchElementException:
                        pass
            except Exception:
                pass
            finally:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
    except Exception as e:
        log.debug("iframe search failed: %s", e)

    try:
        for el in driver.find_elements(
            By.XPATH,
            "//*[normalize-space(.)='Accept all' or normalize-space(text())='Accept all']"
        ):
            try:
                if el.is_displayed():
                    safe_click(driver, el)
                    time.sleep(1.5)
                    log.info("Cookie banner dismissed via XPath text match")
                    return
            except Exception:
                pass
    except Exception as e:
        log.debug("XPath text-match failed: %s", e)

    log.warning("Cookie banner not found or already dismissed — continuing")


def get_hero_image(driver):
    for sel in [
        "img[src*='prs.porsche.com']",
        "img[src*='/iod/image/']",
        "img[src*='models.porsche.com']",
        "img[src*='pictures.porsche.com']",
        "div[class*='viewer'] img",
        "div[role='img']",
        "[data-testid='stage-image'] img"
    ]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                src = el.get_attribute("src") or ""
                if src and "data:image" not in src and len(src) > 30:
                    return src
        except Exception:
            pass

    try:
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            src = img.get_attribute("src") or ""
            if src and "data:image" not in src and len(src) > 50:
                width = img.get_attribute("width") or "0"
                height = img.get_attribute("height") or "0"
                try:
                    if int(width) > 300 or int(height) > 300:
                        return src
                except Exception:
                    if "porsche" in src.lower() and "config" in src.lower():
                        return src
    except Exception:
        pass

    try:
        for canvas in driver.find_elements(By.TAG_NAME, "canvas"):
            w = int(canvas.get_attribute("width") or "0")
            h = int(canvas.get_attribute("height") or "0")
            if w > 300 and h > 200:
                data_url = driver.execute_script("return arguments[0].toDataURL('image/png');", canvas)
                if data_url and data_url.startswith("data:image"):
                    return data_url
    except Exception:
        pass

    return ""


def wait_for_image_change(driver, old_src, timeout=8.0):
    deadline = time.time() + timeout
    time.sleep(0.5)
    while time.time() < deadline:
        new_src = get_hero_image(driver)
        if new_src and new_src != old_src:
            if len(new_src) > 30 and "data:image" not in new_src:
                return new_src
        time.sleep(0.3)
    final_src = get_hero_image(driver)
    if final_src and final_src != old_src:
        return final_src
    return old_src


def extract_price_from_text(text):
    if not text:
        return ""
    m = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    return m.group(0) if m else ""


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def expand_all_toggle_buttons(driver, container, label="section", max_passes=5):
    container_id = container.get_attribute("id") or ""
    for pass_num in range(max_passes):
        if container_id:
            try:
                container = driver.find_element(By.ID, container_id)
            except NoSuchElementException:
                break

        collapsed = container.find_elements(
            By.CSS_SELECTOR,
            "button[aria-expanded='false'][aria-controls$='-toggle-container']",
        )
        if not collapsed:
            log.info(f"    [{label}] All toggles expanded after pass {pass_num + 1}")
            break

        log.info(f"    [{label}] Pass {pass_num + 1}: {len(collapsed)} collapsed button(s)")
        for btn in collapsed:
            try:
                controls = btn.get_attribute("aria-controls") or ""
                try:
                    lbl = btn.find_element(By.CSS_SELECTOR, "h3").text.strip()
                except NoSuchElementException:
                    lbl = btn.text.strip().split("\n")[0] or controls
                log.info(f"      Expanding: '{lbl}' → #{controls}")
                if btn.get_attribute("aria-expanded") != "true":
                    safe_click(driver, btn)
                    time.sleep(1.5)
            except StaleElementReferenceException:
                log.debug("      Button stale, skipping")
            except Exception as e:
                log.debug(f"      Expand failed: {e}")
        time.sleep(1.0)

    time.sleep(2.0)
    if container_id:
        try:
            container = driver.find_element(By.ID, container_id)
        except NoSuchElementException:
            pass
    return container


def scrape_base_price_from_page(driver):
    """Scrape the Base MSRP price from the configurator page summary panel.
    Tries multiple strategies to find the actual base price (vs $0 options)."""
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        pass

    # Strategy 1: Find exact "Base MSRP" label followed by a price
    patterns = [
        r'Base MSRP\s+\$[\d,]+',
        r'Base MSRP.*?\$[\d,]+',
        r'MSRP\s+\$[\d,]+',
        r'Total MSRP\s+\$[\d,]+',
    ]
    for pat in patterns:
        m = re.search(pat, body_text)
        if m:
            price = extract_price_from_text(m.group(0))
            if price and price != "$0":
                return price

    # Strategy 2: Look for large price values in summary panel
    for sel in [
        "div[class*='sticky'] span[class*='text-contrast']",
        "div[class*='summary'] span",
        "aside span[class*='text-contrast']",
        "[data-testid*='price'] span",
        "p[class*='text-contrast'] span",
    ]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                price = extract_price_from_text(el.text)
                if price and price != "$0":
                    try:
                        val = int(price.replace("$", "").replace(",", ""))
                        if val > 1000:
                            return price
                    except ValueError:
                        pass
        except Exception:
            pass

    # Strategy 3: Find the largest price on the page
    all_prices = re.findall(r'\$[\d,]+(?:\.\d{2})?', body_text)
    valid_prices = []
    for p in all_prices:
        try:
            val = int(p.replace("$", "").replace(",", ""))
            if val > 1000:
                valid_prices.append((val, p))
        except ValueError:
            pass

    if valid_prices:
        valid_prices.sort(key=lambda x: x[0], reverse=True)
        return valid_prices[0][1]

    return ""


def get_group_price(driver, input_el, container_el):
    for xpath in [
        "./ancestor::div[.//h3 and .//p[contains(@class,'text-contrast')]][1]",
        "./ancestor::div[.//h3][1]",
    ]:
        try:
            group_block = input_el.find_element(By.XPATH, xpath)
            price_span = group_block.find_element(
                By.CSS_SELECTOR,
                "p.text-contrast-medium span, p[class*='text-contrast'] span, span[class*='price'], span[class*='amount']",
            )
            price = extract_price_from_text(price_span.get_attribute("textContent") or "")
            if price:
                return price
        except Exception:
            pass
    try:
        group_wrapper = input_el.find_element(
            By.XPATH,
            "./ancestor::div[contains(@class,'flex-col') or contains(@class,'grid')][1]/parent::div",
        )
        price_span = group_wrapper.find_element(By.XPATH, ".//p[contains(@class,'text-contrast')]//span")
        price = extract_price_from_text(price_span.get_attribute("textContent") or "")
        if price:
            return price
    except Exception:
        pass
    try:
        all_spans = container_el.find_elements(
            By.CSS_SELECTOR, "p.text-contrast-medium span, p[class*='text-contrast'] span, span[class*='price'], span[class*='amount']"
        )
        result = driver.execute_script("""
            var input = arguments[0]; var spans = arguments[1];
            var inputTop = input.getBoundingClientRect().top;
            var best = null; var bestDist = Infinity;
            for (var i = 0; i < spans.length; i++) {
                var spanTop = spans[i].getBoundingClientRect().top;
                var dist = inputTop - spanTop;
                if (dist >= 0 && dist < bestDist) { bestDist = dist; best = spans[i]; }
            }
            return best ? (best.textContent || best.innerText || '').trim() : '';
        """, input_el, all_spans)
        price = extract_price_from_text(result or "")
        if price:
            return price
    except Exception:
        pass

    try:
        all_price_els = container_el.find_elements(By.XPATH, './/*[contains(text(), "$")]')
        if all_price_els:
            result = driver.execute_script("""
                var input = arguments[0]; var priceEls = arguments[1];
                var inputTop = input.getBoundingClientRect().top;
                var best = null; var bestDist = Infinity;
                for (var i = 0; i < priceEls.length; i++) {
                    var elTop = priceEls[i].getBoundingClientRect().top;
                    var dist = inputTop - elTop;
                    if (dist >= 0 && dist < bestDist) { bestDist = dist; best = priceEls[i]; }
                }
                return best ? (best.textContent || best.innerText || '').trim() : '';
            """, input_el, all_price_els)
            price = extract_price_from_text(result or "")
            if price:
                return price
    except Exception:
        pass

    try:
        price = extract_price_from_text(input_el.get_attribute("data-price") or "")
        if price:
            return price
    except Exception:
        pass

    return ""


def get_card_price(card_el):
    for sel in [
        "p.text-contrast-medium span, p[class*='text-contrast'] span",
        "span[class*='price']",
        "span[class*='amount']",
        "[data-testid*='price']",
        "p span",
    ]:
        try:
            for el in card_el.find_elements(By.CSS_SELECTOR, sel):
                txt = el.get_attribute("textContent") or ""
                p = extract_price_from_text(txt)
                if p:
                    return p
        except Exception:
            pass
    try:
        price_text = card_el.find_element(
            By.CSS_SELECTOR,
            "label p.text-contrast-medium, label p[class*='text-contrast']"
        ).get_attribute("textContent") or ""
        p = extract_price_from_text(price_text)
        if p:
            return p
    except Exception:
        pass
    try:
        for el in card_el.find_elements(By.XPATH, './/*[contains(text(), "$")]'):
            txt = el.get_attribute("textContent") or ""
            p = extract_price_from_text(txt)
            if p:
                return p
    except Exception:
        pass
    try:
        # Fallback to checking the textContent of the card element itself
        card_txt = card_el.get_attribute("textContent") or ""
        p = extract_price_from_text(card_txt)
        if p:
            return p
    except Exception:
        pass
    return ""


def extract_swatch_style(input_el):
    style = input_el.get_attribute("style") or ""
    swatch_image = ""
    swatch_colors = []

    url_match = re.search(r'background-image\s*:\s*url\(["\']?([^"\'\)]+)["\']?\)', style)
    if url_match:
        src = url_match.group(1)
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://configurator.porsche.com" + src
        swatch_image = src
        return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}

    bg_color_match = re.search(r'background-color\s*:\s*(rgb[a]?\([^)]+\))', style)
    if bg_color_match:
        swatch_colors.append(bg_color_match.group(1).strip())
        return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}

    if "linear-gradient" in style:
        rgb_values = re.findall(r'rgb\(\s*[\d,\s]+\)', style)
        seen = set()
        for c in rgb_values:
            normalized = re.sub(r'\s+', '', c)
            if normalized not in seen:
                seen.add(normalized)
                swatch_colors.append(c.strip())

    return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}


# ══════════════════════════════════════════════════════════════════════════════
#  ATOMIC SCRAPERS
# ══════════════════════════════════════════════════════════════════════════════
def capture_image_on_click(driver, click_target, option_name):
    global _image_captures_done
    # Always respect the capture limit (prevents 50+ clicks destabilizing the page)
    if MAX_IMAGE_CAPTURES > 0 and _image_captures_done >= MAX_IMAGE_CAPTURES:
        return get_hero_image(driver)
    if _FAST_MODE:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'instant'});", click_target)
            time.sleep(0.2)
            try:
                click_target.click()
            except Exception:
                driver.execute_script("arguments[0].click();", click_target)
            time.sleep(0.8)
            car_image = get_hero_image(driver)
            _image_captures_done += 1
            return car_image
        except Exception as e:
            log.debug(f"        image capture failed for '{option_name}': {e}")
            return get_hero_image(driver)

    car_image = ""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior: 'smooth'});", click_target)
        time.sleep(0.8)
        before_image = get_hero_image(driver)
        try:
            click_target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", click_target)
        time.sleep(1.5)
        car_image = wait_for_image_change(driver, before_image, timeout=10.0)
        if not car_image or car_image == before_image:
            time.sleep(2.0)
            car_image = get_hero_image(driver)
        _image_captures_done += 1
    except Exception as e:
        log.debug(f"        image capture failed for '{option_name}': {e}")
        car_image = get_hero_image(driver)
    return car_image


def scrape_option_by_input(driver, input_el, container_el):
    """Scrapes a single option strictly using its checkbox/radio input element and its parent container.
    This guarantees no duplicate/placeholder option generation and prevents price leakage across unrelated options."""
    try:
        if not input_el.is_displayed() and not input_el.get_attribute("opacity") == "0":
            # If the input is not displayed at all (and it's not just styled as invisible checkbox)
            # check if its parent or card is displayed.
            pass

        # 1. Determine Option Card/Wrapper Container
        option_container = None
        curr = input_el
        for _ in range(10):
            try:
                curr = curr.find_element(By.XPATH, "..")
                id_attr = curr.get_attribute("id") or ""
                class_attr = curr.get_attribute("class") or ""
                tag_name = curr.tag_name.lower()
                
                if "_item-" in id_attr or "_group-" in id_attr:
                    option_container = curr
                    break
                if tag_name == "label":
                    option_container = curr
                    break  # Break on label as it represents the card
                if "rounded" in class_attr or "border" in class_attr or "overflow-hidden" in class_attr:
                    option_container = curr
                    break
            except Exception:
                break
        
        if not option_container:
            option_container = input_el.find_element(By.XPATH, "..")

        if not option_container.is_displayed():
            return None

        # 2. Extract Option Name
        name = input_el.get_attribute("aria-label") or ""
        if not name:
            try:
                img = option_container.find_element(By.TAG_NAME, "img")
                name = img.get_attribute("alt") or ""
            except Exception:
                pass
        if not name:
            try:
                # Fall back to info icon dialog label if present
                info_a = option_container.find_element(By.CSS_SELECTOR, "a[aria-label][aria-haspopup='dialog']")
                raw = info_a.get_attribute("aria-label") or ""
                candidate = re.sub(r"^Show more information about\s+", "", raw).strip()
                if candidate:
                    name = candidate
            except Exception:
                pass
        if not name:
            try:
                text_content = option_container.text.strip()
                lines = [l.strip() for l in text_content.split("\n") if l.strip()]
                for line in lines:
                    if not re.search(r'\$[\d,]+', line) and not re.match(r'^(from|standard|no charge)', line, re.I):
                        name = line
                        break
            except Exception:
                pass
        if not name:
            name = input_el.get_attribute("value") or ""

        # Cleanup name
        name = re.sub(r'\$[\d,]+.*$', '', name).strip()
        name = re.sub(r'\s+', ' ', name).strip()

        # Reject placeholder/empty names
        if not name or name.lower() in ("option", "unnamed option", "unknown") or len(name) < 2 or name.startswith("Option_"):
            return None

        # 3. Extract Price (STRICTLY within option_container or its parent wrapper)
        price = ""
        try:
            price = get_card_price(option_container)
            if not price:
                try:
                    parent_el = option_container.find_element(By.XPATH, "..")
                    price = get_card_price(parent_el)
                except Exception:
                    pass
        except Exception:
            pass

        if price == "$0":
            price = ""


        # 4. Selection State
        chk = input_el.get_attribute("checked")
        is_selected = input_el.is_selected() or (chk is not None and chk.lower() not in ("false", ""))
        if not is_selected:
            try:
                cls = option_container.get_attribute("class") or ""
                if "border-primary" in cls and "hover:border-primary" not in cls:
                    is_selected = True
            except Exception:
                pass

        # 5. Swatch Image / Colors
        swatch_image = ""
        swatch_colors = []
        
        swatch_data = extract_swatch_style(input_el)
        swatch_image = swatch_data["swatch_image"]
        swatch_colors = swatch_data["swatch_colors"]

        if not swatch_image:
            try:
                img = option_container.find_element(By.TAG_NAME, "img")
                src = img.get_attribute("src") or ""
                if src and not src.startswith("data:"):
                    swatch_image = "https://configurator.porsche.com" + src if src.startswith("/") else src
            except Exception:
                pass

        # 6. Click to Capture Image (Exterior only)
        car_image = ""
        click_target = option_container if option_container.tag_name.lower() == "label" else input_el
        is_exterior = "exterior" in str(container_el.get_attribute("id")).lower()
        if is_exterior and click_target and click_target.is_enabled():
            car_image = capture_image_on_click(driver, click_target, name)

        return {
            "name": name,
            "price": price,
            "swatch_image": swatch_image,
            "swatch_colors": swatch_colors,
            "car_image": car_image,
            "currently_selected": is_selected,
        }
    except Exception as e:
        log.debug(f"Error in scrape_option_by_input: {e}")
        return None


def scrape_best(driver, container_el):
    """Scrapes all checkbox and radio input options in the container, filtering duplicates and placeholder dummy options."""
    inputs = container_el.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
    if not inputs:
        # Fallback to finding clickable labels if no inputs are found
        options = []
        labels = container_el.find_elements(By.CSS_SELECTOR, "label[class*='cursor-pointer']")
        for idx, lbl in enumerate(labels):
            try:
                name = lbl.text.strip().split("\n")[0]
                name = re.sub(r"\$[\d,]+.*$", "", name).strip()
                if not name or name.startswith("Option_") or len(name) < 2:
                    continue
                price = extract_price_from_text(lbl.text)
                options.append({
                    "name": name,
                    "price": price if price != "$0" else "",
                    "swatch_image": "",
                    "swatch_colors": [],
                    "car_image": "",
                    "currently_selected": "border-primary" in (lbl.get_attribute("class") or ""),
                })
            except Exception:
                pass
        return options

    options = []
    seen_names = set()
    for idx, inp in enumerate(inputs):
        opt = scrape_option_by_input(driver, inp, container_el)
        if opt and opt["name"] and opt["name"] not in seen_names:
            seen_names.add(opt["name"])
            options.append(opt)
            log.info(
                "        ✓ [%d/%d] %-40s price=%-12s img=%s",
                len(options), len(inputs), opt["name"][:40], opt["price"] or "—",
                "✓" if opt["car_image"] else "✗",
            )
    return options


def scrape_swatch_options_exterior_only(driver, container_el):
    """Original swatch option scraper used only for exterior colors, preserving its perfect behavior there."""
    options = []
    color_inputs = container_el.find_elements(
        By.CSS_SELECTOR,
        "input[type='checkbox'][style*='background-image'], "
        "input[type='radio'][style*='background-image'], "
        "input[type='checkbox'][style*='background-color'], "
        "input[type='radio'][style*='background-color']",
    )
    if not color_inputs:
        return options
    log.info(f"        found {len(color_inputs)} swatch inputs (exterior)")
    for idx, input_el in enumerate(color_inputs):
        try:
            label = None
            input_id = input_el.get_attribute("id")
            if input_id:
                try:
                    label = container_el.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                except NoSuchElementException:
                    pass
            if not label:
                try:
                    label = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                except NoSuchElementException:
                    pass

            name = input_el.get_attribute("aria-label") or ""
            if not name and label:
                name = label.get_attribute("aria-label") or label.text.strip()
            if not name:
                name = input_el.get_attribute("value") or f"Option_{idx}"

            price = get_group_price(driver, input_el, container_el)
            if not price and label:
                price = extract_price_from_text(label.text)
            if price == "$0":
                price = ""
            if not price:
                price = driver.execute_script("""
                    var el = arguments[0];
                    var seen = new Set();
                    for(var i=0; i<10; i++) {
                        var elId = (el.id || '') + el.className;
                        if(seen.has(elId)) break;
                        seen.add(elId);
                        var txt = el.textContent || '';
                        var m = txt.match(/\\$[\\d,]+/);
                        if(m && m[0] !== '$0') return m[0];
                        el = el.parentElement;
                        if(!el) break;
                        var children = el.children;
                        for(var j=0; j<children.length; j++) {
                            var child = children[j];
                            if(child.tagName === 'BUTTON' && child.getAttribute('aria-controls')) {
                                var btnTxt = child.textContent || '';
                                var bm = btnTxt.match(/\\$[\\d,]+/);
                                if(bm && bm[0] !== '$0') return bm[0];
                            }
                        }
                    }
                    return null;
                """, label if label else input_el) or ""

            swatch_data = extract_swatch_style(input_el)
            is_selected = input_el.is_selected() or input_el.get_attribute("checked") == "true"

            car_image = ""
            click_target = label if label else input_el
            is_exterior = "exterior" in str(container_el.get_attribute("id")).lower()

            if is_exterior and click_target and click_target.is_enabled():
                car_image = capture_image_on_click(driver, click_target, name)

            options.append({
                "name": name,
                "price": price,
                "swatch_image": swatch_data["swatch_image"],
                "swatch_colors": swatch_data["swatch_colors"],
                "car_image": car_image,
                "currently_selected": is_selected,
            })
            log.info(
                "        ✓ [%d/%d] %-40s price=%-12s colors=%d img=%s",
                idx+1, len(color_inputs), name[:40], price or "—",
                len(swatch_data["swatch_colors"]),
                "✓" if car_image else "✗",
            )
        except Exception as e:
            log.debug(f"        error processing swatch {idx}: {e}")
    return options


# Backwards compatibility wrappers
def scrape_swatch_options(driver, container_el):
    container_id = str(container_el.get_attribute("id") or "").lower()
    if "exterior-color" in container_id or "exterior_color" in container_id:
        return scrape_swatch_options_exterior_only(driver, container_el)
    return scrape_best(driver, container_el)

def scrape_card_options(driver, container_el):
    return scrape_best(driver, container_el)

def scrape_wheel_items(driver, container_el):
    return scrape_best(driver, container_el)

def scrape_label_options(driver, container_el):
    return scrape_best(driver, container_el)




# ══════════════════════════════════════════════════════════════════════════════
#  DYNAMIC SUBCATEGORY DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
def discover_and_scrape_toggle_subcats(driver, container, section_label="section"):
    result = {}
    seen_toggle_ids = set()

    toggle_btns = container.find_elements(
        By.CSS_SELECTOR,
        "button[aria-controls$='-toggle-container']",
    )
    log.info(f"    [{section_label}] Found {len(toggle_btns)} toggle buttons")

    for btn in toggle_btns:
        controls = btn.get_attribute("aria-controls") or ""
        if not controls or controls in seen_toggle_ids:
            continue
        seen_toggle_ids.add(controls)

        lbl = btn.get_attribute("aria-label") or ""
        if not lbl:
            lbl = btn.text.strip().split("\n")[0].strip()
        if not lbl:
            try:
                lbl = btn.find_element(By.CSS_SELECTOR, "h3, h4, [class*='heading'], [class*='title']").text.strip()
            except NoSuchElementException:
                pass
        if not lbl:
            cat_id = controls.replace("-toggle-container", "")
            try:
                cat_div = container.find_element(By.ID, f"category-{cat_id}")
                lbl = cat_div.find_element(By.CSS_SELECTOR, "h3, h4, [class*='heading'], [class*='title']").text.strip()
            except NoSuchElementException:
                pass
        if not lbl:
            lbl = controls.replace("-toggle-container", "")

        # Clean up trailing option count digits
        lbl = re.sub(r'\s+\d+$', '', lbl).strip()
        key = slugify(lbl)
        log.info(f"      ── Toggle subcat: '{lbl}' (#{controls}) key='{key}' ──")

        try:
            toggle_el = driver.find_element(By.ID, controls)
        except NoSuchElementException:
            log.warning(f"      Toggle container #{controls} not found — skipping '{lbl}'")
            result[key] = []
            continue

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle_el)
        time.sleep(0.5)

        options = scrape_card_options(driver, toggle_el)
        if not options:
            options = scrape_wheel_items(driver, toggle_el)
        if not options:
            options = scrape_swatch_options(driver, toggle_el)
        if not options:
            options = scrape_label_options(driver, toggle_el)

        log.info(f"      → {len(options)} option(s) scraped for '{lbl}'")
        result[key] = options

    return result


def discover_and_scrape_inline_subcats(driver, container, section_label="section"):
    result = {}
    seen_keys = set()

    top_category_divs = container.find_elements(
        By.XPATH,
        ".//div[starts-with(@id,'category-') "
        "and not(contains(@id,'_group-')) "
        "and not(contains(@id,'_item-'))]",
    )

    for cat_div in top_category_divs:
        is_inside_toggle = driver.execute_script("""
            var el = arguments[0];
            while (el.parentElement) {
                el = el.parentElement;
                if ((el.id || '').endsWith('-toggle-container')) return true;
            }
            return false;
        """, cat_div)
        if is_inside_toggle:
            continue

        # Skip categories that use toggle buttons
        has_toggle_btn = bool(cat_div.find_elements(By.CSS_SELECTOR, "button[aria-controls]"))
        if has_toggle_btn:
            log.info(f"      Skipping toggle category in inline scraper: #{cat_div.get_attribute('id')}")
            continue

        cat_id_attr = cat_div.get_attribute("id")
        log.info(f"      Inspecting inline category: #{cat_id_attr}")

        flex_blocks = cat_div.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
        found_any = False

        for block in flex_blocks:
            heading = block.get_attribute("aria-label") or ""
            if not heading:
                try:
                    heading = block.find_element(By.CSS_SELECTOR, "h3, h4, [class*='heading'], [class*='title']").text.strip()
                except NoSuchElementException:
                    pass
            if not heading:
                try:
                    heading = block.find_element(By.XPATH, ".//*[self::h3 or self::h4]").text.strip()
                except NoSuchElementException:
                    pass
            if not heading:
                continue

            items = block.find_elements(
                By.CSS_SELECTOR,
                "input[type='checkbox'], input[type='radio'], div[id*='_item-']",
            )
            if not items:
                continue

            key = slugify(heading)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            found_any = True

            log.info(f"      ── Inline subcat: '{heading}' ({len(items)} items) key='{key}' ──")

            options = scrape_swatch_options(driver, block)
            if not options:
                options = scrape_card_options(driver, block)
            if not options:
                options = scrape_wheel_items(driver, block)
            if not options:
                options = scrape_label_options(driver, block)

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

        if not found_any:
            try:
                heading = cat_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except NoSuchElementException:
                heading = cat_id_attr or ""

            if heading:
                key = slugify(heading)
                if key not in seen_keys:
                    seen_keys.add(key)
                    log.info(f"      ── Inline cat (flat): '{heading}' key='{key}' ──")
                    options = scrape_best(driver, cat_div)
                    log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
                    result[key] = options

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  STRATEGY IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════
def strategy_flat(driver, container_id, section_key=""):
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
        time.sleep(1)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
        time.sleep(1)
        return scrape_best(driver, container)
    except TimeoutException:
        log.warning(f"    Container #{container_id} not found")
        return []


def strategy_flat_with_expand(driver, container_id, section_key=""):
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
        time.sleep(1)

        toggle_prices = {}
        toggle_btns = container.find_elements(By.CSS_SELECTOR, "button[aria-controls$='-toggle-container']")
        for tb in toggle_btns:
            tb_text = tb.text.strip()
            tb_price = extract_price_from_text(tb_text)
            controls = tb.get_attribute("aria-controls") or ""
            if tb_price and controls:
                toggle_prices[controls] = tb_price
                log.info("    Toggle price: '%s' → %s (for #%s)", tb_text[:40], tb_price, controls)

        log.info("    Expanding all nested sub-sections...")
        container = expand_all_toggle_buttons(driver, container, label=section_key)
        time.sleep(1.5)

        try:
            container = driver.find_element(By.ID, container_id)
        except Exception:
            pass

        if section_key == "exterior_colors":
            # For exterior colors, run the original scraping method exactly
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
            time.sleep(1)
            result = scrape_swatch_options_exterior_only(driver, container)

            if isinstance(result, list) and toggle_prices:
                for tcid, tc_price in toggle_prices.items():
                    try:
                        toggle_el = driver.find_element(By.ID, tcid)
                        if not toggle_el.is_displayed():
                            continue
                        for item in result:
                            if item.get("price") in (None, "", "$0"):
                                item["price"] = tc_price
                    except Exception:
                        pass
            return result

        # For all other flat sections, scrape inline and toggle sections individually to prevent price leakage
        result = []
        all_inputs = container.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
        inline_inputs = []
        for inp in all_inputs:
            is_inside_toggle = driver.execute_script("""
                var el = arguments[0];
                var main = arguments[1];
                while (el && el !== main) {
                    if ((el.id || '').endsWith('-toggle-container')) return true;
                    el = el.parentElement;
                }
                return false;
            """, inp, container)
            if not is_inside_toggle:
                inline_inputs.append(inp)

        seen_names = set()
        for inp in inline_inputs:
            opt = scrape_option_by_input(driver, inp, container)
            if opt and opt["name"] and opt["name"] not in seen_names:
                seen_names.add(opt["name"])
                result.append(opt)

        for tcid, tc_price in toggle_prices.items():
            try:
                toggle_el = driver.find_element(By.ID, tcid)
                if not toggle_el.is_displayed():
                    continue
                tc_inputs = toggle_el.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
                for inp in tc_inputs:
                    opt = scrape_option_by_input(driver, inp, toggle_el)
                    if opt and opt["name"] and opt["name"] not in seen_names:
                        seen_names.add(opt["name"])
                        if not opt.get("price") or opt["price"] == "$0":
                            opt["price"] = tc_price
                        result.append(opt)
            except Exception as e:
                log.debug(f"Error scraping toggle container {tcid}: {e}")

        if not result:
            result = scrape_best(driver, container)

        return result
    except TimeoutException:
        log.warning(f"    Container #{container_id} not found")
        return []




def strategy_toggle_subcats(driver, container_id, section_key=""):
    result = {}
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    log.info(f"    [{section_key}] Step 1: expanding all collapsed toggles...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    log.info(f"    [{section_key}] Step 2: scraping inline sub-categories...")
    inline_result = discover_and_scrape_inline_subcats(driver, container, section_label=section_key)
    result.update(inline_result)

    log.info(f"    [{section_key}] Step 3: scraping toggle sub-categories...")
    toggle_result = discover_and_scrape_toggle_subcats(driver, container, section_label=section_key)
    result.update(toggle_result)

    if not result:
        log.warning(f"    [{section_key}] No sub-categories found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  WHEELS STRATEGY  (fully rewritten)
# ══════════════════════════════════════════════════════════════════════════════
def _get_toggle_button_heading(driver, cat_div):
    """Extract heading text from a category-XXX div that uses a toggle button layout.

    The HTML pattern is:
      <div id="category-IRL" ...>
        <button aria-controls="IRL-toggle-container">
          ...
          <h3>Wheel Colors</h3>
          ...
        </button>
      </div>
    """
    try:
        btn = cat_div.find_element(By.CSS_SELECTOR, "button[aria-controls]")
        # Prefer h3 inside the button
        try:
            val = btn.find_element(By.CSS_SELECTOR, "h3, h4").text.strip()
            return re.sub(r'\s+\d+$', '', val).strip()
        except NoSuchElementException:
            pass
        # Fall back to button's own text (first non-empty line)
        raw = btn.text.strip()
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        # Strip price lines
        lines = [l for l in lines if not re.match(r'^from\s+\$', l, re.I) and not re.match(r'^\$[\d,]', l)]
        if lines:
            val = lines[0]
            return re.sub(r'\s+\d+$', '', val).strip()
    except NoSuchElementException:
        pass
    return ""


def _get_toggle_button_price(cat_div):
    """Extract the 'from $X' price shown on the toggle button (e.g. winter wheel set)."""
    try:
        btn = cat_div.find_element(By.CSS_SELECTOR, "button[aria-controls]")
        # Look for <p class="text-contrast-medium ..."><span>from $X</span></p>
        for sel in [
            "p.text-contrast-medium span",
            "p[class*='text-contrast'] span",
        ]:
            try:
                span = btn.find_element(By.CSS_SELECTOR, sel)
                price = extract_price_from_text(span.text)
                if price:
                    return price
            except NoSuchElementException:
                pass
        # Fallback: any $X in the button text
        return extract_price_from_text(btn.text)
    except NoSuchElementException:
        return ""


def strategy_wheels(driver, container_id, section_key="wheels"):
    """
    Wheel section layout (from live HTML):

    section-wheels-toggle-container
    ├── category-IRA          ← inline items, NO toggle button
    │   ├── flex-col "19\"/20\" Wheels"  → _item- divs (wheel designs)
    │   └── flex-col "20\"/21\" Wheels"  → _item- divs (wheel designs)
    ├── category-IRL          ← toggle button → IRL-toggle-container
    │   └── "Wheel Colors"    → swatch/card options inside toggle
    ├── category-IRZ          ← toggle button → IRZ-toggle-container
    │   └── "Wheel Accessories"
    ├── category-ABA          ← toggle button → ABA-toggle-container (or ABC)
    │   └── "Wheel sets"
    └── category-ABC          ← toggle button with "from $X" price
        └── "Add winter wheel-and-tyre set"

    Steps:
      1. Expand all toggle buttons so their containers are populated.
      2. Scrape category-IRA inline groups (wheel designs) by h3 heading.
      3. Scrape every other category-XXX that has a toggle button by
         reading the h3 from inside the button and scraping the toggle container.
    """
    result = {}
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    # ── Step 1: expand ALL toggle buttons so their containers are populated ──
    log.info(f"    [{section_key}] Step 1: expanding all toggle sub-sections...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    # Re-fetch after expansion
    try:
        container = driver.find_element(By.ID, container_id)
    except NoSuchElementException:
        pass

    # ── Step 2: find every top-level category-XXX div ──
    cat_divs = container.find_elements(
        By.XPATH,
        ".//div[starts-with(@id,'category-') "
        "and not(contains(@id,'_group-')) "
        "and not(contains(@id,'_item-'))]",
    )
    log.info(f"    [{section_key}] Found {len(cat_divs)} top-level category divs")

    for cat_div in cat_divs:
        cat_id = cat_div.get_attribute("id") or ""

        # Skip categories that are nested inside a toggle container
        is_inside_toggle = driver.execute_script("""
            var el = arguments[0];
            var main = arguments[1];
            while (el && el !== main) {
                if ((el.id || '').endsWith('-toggle-container')) return true;
                el = el.parentElement;
            }
            return false;
        """, cat_div, container)
        if is_inside_toggle:
            log.info(f"      Skipping nested category: #{cat_id}")
            continue

        # ── Determine if this category uses a toggle button ──
        has_toggle_btn = bool(cat_div.find_elements(By.CSS_SELECTOR, "button[aria-controls]"))

        if not has_toggle_btn:
            # ── Inline category (e.g. category-IRA with wheel design groups) ──
            log.info(f"      ── Inline category: #{cat_id} ──")
            _scrape_inline_wheel_category(driver, cat_div, result)
        else:
            # ── Toggle-button category (IRL, IRZ, ABA, ABC …) ──
            heading = _get_toggle_button_heading(driver, cat_div)
            if not heading:
                heading = cat_id.replace("category-", "")

            btn_price = _get_toggle_button_price(cat_div)
            key = slugify(heading)
            log.info(f"      ── Toggle category: '{heading}' (#{cat_id}) key='{key}' btn_price='{btn_price}' ──")

            # Locate the toggle container: aria-controls value on the button
            toggle_container_id = ""
            try:
                btn_el = cat_div.find_element(By.CSS_SELECTOR, "button[aria-controls]")
                toggle_container_id = btn_el.get_attribute("aria-controls") or ""
            except NoSuchElementException:
                pass

            options = []
            if toggle_container_id:
                try:
                    toggle_el = driver.find_element(By.ID, toggle_container_id)
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle_el)
                    time.sleep(0.5)

                    # Use the new robust unified option scraper
                    options = scrape_best(driver, toggle_el)


                    # If the items have no price but the button advertised one, apply it
                    if btn_price and options:
                        for opt in options:
                            if not opt.get("price"):
                                opt["price"] = btn_price

                except NoSuchElementException:
                    log.warning(f"      Toggle container #{toggle_container_id} not found")

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

    if not result:
        log.warning(f"    [{section_key}] Structured approach empty — flat fallback")
        result["all"] = scrape_best(driver, container)

    return result


def _scrape_inline_wheel_category(driver, cat_div, result):
    """Scrape an inline (non-toggle) wheel category like category-IRA.

    These contain multiple flex-col blocks, each with an h3 heading and
    a set of _item- divs (wheel design thumbnails).
    """
    seen_keys = set()

    flex_blocks = cat_div.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
    log.info(f"        Found {len(flex_blocks)} flex-col blocks in inline category")

    for block in flex_blocks:
        # Get heading — look for h3/h4 that is NOT inside a button
        heading = ""
        try:
            h_els = block.find_elements(By.CSS_SELECTOR, "h3, h4")
            for h in h_els:
                # Skip headings inside buttons (toggle headers)
                inside_btn = driver.execute_script(
                    "var el=arguments[0]; while(el){if(el.tagName==='BUTTON') return true; el=el.parentElement;} return false;",
                    h
                )
                if not inside_btn:
                    txt = h.text.strip()
                    if txt:
                        heading = txt
                        break
        except Exception:
            pass

        if not heading:
            continue

        key = slugify(heading)
        if key in seen_keys:
            continue

        # Collect _item- divs in this block (wheel design thumbnails)
        item_divs = block.find_elements(By.CSS_SELECTOR, "div[id*='_item-']")
        if not item_divs:
            # Try broader: label elements containing an img + checkbox
            item_divs = block.find_elements(
                By.CSS_SELECTOR, "label[class*='cursor-pointer'], div[class*='gap-fluid-xs']"
            )

        if not item_divs:
            log.info(f"        Skipping block '{heading}' — no items found")
            continue

        seen_keys.add(key)
        log.info(f"        ── Inline wheel group: '{heading}' ({len(item_divs)} items) key='{key}' ──")

        # Determine group price (shown in the flex-col header area, if any)
        group_price = ""
        for sel in ["p.text-contrast-medium span", "p[class*='text-contrast'] span",
                    "span[class*='price']", "span[class*='amount']"]:
            try:
                for el in block.find_elements(By.CSS_SELECTOR, sel):
                    p = extract_price_from_text(el.text)
                    if p:
                        group_price = p
                        break
                if group_price:
                    break
            except Exception:
                pass

        options = []
        for item_el in item_divs:
            opt = _extract_inline_wheel_item(driver, item_el, group_price)
            if opt:
                options.append(opt)
                log.info(
                    "          ✓  %-45s price=%-10s selected=%s",
                    opt["name"][:45], opt["price"] or "—", opt["currently_selected"]
                )

        # Fallback if _item- based extraction yielded nothing
        if not options:
            options = scrape_best(driver, block)

        # Apply group price to items missing a price
        if group_price and options:
            for opt in options:
                if not opt.get("price"):
                    opt["price"] = group_price

        log.info(f"        → {len(options)} options for '{heading}'")
        result[key] = options


def _extract_inline_wheel_item(driver, item_el, fallback_price=""):
    """Extract a single wheel design item from a div[id*='_item-'] or label element."""
    name = ""
    swatch_image = ""
    price = ""
    is_selected = False

    # Name: from img alt, then input aria-label, then aria-label on div
    try:
        img = item_el.find_element(By.CSS_SELECTOR, "img")
        name = img.get_attribute("alt") or ""
        src = img.get_attribute("src") or ""
        if src and not src.startswith("data:"):
            swatch_image = "https://configurator.porsche.com" + src if src.startswith("/") else src
    except NoSuchElementException:
        pass

    if not name:
        try:
            inp = item_el.find_element(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
            name = inp.get_attribute("aria-label") or ""
        except NoSuchElementException:
            pass

    if not name:
        name = item_el.get_attribute("aria-label") or ""

    if not name:
        return None

    # Price: check the item itself, then nearby p.text-contrast-medium
    price = get_card_price(item_el)

    # Selected state
    try:
        inp = item_el.find_element(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
        chk = inp.get_attribute("checked")
        is_selected = inp.is_selected() or (chk is not None and chk.lower() not in ("false", ""))
    except NoSuchElementException:
        pass

    # Check label border class for "selected" visual state (border-primary vs border-surface)
    if not is_selected:
        try:
            lbl = item_el.find_element(By.CSS_SELECTOR, "label")
            cls = lbl.get_attribute("class") or ""
            # border-primary without hover: indicates currently selected
            if "border-primary" in cls and "hover:border-primary" not in cls:
                is_selected = True
        except NoSuchElementException:
            pass

    return {
        "name": name,
        "price": price or fallback_price,
        "swatch_image": swatch_image,
        "swatch_colors": [],
        "car_image": "",
        "currently_selected": is_selected,
    }


def extract_wheel_item(driver, item_el, container, heading=""):
    """Extract a single wheel item's name, price, image, etc."""
    name = item_el.get_attribute("aria-label") or ""

    if not name:
        try:
            img = item_el.find_element(By.TAG_NAME, "img")
            name = img.get_attribute("alt") or ""
        except Exception:
            pass

    if not name:
        try:
            inp = item_el.find_element(By.CSS_SELECTOR, "input")
            name = inp.get_attribute("aria-label") or ""
        except Exception:
            pass

    if not name:
        name = f"Wheel_{heading}_{container.id}" if heading and container.id else f"Wheel_Option"

    swatch_image = ""
    try:
        img = item_el.find_element(By.TAG_NAME, "img")
        src = img.get_attribute("src") or ""
        if src and not src.startswith("data:"):
            swatch_image = "https://configurator.porsche.com" + src if src.startswith("/") else src
    except Exception:
        pass

    price = get_card_price(item_el)
    if not price:
        price = get_group_price(driver, item_el, container)

    is_selected = False
    try:
        inp = item_el.find_element(By.CSS_SELECTOR, "input")
        is_selected = inp.is_selected() or inp.get_attribute("checked") == "true"
    except Exception:
        pass

    log.info("        ✓  %-45s price=%-10s", name[:45], price or "\u2014")

    return {
        "name": name,
        "price": price,
        "swatch_image": swatch_image,
        "swatch_colors": [],
        "car_image": "",
        "currently_selected": is_selected,
    }


def find_price_in_container(driver, container, heading=""):
    """Search container for a price near the given heading text."""
    for price_sel in [
        "p.text-contrast-medium span",
        "p[class*='text-contrast'] span",
        "span[class*='price']",
        "span[class*='amount']",
        "[class*='price']",
    ]:
        try:
            for el in container.find_elements(By.CSS_SELECTOR, price_sel):
                p = extract_price_from_text(el.text)
                if p:
                    return p
        except Exception:
            pass
    try:
        for el in container.find_elements(By.XPATH, './/*[contains(text(), "$")]'):
            p = extract_price_from_text(el.text)
            if p:
                return p
    except Exception:
        pass
    return ""


def strategy_interior_colors(driver, container_id, section_key="interior_colors_and_material"):
    result = {}
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
    time.sleep(0.5)

    flex_blocks = container.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
    if not flex_blocks:
        flex_blocks = container.find_elements(By.XPATH,
            ".//div[.//h3 or .//h4 or .//*[@class and contains(@class, 'heading')]]")

    seen_keys = set()
    log.info(f"    [{section_key}] Found {len(flex_blocks)} blocks to inspect")

    for block in flex_blocks:
        heading = block.get_attribute("aria-label") or ""
        if not heading:
            try:
                heading = block.find_element(By.CSS_SELECTOR, "h3, h4, [class*='heading'], [class*='title']").text.strip()
            except NoSuchElementException:
                continue
        if not heading:
            continue

        key = slugify(heading)
        if key in seen_keys:
            continue

        swatch_inputs = block.find_elements(
            By.CSS_SELECTOR, "input[type='checkbox'][style], input[type='radio'][style]"
        )
        if not swatch_inputs:
            swatch_inputs = block.find_elements(
                By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']"
            )
        if not swatch_inputs:
            continue

        seen_keys.add(key)

        group_price = ""
        for sel in [
            "p.text-contrast-medium span",
            "p[class*='text-contrast'] span",
            "span[class*='price']",
            "span[class*='amount']",
            "[class*='price']",
            "[data-testid*='price']",
        ]:
            try:
                for el in block.find_elements(By.CSS_SELECTOR, sel):
                    p = extract_price_from_text(el.text)
                    if p:
                        group_price = p
                        break
                if group_price:
                    break
            except Exception:
                pass
        if not group_price:
            try:
                for el in block.find_elements(By.XPATH, './/*[contains(text(), "$")]'):
                    p = extract_price_from_text(el.text)
                    if p:
                        group_price = p
                        break
            except Exception:
                pass

        log.info(f"      ── Group: '{heading}' ({len(swatch_inputs)} swatches, price={group_price or '—'}) ──")

        options = []
        for idx, input_el in enumerate(swatch_inputs):
            try:
                name = input_el.get_attribute("aria-label") or ""
                if not name:
                    try:
                        ancestor_label = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                        name = ancestor_label.get_attribute("aria-label") or ancestor_label.text.strip()
                    except NoSuchElementException:
                        pass
                if not name:
                    name = input_el.get_attribute("value") or f"Option_{idx}"

                item_price = get_group_price(driver, input_el, block)
                if not item_price:
                    item_price = group_price
                if not item_price:
                    item_price = get_group_price(driver, input_el, container)

                swatch_data = extract_swatch_style(input_el)
                is_selected = (
                    input_el.is_selected() or input_el.get_attribute("checked") == "true"
                )

                click_target = None
                try:
                    click_target = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                except NoSuchElementException:
                    input_id = input_el.get_attribute("id") or ""
                    if input_id:
                        try:
                            click_target = container.find_element(
                                By.CSS_SELECTOR, f"label[for='{input_id}']"
                            )
                        except NoSuchElementException:
                            pass
                if not click_target:
                    click_target = input_el

                car_image = ""

                options.append({
                    "name": name,
                    "price": item_price,
                    "swatch_image": swatch_data["swatch_image"],
                    "swatch_colors": swatch_data["swatch_colors"],
                    "car_image": car_image,
                    "currently_selected": is_selected,
                })
                log.info(
                    "        ✓ [%d/%d] %-45s price=%-10s colors=%d",
                    idx+1, len(swatch_inputs), name[:45], item_price or "—",
                    len(swatch_data["swatch_colors"]),
                )
            except Exception as e:
                log.debug(f"        error processing swatch {idx} in '{heading}': {e}")

        log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
        result[key] = options

    if not result:
        log.warning(f"    [{section_key}] No groups found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    # Empty all prices for the interior colors and materials section (no $0)
    if isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        item["price"] = ""
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                item["price"] = ""

    return result


def strategy_interior(driver, container_id, section_key="interior"):
    result = {}
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    log.info(f"    [{section_key}] Expanding all sub-categories...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    # Also try toggle-based discovery as in toggle_subcats strategy
    toggle_result = discover_and_scrape_toggle_subcats(driver, container, section_label=section_key)
    if toggle_result:
        log.info(f"    [{section_key}] Found {len(toggle_result)} toggle sub-categories via toggle discovery")
        result.update(toggle_result)

    # Fall back to flat scrape per toggle container
    subcat_containers = container.find_elements(By.CSS_SELECTOR, "div[id$='-toggle-container']")
    log.info(f"    [{section_key}] Found {len(subcat_containers)} toggle containers")

    for subcat_container in subcat_containers:
        try:
            subcat_id = subcat_container.get_attribute("id")
            if not subcat_id or not subcat_id.endswith("-toggle-container"):
                continue
            base_id = subcat_id.replace("-toggle-container", "")

            heading = subcat_container.get_attribute("aria-label") or None
            if not heading:
                try:
                    category_div = container.find_element(By.CSS_SELECTOR, f"div[id='category-{base_id}']")
                    btn_el = category_div.find_element(By.CSS_SELECTOR, "button[aria-controls]")
                    heading = btn_el.text.strip().split("\n")[0].strip()
                except NoSuchElementException:
                    pass
            if not heading:
                try:
                    category_div = container.find_element(By.CSS_SELECTOR, f"div[id='category-{base_id}']")
                    heading = category_div.find_element(By.CSS_SELECTOR, "h3, h4, [class*='heading']").text.strip()
                except NoSuchElementException:
                    pass
            if not heading:
                try:
                    heading = subcat_container.find_element(By.XPATH, "./preceding::h3[1] or ./preceding::h4[1]").text.strip()
                except NoSuchElementException:
                    pass
            if not heading:
                heading = base_id

            heading = re.sub(r'\s+\d+$', '', heading).strip()
            key = slugify(heading)
            if key in result:
                continue

            log.info(f"      ── Sub-category: '{heading}' (#{subcat_id}) key='{key}' ──")

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", subcat_container)
            time.sleep(0.5)

            options = scrape_card_options(driver, subcat_container)
            if not options:
                options = scrape_swatch_options(driver, subcat_container)
            if not options:
                options = scrape_best(driver, subcat_container)

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

        except Exception as e:
            log.debug(f"      Error processing sub-category: {e}")
            continue

    if not result:
        log.warning(f"    [{section_key}] No sub-categories found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════
STRATEGY_MAP = {
    "flat":               strategy_flat,
    "flat_with_expand":   strategy_flat_with_expand,
    "toggle_subcats":     strategy_toggle_subcats,
    "wheels":             strategy_wheels,
    "interior_colors":    strategy_interior_colors,
    "interior":           strategy_interior,
}


def expand_section(driver, testid):
    try:
        btn = WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"button[data-testid='{testid}']"))
        )
        if btn.get_attribute("aria-expanded") != "true":
            safe_click(driver, btn)
            time.sleep(2.5)
        log.info("  [✓ open] %s", testid)
        return True
    except TimeoutException:
        log.warning("  [✗ miss] %s – button not found", testid)
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  TRIM SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def scrape_trim(driver, trim):
    log.info("━" * 60)
    log.info("Loading: %s", trim["link"])
    driver.get(trim["link"])
    time.sleep(5)
    dismiss_overlays(driver)
    time.sleep(2)

    base_price = scrape_base_price_from_page(driver)
    log.info("Base price from page: %s", base_price or "not found")

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "button[data-testid='section-section-exterior-color-button']")
            )
        )
        log.info("Page is ready ✓  |  Title: %s", driver.title)
    except TimeoutException:
        log.warning("Timeout waiting for section buttons – proceeding anyway")

    categories = {}

    for section in SECTIONS:
        key          = section["key"]
        testid       = section["btn_testid"]
        container_id = section["container_id"]
        strategy     = section.get("strategy", "flat")

        log.info("")
        log.info("  ── Section: %s  (strategy: %s) ──", key.upper(), strategy)

        opened = expand_section(driver, testid)
        if not opened:
            categories[key] = {} if strategy != "flat" else []
            continue

        scraper_fn = STRATEGY_MAP.get(strategy, strategy_flat)
        categories[key] = scraper_fn(driver, container_id, section_key=key)

    hero_image = get_hero_image(driver)

    return {
        "name":       trim["name"],
        "base_price": base_price if base_price else trim.get("price", ""),
        "base_image": hero_image if hero_image else trim.get("image", ""),
        "url":        trim["link"],
        "configurations": [{"configuration_name": "Default Configuration", "categories": categories}],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CSV CONVERTER (integrated)
# ══════════════════════════════════════════════════════════════════════════════
def convert_to_csv(data, output_file):
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
            trim_base_price = trim.get("base_price", "")

            if trim_base_price and str(trim_base_price).lower() not in ["null", "none", ""]:
                if not str(trim_base_price).startswith("$"):
                    trim_base_price = f"${trim_base_price}"
            else:
                trim_base_price = ""

            for config in trim.get("configurations", []):
                categories = config.get("categories", {})

                for section_key, section_value in categories.items():
                    if isinstance(section_value, list):
                        for item in section_value:
                            if isinstance(item, dict):
                                price = item.get("price", "")
                                if price and str(price).lower() in ["null", "none", ""]:
                                    price = ""
                                car_image = item.get("car_image", "")
                                swatch_image = item.get("swatch_image", "")
                                display_image = car_image if car_image else swatch_image
                                all_rows.append({
                                    "car": car_name,
                                    "model": trim_name,
                                    "base price of car": trim_base_price,
                                    "type": section_key,
                                    "category": section_key,
                                    "sub category": item.get("name", ""),
                                    "multi allowed": "",
                                    "description": "",
                                    "car model image": car_base_image,
                                    "trim image": trim_base_image,
                                    "price": price,
                                    "car image": car_image,
                                    "currently selected": "yes" if item.get("currently_selected") else "no",
                                    "image": display_image,
                                })

                    elif isinstance(section_value, dict):
                        for subsection_key, subsection_value in section_value.items():
                            if isinstance(subsection_value, list):
                                for item in subsection_value:
                                    if isinstance(item, dict):
                                        price = item.get("price", "")
                                        if price and str(price).lower() in ["null", "none", ""]:
                                            price = ""
                                        car_image = item.get("car_image", "")
                                        swatch_image = item.get("swatch_image", "")
                                        display_image = car_image if car_image else swatch_image
                                        all_rows.append({
                                            "car": car_name,
                                            "model": trim_name,
                                            "base price of car": trim_base_price,
                                            "type": section_key,
                                            "category": subsection_key,
                                            "sub category": item.get("name", ""),
                                            "multi allowed": "",
                                            "description": "",
                                            "car model image": car_base_image,
                                            "trim image": trim_base_image,
                                            "price": price,
                                            "car image": car_image,
                                            "currently selected": "yes" if item.get("currently_selected") else "no",
                                            "image": display_image,
                                        })

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    log.info("CSV saved → %s (%d rows)", output_file, len(all_rows))
    return all_rows


# ══════════════════════════════════════════════════════════════════════════════
#  DYNAMIC MODEL/TRIM DISCOVERY (from website)
# ══════════════════════════════════════════════════════════════════════════════
def discover_trims_from_website(driver):
    """Visit the Porsche models page and try to discover all models and trims."""
    log.info("═" * 60)
    log.info("Attempting dynamic discovery of models/trims from website...")
    log.info("═" * 60)

    discovered = {}
    models_url = "https://models.porsche.com/en-US/model-start"

    try:
        driver.get(models_url)
        time.sleep(5)
        dismiss_overlays(driver)
        time.sleep(3)

        log.info("Models page loaded: %s", driver.title)

        model_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/model-start/']")
        log.info("Found %d potential model links", len(model_links))

        model_names = set()
        for link in model_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()

            for model in ["718", "911", "Taycan", "Panamera", "Macan", "Cayenne"]:
                if model.lower() in href.lower() or model.lower() in text.lower():
                    model_names.add(model)

        log.info("Discovered model names: %s", sorted(model_names))

        for model_name in sorted(model_names):
            model_slug = model_name.lower().replace(" ", "-")
            model_page_url = f"https://models.porsche.com/en-US/model-start/{model_slug}"
            log.info("  Visiting %s...", model_page_url)

            try:
                driver.get(model_page_url)
                time.sleep(5)

                page_text = driver.find_element(By.TAG_NAME, "body").text

                configurator_links = driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[href*='configurator.porsche.com'], a[href*='mode/model/']"
                )

                trim_data = []
                seen_codes = set()

                for cl in configurator_links:
                    href = cl.get_attribute("href") or ""

                    code_match = re.search(r'/mode/model/([A-Za-z0-9]{5,8})', href)
                    if code_match:
                        code = code_match.group(1)
                        if code not in seen_codes:
                            seen_codes.add(code)

                            parent_text = ""
                            try:
                                parent_text = cl.find_element(By.XPATH, "..").text.strip()
                            except Exception:
                                parent_text = cl.text.strip()

                            trim_name = parent_text or f"{model_name} {code}"
                            trim_name = re.sub(r'\$[\d,]+.*$', '', trim_name).strip()
                            trim_name = re.sub(r'\s+', ' ', trim_name).strip()

                            log.info("    Found trim: '%s' → code=%s", trim_name[:50], code)
                            trim_data.append((trim_name, code))

                if trim_data:
                    discovered[model_name] = {"trims": trim_data}
                else:
                    log.warning("    No trims discovered for %s via links, trying image URL parsing...", model_name)

                    page_source = driver.page_source
                    img_codes = set(re.findall(r'/iod/image/US/([A-Za-z0-9]{5,8})/', page_source))

                    from selenium.webdriver.common.by import By
                    heading_els = driver.find_elements(By.CSS_SELECTOR, "h2, h3, [class*='heading']")
                    headings = [h.text.strip() for h in heading_els if h.text.strip()]

                    if img_codes and headings:
                        for i, code in enumerate(sorted(img_codes)):
                            trim_name = headings[i] if i < len(headings) else f"{model_name} {code}"
                            trim_data.append((trim_name, code))
                            log.info("    Found trim (img): '%s' → code=%s", trim_name[:50], code)
                        discovered[model_name] = {"trims": trim_data}

            except Exception as e:
                log.error("  Error discovering trims for %s: %s", model_name, e)

        # Merge with hardcoded data: discovered takes priority, hardcoded fills gaps
        merged = {}
        for model_name, model_data in MODEL_TRIMS.items():
            merged[model_name] = model_data

        for model_name, model_data in discovered.items():
            if model_name in merged:
                existing_codes = {c for _, c in merged[model_name]["trims"]}
                for trim_name, code in model_data["trims"]:
                    if code not in existing_codes:
                        merged[model_name]["trims"].append((trim_name, code))
                        log.info("  Added discovered trim: %s → %s", trim_name, code)
            else:
                merged[model_name] = model_data
                log.info("  Added discovered model: %s", model_name)

        log.info("Dynamic discovery complete. Final model count: %d", len(merged))
        return merged

    except Exception as e:
        log.error("Dynamic discovery failed: %s", e)
        log.info("Falling back to hardcoded model/trim data")
        return MODEL_TRIMS


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ultimate Porsche Configurator Scraper")
    parser.add_argument("--discover", action="store_true",
                        help="Dynamically discover models/trims from website (slow)")
    parser.add_argument("--models", nargs="*",
                        help="Only scrape specific models, e.g. --models 911 Taycan")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run in headless mode (default: True)")
    parser.add_argument("--output-dir", default=".",
                        help="Output directory for JSON/CSV files")
    parser.add_argument("--max-trims", type=int, default=0,
                        help="Max trims per model to scrape (0 = all)")
    parser.add_argument("--fast", action="store_true",
                        help="Fast mode: shorter waits, fewer image captures (max 3 per trim)")
    args = parser.parse_args()

    global _FAST_MODE, MAX_IMAGE_CAPTURES
    if args.fast:
        _FAST_MODE = True
        MAX_IMAGE_CAPTURES = 3
        log.info("FAST MODE enabled — shorter waits, max 3 image captures per trim")

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    driver = build_driver(headless=args.headless)
    all_models = []

    try:
        # Determine model/trim data
        model_data_source = MODEL_TRIMS
        if args.discover:
            model_data_source = discover_trims_from_website(driver)

        # Filter by requested models if specified
        if args.models:
            filtered = {}
            for m in args.models:
                if m in model_data_source:
                    filtered[m] = model_data_source[m]
                else:
                    log.warning("Unknown model: %s (available: %s)", m, list(model_data_source.keys()))
            model_data_source = filtered

        log.info("\n" + "=" * 60)
        log.info("  STARTING SCRAPE — %d models, %d total trims",
                 len(model_data_source),
                 sum(len(m["trims"]) for m in model_data_source.values()))
        log.info("=" * 60)

        for model_name, model_data in model_data_source.items():
            trims = model_data["trims"]
            if args.max_trims > 0:
                trims = trims[:args.max_trims]

            log.info("\n" + "═" * 60)
            log.info("  MODEL: %s (%d trims)", model_name, len(trims))
            log.info("═" * 60)

            scraped_trims = []
            for trim_idx, (trim_name, trim_code) in enumerate(trims):
                configurator_url = f"https://configurator.porsche.com/en-US/mode/model/{trim_code}"

                trim = {
                    "name": trim_name,
                    "code": trim_code,
                    "link": configurator_url,
                }

                global _image_captures_done
                _image_captures_done = 0
                try:
                    log.info("\n  [%d/%d] Scraping: %s", trim_idx + 1, len(trims), trim_name)
                    scraped = scrape_trim(driver, trim)

                    cats = scraped["configurations"][0]["categories"]
                    total = 0
                    for cat_name, cat_val in cats.items():
                        if isinstance(cat_val, dict):
                            for sub_key, sub_val in cat_val.items():
                                c = len(sub_val) if isinstance(sub_val, list) else 0
                                total += c
                        else:
                            total += len(cat_val)
                    log.info("  Trim '%s' scraped ✓ — %d total options", trim_name, total)

                    scraped_trims.append(scraped)

                    trim_slug = re.sub(r'[^a-z0-9]+', '_', trim_name.lower()).strip('_')
                    model_slug = re.sub(r'[^a-z0-9]+', '_', model_name.lower()).strip('_')
                    trim_file = os.path.join(output_dir, f"{model_slug}__{trim_slug}.json")
                    with open(trim_file, "w", encoding="utf-8") as tf:
                        json.dump(scraped, tf, indent=2, ensure_ascii=False)
                    log.info("  Saved → %s", trim_file)

                except Exception as exc:
                    log.error("Failed to scrape trim '%s': %s", trim_name, exc)
                    import traceback
                    traceback.print_exc()
                    scraped_trims.append({
                        "name": trim_name,
                        "base_price": "",
                        "base_image": "",
                        "url": configurator_url,
                        "error": str(exc),
                        "configurations": [{"configuration_name": "Default Configuration", "categories": {}}],
                    })

            all_models.append({
                "name": model_name,
                "trims": scraped_trims,
            })

    finally:
        driver.quit()

    combined_file = os.path.join(output_dir, "porsche_data.json")
    with open(combined_file, "w", encoding="utf-8") as fh:
        json.dump(all_models, fh, indent=2, ensure_ascii=False)
    log.info("Combined JSON saved → %s", combined_file)

    csv_file = os.path.join(output_dir, "porsche_output.csv")
    csv_rows = convert_to_csv(all_models, csv_file)

    log.info("\n" + "=" * 60)
    log.info("  SCRAPE COMPLETE — %d models, %d trims", len(all_models),
             sum(len(m["trims"]) for m in all_models))
    log.info("=" * 60)
    for m in all_models:
        price = m["trims"][0].get("base_price", "") if m["trims"] else ""
        log.info("  %-12s  %3d trims  (e.g. %s %s)",
                 m["name"], len(m["trims"]),
                 m["trims"][0]["name"] if m["trims"] else "—",
                 price if price else "")
    log.info("")
    log.info("Files:  JSON → %s", combined_file)
    log.info("        CSV  → %s", csv_file)
    log.info("        Per-trim JSON files in: %s", output_dir)


if __name__ == "__main__":
    main()