import json
import time
import base64
import re
import cloudinary
import cloudinary.uploader
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class McLarenScraper:
    def __init__(self):
        """Initialize the McLaren scraper"""
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        self.data = []
        self.output_file = "mclaren_car_data.json"
        self.current_model = None  # Track current model being processed

        # Configure Cloudinary
        cloudinary.config(
            cloud_name="dsmkxcczo",
            api_key="395956489484953",
            api_secret="rMIXWeYnZI7-ir834KFjEpf0dWI",
            secure=True
        )
        
        # Model-specific configurations
        self.model_config = {
            "GTS": {
                # Color Section
                "exterior_colors": True,
                
                # Wheels & Brakes Section
                "wheels_id": "edit-CH_P22_WHEELS",
                "brakes_id": "edit-CH_P22_BRAKE_CALIPERS",
                "wheel_bolts_id": "edit-CH_P22_TITAN_LOCKBOLT_CBOX",
                "wheel_finish_id": "edit-CH_P22_WHEEL_FINISH",
                
                # Exterior Section
                "bright_pack_id": "edit-CH_P22_MSO_BRIGHT_PK_CBOX",
                "exterior_details_id": "edit-CH_P22_CF_EXTDET_PK_CBOX",
                "underbody_carbon_id": "edit-CH_P22_CF_UNDBOD_PK_CBOX",
                "stealth_badge_pack_id": "edit-CH_P22_STEALTH_BADGE_CBOX",
                "gts_side_badge_id": "edit-CH_P22_GTS_SIDE_BADGE",
                "roof_id": "edit-CH_P22_ROOF",
                "privacy_glass_id": "edit-CH_P22_PRIVACY_GLASS_CBOX",
                "exhaust_type_id": "edit-CH_P22_EXHAUST",
                "exhaust_finisher_id": "edit-CH_P22_EXHAUST_FINISHER",
                
                # Interior Specification Section
                "interior_theme_id": "edit-CH_P22_TRIM_01",
                
                # Interior Section
                "interior_color_id": "edit-CH_P22_INT_THEME",
                "contrast_stitch_id": "edit-CH_P22_CON_STITCH",
                "steering_wheel_id": "edit-CH_P22_STEERING_WHL",
                "seat_belts_id": "edit-CH_P22_SEAT_BELT",
                "seat_back_id": "edit-CH_P22_SEAT_BACK",
                "sill_finishers_id": "edit-CH_P22_SILL_TRIM",
                "luggage_bay_floor_id": "edit-CH_P22_TOUR_DECK",
                "luggage_strap_id": "edit-CH_P22_LUG_RETAIN_CBOX",
                "armrest_id": "edit-CH_P22_P29_EMBOSS_AR_CBOX",
                "track_plaque_id": "edit-CH_P22_CONSTRUCTOR_PLAQUE_CBOX",
                "interior_carbon_pack_id": "edit-CH_P22_CF_INTDET_PK_CBOX",
                
                # Option Packs Section
                "practicality_pack_id": "edit-CH_P22_PRAC_PK_CBOX",
                "premium_pack_id": "edit-CH_P22_PREMIUM_PK_CBOX",
                "machined_aluminium_pack_id": "edit-CH_P22_PREC_MACH_AL_PK_CBOX",
                
                # Options Section
                "vehicle_lift_id": "edit-CH_P22_VEH_LIFT_CBOX",
                "alarm_upgrade_id": "edit-CH_P22_VOL_ALARM_CBOX",
                "tracking_system_id": "edit-CH_P22_TK_SYS_CBOX",
                "battery_charger_id": "edit-CH_P22_LI_ION_CHGR_CBOX",
                "warning_triangle_id": "edit-CH_P22_WARN_TRI_CBOX",
                "fire_extinguisher_id": "edit-CH_P22_EXTING_CBOX",
                "car_cover_id": "edit-CH_P22_BRAND_COVER_CBOX",
                "ashtray_id": "edit-CH_P22_ASHTRAY_CBOX",
                "painted_key_id": "edit-CH_P22_PAINTED_KEY_CBOX",
                "printed_handbook_id": "edit-CH_P22_PRINT_HB_CBOX",
                "owners_manual_id": "edit-CH_GEN_MANUAL_LNG",
                "system_language_id": "edit-CH_GEN_SYS_LNG"
            },
            "ARTURA": {
                # Color Section
                "exterior_colors": True,
                
                # Wheels & Brakes Section
                "wheels_id": "edit-CH_P16_WHL_TYPE",
                "brakes_id": "edit-CH_P16_BRAKE_CLR",
                "tyre_type_id": "edit-CH_P16_TYRE_TYPE",
                "wheel_bolts_id": "edit-CH_P16_TITAN_LOCKBOLT_CBOX",
                "wheel_finish_id": "edit-CH_P16_WHL_FIN",
                
                # Exterior Section
                "bright_pack_id": "edit-CH_P16_MSO_BRIGHT_PK_CBOX",
                "stealth_badge_pack_id": "edit-CH_P16_STEALTH_BADGE_CBOX",
                "underbody_carbon_id": "edit-CH_P16_MSO_CF_PK1_CBOX",
                "exterior_details_id": "edit-CH_P16_MSO_CF_PK2_CBOX",
                "mirror_casings_id": "edit-CH_P16_MIRROR_CASING",
                "front_fender_louvres_id": "edit-CH_P16_FR_FENDER",
                "exhaust_type_id": "edit-CH_P16_EXHAUST",
                "exhaust_hot_vee_finishers_id": "edit-CH_P16_EXHAUST_FINISHER",
                "roof_id": "edit-CH_P16_ROOF",
                "engine_cover_id": "edit-CH_P16_ENG_BEAUT",
                "thermal_windscreen_id": "edit-CH_P16_THERM_WINDSCREEN_CBOX",
                "rear_spoiler_id": "edit-CH_P16_MSO_CF_SPOILER_CBOX",
                
                # Interior Specification Section
                "interior_theme_id": "edit-CH_P16_TRIM",
                
                # Interior Section
                "interior_color_id": "edit-CH_P16_INTERIOR",
                "gloss_black_finish_id": "edit-CH_P16_BLK_INT_FIN_PK_CBOX",
                "interior_carbon_pack_id": "edit-CH_P16_CF_INTERIOR_PK_CBOX",
                "seat_type_id": "edit-CH_P16_SEAT_TYPE",
                "seat_belts_id": "edit-CH_P16_BELT",
                "harness_bar_id": "edit-CH_P16_HARNESS_BAR_CBOX",
                "steering_wheel_type_id": "edit-CH_P16_STR_WHL_TYPE",
                "steering_wheel_grip_id": "edit-CH_P16_STR_WHL_GRIP",
                "sill_finishers_id": "edit-CH_P16_SILL_FIN",
                "floor_mats_id": "edit-CH_P16_DROPIN_MAT_EDGE",
                "armrest_id": "edit-CH_P16_EMBOSS_AR_CBOX",
                "track_plaque_id": "edit-CH_P16_CONSTRUCTOR_PLAQUE_CBOX",
                
                # Entertainment Section
                "audio_id": "edit-CH_P16_AUDIO",
                
                # Option Packs Section
                "practicality_pack_id": "edit-CH_P16_PRAC_PK_CBOX",
                "technology_pack_id": "edit-CH_P16_TECH_PK_CBOX",
                "driving_assistant_pack_id": "edit-CH_P16_DRIVING_ASSISTANT_PK_CBOX",
                
                # Options Section
                "vehicle_lift_id": "edit-CH_P16_VEH_LIFT_CBOX",
                "alarm_upgrade_id": "edit-CH_P16_VOL_ALARM_CBOX",
                "tracking_system_id": "edit-CH_P16_TK_SYS_CBOX",
                "warning_triangle_id": "edit-CH_P16_WARN_TRI_CBOX",
                "fire_extinguisher_id": "edit-CH_P16_EXTING_CBOX",
                "car_cover_id": "edit-CH_P16_BRAND_COVER_CBOX",
                "ashtray_id": "edit-CH_P16_ASHTRAY_CBOX",
                "painted_key_id": "edit-CH_P16_PAINTED_KEY_CBOX",
                "printed_handbook_id": "edit-CH_P16_PRINT_HB_CBOX",
                "owners_manual_id": "edit-CH_GEN_MANUAL_LNG",
                "system_language_id": "edit-CH_GEN_SYS_LNG"
            },
            "ARTURA SPIDER": {
                # Color Section
                "exterior_colors": True,
                
                # Wheels & Brakes Section
                "wheels_id": "edit-CH_P16_WHL_TYPE",
                "brakes_id": "edit-CH_P16_BRAKE_CLR",
                "tyre_type_id": "edit-CH_P16_TYRE_TYPE",
                "wheel_bolts_id": "edit-CH_P16_TITAN_LOCKBOLT_CBOX",
                "wheel_finish_id": "edit-CH_P16_WHL_FIN",
                
                # Exterior Section
                "bright_pack_id": "edit-CH_P16_MSO_BRIGHT_PK_CBOX",
                "stealth_badge_pack_id": "edit-CH_P16_STEALTH_BADGE_CBOX",
                "underbody_carbon_id": "edit-CH_P16_MSO_CF_PK1_CBOX",
                "exterior_details_id": "edit-CH_P16_MSO_CF_PK2_CBOX",
                "mirror_casings_id": "edit-CH_P16_MIRROR_CASING",
                "front_fender_louvres_id": "edit-CH_P16_FR_FENDER",
                "tonneau_id": "edit-CH_P16_TONNEAU",
                "exhaust_type_id": "edit-CH_P16_EXHAUST",
                "exhaust_hot_vee_finishers_id": "edit-CH_P16_EXHAUST_FINISHER",
                "roof_id": "edit-CH_P16_ROOF",
                "thermal_windscreen_id": "edit-CH_P16_THERM_WINDSCREEN_CBOX",
                "rear_spoiler_id": "edit-CH_P16_MSO_CF_SPOILER_CBOX",
                
                # Interior Specification Section
                "interior_theme_id": "edit-CH_P16_TRIM",
                
                # Interior Section
                "interior_color_id": "edit-CH_P16_INTERIOR",
                "gloss_black_finish_id": "edit-CH_P16_BLK_INT_FIN_PK_CBOX",
                "interior_carbon_pack_id": "edit-CH_P16_CF_INTERIOR_PK_CBOX",
                "seat_type_id": "edit-CH_P16_SEAT_TYPE",
                "seat_belts_id": "edit-CH_P16_BELT",
                "steering_wheel_type_id": "edit-CH_P16_STR_WHL_TYPE",
                "steering_wheel_grip_id": "edit-CH_P16_STR_WHL_GRIP",
                "sill_finishers_id": "edit-CH_P16_SILL_FIN",
                "floor_mats_id": "edit-CH_P16_DROPIN_MAT_EDGE",
                "armrest_id": "edit-CH_P16_EMBOSS_AR_CBOX",
                "track_plaque_id": "edit-CH_P16_CONSTRUCTOR_PLAQUE_CBOX",
                
                # Entertainment Section
                "audio_id": "edit-CH_P16_AUDIO",
                
                # Option Packs Section
                "practicality_pack_id": "edit-CH_P16_PRAC_PK_CBOX",
                "technology_pack_id": "edit-CH_P16_TECH_PK_CBOX",
                "driving_assistant_pack_id": "edit-CH_P16_DRIVING_ASSISTANT_PK_CBOX",
                
                # Options Section
                "vehicle_lift_id": "edit-CH_P16_VEH_LIFT_CBOX",
                "alarm_upgrade_id": "edit-CH_P16_VOL_ALARM_CBOX",
                "tracking_system_id": "edit-CH_P16_TK_SYS_CBOX",
                "warning_triangle_id": "edit-CH_P16_WARN_TRI_CBOX",
                "fire_extinguisher_id": "edit-CH_P16_EXTING_CBOX",
                "car_cover_id": "edit-CH_P16_BRAND_COVER_CBOX",
                "ashtray_id": "edit-CH_P16_ASHTRAY_CBOX",
                "painted_key_id": "edit-CH_P16_PAINTED_KEY_CBOX",
                "printed_handbook_id": "edit-CH_P16_PRINT_HB_CBOX",
                "owners_manual_id": "edit-CH_GEN_MANUAL_LNG",
                "system_language_id": "edit-CH_GEN_SYS_LNG"
            },
            "750S": {
                # Color Section
                "exterior_colors": True,
                
                # Wheels & Brakes Section
                "wheels_id": "edit-CH_P28_WHL_STYLE",
                "brakes_id": "edit-CH_P14_BRAKE_CLR",
                "tyre_type_id": "edit-CH_P14_TYRE_TYPE",
                "wheel_bolts_id": "edit-CH_P28_TITANIUM_BOLT_CBOX",
                "wheel_finish_id": "edit-CH_P28_WHL_FIN",
                "track_brake_upgrade_id": "edit-CH_P28_PCCB_CBOX",
                
                # Exterior Section
                "black_pack_id": "edit-CH_P28_BLK_PCK_CBOX",
                "stealth_badge_pack_id": "edit-CH_P14_STEALTH_BADGE_CBOX",
                "underbody_carbon_pack_id": "edit-CH_P28_CF_UNDERBODY_PK_CBOX",
                "exterior_carbon_pack_id": "edit-CH_P28_CF_DETAIL_PK_CBOX",
                "upper_structure_carbon_pack_id": "edit-CH_P28_CF_UPR_COUPE_PK_CBOX",
                "hood_id": "edit-CH_P14_BONNET",
                "front_fender_id": "edit-CH_P28_FRONT_FENDER",
                "exhaust_finisher_id": "edit-CH_P28_EXH_FIN",
                "active_rear_spoiler_id": "edit-CH_P14_AIRBRAKE",
                "headlight_surround_id": "edit-CH_P28_HEADLIGHT_SUR",
                "rear_bumper_id": "edit-CH_P28_RR_BUMPER",
                "rear_bumper_ducts_id": "edit-CH_P28_REAR_BUMPER_INSERT",
                "window_surrounds_id": "edit-CH_P28_WINDOW_SURR_EXT",
                "sound_comfort_windscreen_id": "edit-CH_P28_SOUND_WINDSCREEN_CBOX",
                
                # Interior Specification Section
                "interior_theme_id": "edit-CH_P28_SPEC",
                
                # Interior Section
                "interior_color_id": "edit-CH_P14_INT_THEME",
                "seat_type_id": "edit-CH_P14_SEAT_STYLE",
                "passenger_seat_position_id": "edit-CH_P14_SEAT_POS",
                "seat_size_id": "edit-CH_P14_SEAT_SIZE",
                "seat_belts_id": "edit-CH_P14_SEAT_BELT",
                "steering_wheel_id": "edit-CH_P14_STEERING_WHL",
                "sill_finishers_id": "edit-CH_P14_SILL_TRIM_CLR",
                "double_glazed_engine_window_id": "edit-CH_P14_DBL_GLZ_ENG_WDW_CBOX",
                "floor_mats_id": "edit-CH_P14_PRACT_FLMAT_CBOX",
                "track_plaque_id": "edit-CH_P14_TRACK_PLAQUE_CBOX",
                
                # Entertainment Section
                "audio_id": "edit-CH_P14_AUDIO",
                
                # Safety & Security Section
                "vehicle_lift_id": "edit-CH_P28_VEH_LIFT_CBOX",
                "park_assist_360_id": "edit-CH_P14_PK_ASSIST_360_CBOX",
                "parking_sensors_id": "edit-CH_P14_FR_RR_PK_SENS_CBOX",
                "rear_camera_sensors_id": "edit-CH_P14_RR_VIEW_CAM_SENS_CBOX",
                "alarm_upgrade_id": "edit-CH_P14_VOL_ALARM_CBOX",
                "tracking_system_id": "edit-CH_P14_TK_SYS_CBOX",
                "homelink_id": "edit-CH_P14_HOMELINK_CBOX",
                
                # Practical Section
                "battery_charger_id": "edit-CH_P14_LI_ION_CHGR_CBOX",
                "warning_triangle_id": "edit-CH_P14_WARN_TRI_CBOX",
                "fire_extinguisher_id": "edit-CH_P14_EXTING_CBOX",
                "car_cover_id": "edit-CH_P14_BRAND_COVER_CBOX",
                "ashtray_id": "edit-CH_P14_ASHTRAY_CBOX",
                "painted_key_id": "edit-CH_P14_PAINTED_KEY_CBOX",
                "printed_handbook_id": "edit-CH_P14_PRINT_HB_CBOX",
                "owners_manual_id": "edit-CH_GEN_MANUAL_LNG",
                "system_language_id": "edit-CH_GEN_SYS_LNG"
            },
            "750S SPIDER": {
                # Color Section
                "exterior_colors": True,
                
                # Wheels & Brakes Section
                "wheels_id": "edit-CH_P28_WHL_STYLE",
                "brakes_id": "edit-CH_P14_BRAKE_CLR",
                "tyre_type_id": "edit-CH_P14_TYRE_TYPE",
                "wheel_bolts_id": "edit-CH_P28_TITANIUM_BOLT_CBOX",
                "wheel_finish_id": "edit-CH_P28_WHL_FIN",
                "track_brake_upgrade_id": "edit-CH_P28_PCCB_CBOX",
                
                # Exterior Section
                "black_pack_id": "edit-CH_P28_BLK_PCK_CBOX",
                "stealth_badge_pack_id": "edit-CH_P14_STEALTH_BADGE_CBOX",
                "underbody_carbon_pack_id": "edit-CH_P28_CF_UNDERBODY_PK_CBOX",
                "exterior_carbon_pack_id": "edit-CH_P28_CF_DETAIL_PK_CBOX",
                "upper_structure_carbon_pack_id": "edit-CH_P28_CF_UPR_COUPE_PK_CBOX",
                "roof_pan_id": "edit-CH_P14_ROOF_PAN",
                "hood_id": "edit-CH_P14_BONNET",
                "front_fender_id": "edit-CH_P28_FRONT_FENDER",
                "exhaust_finisher_id": "edit-CH_P28_EXH_FIN",
                "active_rear_spoiler_id": "edit-CH_P14_AIRBRAKE",
                "headlight_surround_id": "edit-CH_P28_HEADLIGHT_SUR",
                "rear_bumper_id": "edit-CH_P28_RR_BUMPER",
                "rear_bumper_ducts_id": "edit-CH_P28_REAR_BUMPER_INSERT",
                "sound_comfort_windscreen_id": "edit-CH_P28_SOUND_WINDSCREEN_CBOX",
                
                # Interior Specification Section
                "interior_theme_id": "edit-CH_P28_SPEC",
                
                # Interior Section
                "interior_color_id": "edit-CH_P14_INT_THEME",
                "gloss_finish_visual_carbon_fibre_extended_upper_trim_id": "edit-CH_P28_CF_UPPERTRIM_PK_CBOX",
                "seat_type_id": "edit-CH_P14_SEAT_STYLE",
                "passenger_seat_position_id": "edit-CH_P14_SEAT_POS",
                "seat_size_id": "edit-CH_P14_SEAT_SIZE",
                "seat_belts_id": "edit-CH_P14_SEAT_BELT",
                "steering_wheel_id": "edit-CH_P14_STEERING_WHL",
                "sill_finishers_id": "edit-CH_P14_SILL_TRIM_CLR",
                "floor_mats_id": "edit-CH_P14_PRACT_FLMAT_CBOX",
                "track_plaque_id": "edit-CH_P14_TRACK_PLAQUE_CBOX",
                
                # Entertainment Section
                "audio_id": "edit-CH_P14_AUDIO",
                
                # Safety & Security Section
                "vehicle_lift_id": "edit-CH_P28_VEH_LIFT_CBOX",
                "park_assist_360_id": "edit-CH_P14_PK_ASSIST_360_CBOX",
                "parking_sensors_id": "edit-CH_P14_FR_RR_PK_SENS_CBOX",
                "rear_camera_sensors_id": "edit-CH_P14_RR_VIEW_CAM_SENS_CBOX",
                "alarm_upgrade_id": "edit-CH_P14_VOL_ALARM_CBOX",
                "tracking_system_id": "edit-CH_P14_TK_SYS_CBOX",
                "homelink_id": "edit-CH_P14_HOMELINK_CBOX",
                
                # Practical Section
                "battery_charger_id": "edit-CH_P14_LI_ION_CHGR_CBOX",
                "warning_triangle_id": "edit-CH_P14_WARN_TRI_CBOX",
                "fire_extinguisher_id": "edit-CH_P14_EXTING_CBOX",
                "car_cover_id": "edit-CH_P14_BRAND_COVER_CBOX",
                "ashtray_id": "edit-CH_P14_ASHTRAY_CBOX",
                "painted_key_id": "edit-CH_P14_PAINTED_KEY_CBOX",
                "printed_handbook_id": "edit-CH_P14_PRINT_HB_CBOX",
                "owners_manual_id": "edit-CH_GEN_MANUAL_LNG",
                "system_language_id": "edit-CH_GEN_SYS_LNG"
            }
        }

    def get_model_config(self, model_name):
        """Get configuration for current model"""
        return self.model_config.get(model_name, {})

    def upload_to_cloudinary(self, base64_image, folder="mclaren_cars", filename=None):
        """Upload base64 image to Cloudinary and return URL"""
        try:
            if not base64_image:
                return ""
            
            img_bytes = base64.b64decode(base64_image)
            img = Image.open(BytesIO(img_bytes))
            png_buffer = BytesIO()
            img.save(png_buffer, format='PNG')
            png_buffer.seek(0)
            
            upload_params = {
                "folder": folder,
                "format": "png",
                "quality": "auto",
                "fetch_format": "auto"
            }
            
            if filename:
                upload_params["public_id"] = filename
            
            result = cloudinary.uploader.upload(png_buffer, **upload_params)
            print(f"          ✓ Uploaded to Cloudinary: {result['secure_url']}")
            return result['secure_url']
            
        except Exception as e:
            print(f"          ✗ Cloudinary upload error: {e}")
            return ""
    
    def load_initial_models(self):
        """Load initial McLaren models array"""
        return [
            {
                "name": "GTS",
                "link": "https://configurator.mclaren.com/mclaren-ui/?profile/gts",
                "price": "null",
                "image": "https://configurator.mclaren.com/resource/image/cars/P22.png"
            },
            {
                "name": "ARTURA",
                "link": "https://configurator.mclaren.com/mclaren-ui/?profile/artura",
                "price": "null",
                "image": "https://configurator.mclaren.com/resource/image/cars/P16.png"
            },
            {
                "name": "ARTURA SPIDER",
                "link": "https://configurator.mclaren.com/mclaren-ui/?profile/artura-spider",
                "price": "null",
                "image": "https://configurator.mclaren.com/resource/image/cars/P16S.png"
            },
            {
                "name": "750S",
                "link": "https://configurator.mclaren.com/mclaren-ui/?profile/750s",
                "price": "null",
                "image": "https://configurator.mclaren.com/resource/image/cars/P28.png"
            },
            {
                "name": "750S SPIDER",
                "link": "https://configurator.mclaren.com/mclaren-ui/?profile/750s-spider",
                "price": "null",
                "image": "https://configurator.mclaren.com/resource/image/cars/P28S.png"
            }
        ]
    
    def wait_for_3d_model(self, timeout=20):
        """Wait for the 3D model to load completely"""
        print("    Waiting for 3D model to load...")
        try:
            viz_container = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "visualization-3D"))
            )
            print("    ✓ Visualization container found")
            
            canvas = self.wait.until(
                EC.presence_of_element_located((By.ID, "infinityrt-canvas"))
            )
            print("    ✓ Canvas found")
            
            self.wait.until(lambda d: canvas.size['width'] > 0 and canvas.size['height'] > 0)
            print("    ✓ Canvas has dimensions")
            
            time.sleep(5)
            
            has_webgl = self.driver.execute_script("""
                var canvas = document.getElementById('infinityrt-canvas');
                try {
                    var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    return gl !== null;
                } catch(e) {
                    return false;
                }
            """)
            
            if has_webgl:
                print("    ✓ WebGL context active")
            else:
                print("    ⚠ WebGL context not detected")
            
            time.sleep(3)
            print("    ✓ 3D model loaded")
            return True
            
        except Exception as e:
            print(f"    Error waiting for 3D model: {e}")
            return False

    def crop_image(self, screenshot_bytes, crop_top_ratio=0.05, crop_bottom_ratio=0.15, crop_left_ratio=0.0, crop_right_ratio=0.0):
        """Crop the screenshot to remove UI elements and focus on the car"""
        try:
            image = Image.open(BytesIO(screenshot_bytes))
            width, height = image.size
            
            top_crop = int(height * crop_top_ratio)
            bottom_crop = int(height * crop_bottom_ratio)
            left_crop = int(width * crop_left_ratio)
            right_crop = int(width * crop_right_ratio)
            
            crop_box = (left_crop, top_crop, width - right_crop, height - bottom_crop)
            cropped_image = image.crop(crop_box)
            
            buffered = BytesIO()
            cropped_image.save(buffered, format="PNG")
            cropped_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            print(f"          Cropped: {width}x{height} -> {cropped_image.size[0]}x{cropped_image.size[1]}")
            return cropped_base64
            
        except Exception as e:
            print(f"          Error cropping image: {e}")
            return base64.b64encode(screenshot_bytes).decode('utf-8')
    
    def wait_for_canvas_update(self, timeout=10):
        """Wait for canvas to update after a change"""
        try:
            canvas = self.driver.find_element(By.ID, "infinityrt-canvas")
            self.wait.until(lambda d: canvas.is_displayed() and 
                          canvas.size['width'] > 0 and 
                          canvas.size['height'] > 0)
            time.sleep(3)
            print("          ✓ Canvas ready")
            return True
        except Exception as e:
            print(f"          ⚠ Canvas check failed: {e}")
            time.sleep(4)
            return False
    
    def capture_canvas_image(self, wait_time=4, upload=True, folder="mclaren_cars", filename=None, retry_count=0):
        """Capture the current state of the 3D canvas and upload to Cloudinary"""
        try:
            time.sleep(wait_time)
            canvas = self.driver.find_element(By.ID, "infinityrt-canvas")
            
            self.driver.execute_script("""
                arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});
            """, canvas)
            time.sleep(1.5)
            
            try:
                screenshot_bytes = canvas.screenshot_as_png
                img_base64 = self.crop_image(
                    screenshot_bytes, 
                    crop_top_ratio=0.15, 
                    crop_bottom_ratio=0.15, 
                    crop_left_ratio=0.0, 
                    crop_right_ratio=0.30
                )
                print("          ✓ Captured and cropped via element screenshot")
            except Exception as e:
                print(f"          ⚠ Element screenshot failed: {e}")
                img_base64 = ""
            
            if not img_base64:
                try:
                    location = canvas.location
                    size = canvas.size
                    screenshot = self.driver.get_screenshot_as_png()
                    screenshot_img = Image.open(BytesIO(screenshot))
                    
                    left = location['x']
                    top = location['y']
                    right = left + size['width']
                    bottom = top + size['height']
                    
                    canvas_img = screenshot_img.crop((left, top, right, bottom))
                    buffer = BytesIO()
                    canvas_img.save(buffer, format='PNG')
                    screenshot_bytes = buffer.getvalue()
                    
                    img_base64 = self.crop_image(
                        screenshot_bytes,
                        crop_top_ratio=0.15,
                        crop_bottom_ratio=0.15,
                        crop_left_ratio=0.0,
                        crop_right_ratio=0.30
                    )
                    print("          ✓ Captured and cropped via page screenshot")
                except Exception as e:
                    print(f"          ⚠ Page screenshot failed: {e}")
            
            if img_base64 and retry_count < 3:
                try:
                    img_bytes = base64.b64decode(img_base64)
                    img = Image.open(BytesIO(img_bytes))
                    gray_img = img.convert('L')
                    pixels = list(gray_img.getdata())
                    avg_brightness = sum(pixels) / len(pixels)
                    variance = sum((p - avg_brightness) ** 2 for p in pixels[:1000]) / 1000
                    
                    if avg_brightness < 10 or variance < 10:
                        print(f"          ⚠ Image appears blank (brightness: {avg_brightness:.1f}, variance: {variance:.1f})")
                        if retry_count < 3:
                            print(f"          ↻ Retrying... (attempt {retry_count + 2}/4)")
                            time.sleep(5)
                            return self.capture_canvas_image(wait_time=6, upload=upload, folder=folder, filename=filename, retry_count=retry_count + 1)
                    else:
                        print(f"          ✓ Image validated (brightness: {avg_brightness:.1f})")
                except Exception as e:
                    print(f"          ⚠ Image validation error: {e}")
            
            if upload and img_base64:
                cloudinary_url = self.upload_to_cloudinary(img_base64, folder, filename)
                return cloudinary_url
            
            return img_base64 if not upload else ""
            
        except Exception as e:
            print(f"      Error capturing canvas: {e}")
            if retry_count < 3:
                print(f"      Retrying capture (attempt {retry_count + 2}/4)...")
                time.sleep(6)
                return self.capture_canvas_image(wait_time=6, upload=upload, folder=folder, filename=filename, retry_count=retry_count + 1)
            return ""
    
    def click_summary_button(self):
        """Click the summary button to reveal more features"""
        print("\n  Clicking summary button...")
        try:
            summary_btn = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "main__summary-button"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", summary_btn)
            time.sleep(1)
            
            try:
                summary_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", summary_btn)
            
            time.sleep(2)
            print("    ✓ Summary button clicked")
            return True
        except Exception as e:
            print(f"    ✗ Error clicking summary button: {e}")
            return False
    
    def scrape_wheels(self):
        """Scrape wheel options WITHOUT taking screenshots - FIXED WHEEL NAME"""
        print("\n    Scraping Wheels...")
        wheels = []
        
        config = self.get_model_config(self.current_model)
        wheels_id = config.get("wheels_id")
        
        if not wheels_id:
            print(f"      ⚠ No wheels configuration for {self.current_model}")
            return wheels
        
        try:
            edit_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, wheels_id))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_btn)
            time.sleep(0.5)
            
            try:
                edit_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", edit_btn)
            
            time.sleep(2)
            print("      ✓ Wheel editor opened")
            
            wheel_elements = self.driver.find_elements(By.CLASS_NAME, "wheel-cstic__image-value")
            print(f"      Found {len(wheel_elements)} wheel option(s)")
            
            for idx, wheel_elem in enumerate(wheel_elements):
                try:
                    wheel_name = f"Wheel {idx + 1}"
                    try:
                        text_elem = wheel_elem.find_element(By.CSS_SELECTOR, "p.wheel-cstic__text")
                        wheel_name = text_elem.text.strip() or wheel_name
                        print(f"          Found wheel name from p tag: {wheel_name}")
                    except:
                        try:
                            text_elem = wheel_elem.find_element(By.CLASS_NAME, "wheel-cstic__text")
                            wheel_name = text_elem.text.strip() or wheel_name
                        except:
                            wheel_name = (
                                wheel_elem.get_attribute("aria-label") or
                                wheel_elem.get_attribute("title") or
                                wheel_elem.get_attribute("data-name") or
                                wheel_name
                            )
                    
                    price = "$0"
                    full_text = f"{wheel_elem.get_attribute('aria-label') or ''} {wheel_elem.text}"
                    price_match = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', full_text)
                    if price_match:
                        price = price_match.group(0).strip()
                        wheel_name = re.sub(r'\$\s*[\d,]+(?:\.\d{2})?', '', wheel_name).strip()
                    
                    wheel_image = ""
                    try:
                        img = wheel_elem.find_element(By.TAG_NAME, "img")
                        wheel_image = img.get_attribute("src")
                    except:
                        pass
                    
                    elem_class = wheel_elem.get_attribute("class") or ""
                    is_selected = any(word in elem_class.lower() for word in ["active", "selected", "current"])
                    
                    wheel_data = {
                        "name": wheel_name,
                        "price": price,
                        "wheel_image": wheel_image,
                        "currently_selected": is_selected
                    }
                    
                    wheels.append(wheel_data)
                    print(f"          ✓ {wheel_name} - {price}")
                    
                except Exception as e:
                    print(f"          ✗ Error processing wheel: {e}")
                    continue
            
            print(f"    ✓ Scraped {len(wheels)} wheel(s)")
            return wheels
            
        except Exception as e:
            print(f"    ✗ Error scraping wheels: {e}")
            return []
    
    def scrape_brakes(self):
        """Scrape brake options WITHOUT taking screenshots - FIXED BRAKE IMAGE"""
        print("\n    Scraping Brakes...")
        brakes = []
        
        config = self.get_model_config(self.current_model)
        brakes_id = config.get("brakes_id")
        
        if not brakes_id:
            print(f"      ⚠ No brakes configuration for {self.current_model}")
            return brakes
        
        try:
            edit_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, brakes_id))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_btn)
            time.sleep(0.5)
            
            try:
                edit_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", edit_btn)
            
            time.sleep(2)
            print("      ✓ Brake editor opened")
            
            brake_containers = self.driver.find_elements(By.CLASS_NAME, "wheel-cstic__value")
            print(f"      Found {len(brake_containers)} brake option(s)")
            
            for idx, brake_elem in enumerate(brake_containers):
                try:
                    brake_name = (
                        brake_elem.get_attribute("aria-label") or
                        brake_elem.get_attribute("title") or
                        brake_elem.text.strip() or
                        f"Brake {idx + 1}"
                    )
                    
                    price = "$0"
                    full_text = f"{brake_elem.get_attribute('aria-label') or ''} {brake_elem.text}"
                    price_match = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', full_text)
                    if price_match:
                        price = price_match.group(0).strip()
                        brake_name = re.sub(r'\$\s*[\d,]+(?:\.\d{2})?', '', brake_name).strip()
                    
                    brake_image = ""
                    try:
                        img = brake_elem.find_element(By.CLASS_NAME, "wheel-cstic__image")
                        brake_image = img.get_attribute("src")
                        print(f"          Found brake image from wheel-cstic__image: {brake_image[:50]}...")
                    except:
                        try:
                            img = brake_elem.find_element(By.TAG_NAME, "img")
                            brake_image = img.get_attribute("src")
                        except:
                            pass
                    
                    elem_class = brake_elem.get_attribute("class") or ""
                    is_selected = any(word in elem_class.lower() for word in ["active", "selected", "current"])
                    
                    brake_data = {
                        "name": brake_name,
                        "price": price,
                        "brake_image": brake_image,
                        "currently_selected": is_selected
                    }
                    
                    brakes.append(brake_data)
                    print(f"          ✓ {brake_name} - {price}")
                    
                except Exception as e:
                    print(f"          ✗ Error processing brake: {e}")
                    continue
            
            print(f"    ✓ Scraped {len(brakes)} brake(s)")
            return brakes
            
        except Exception as e:
            print(f"    ✗ Error scraping brakes: {e}")
            return []
    
    def scrape_exterior_colors(self):
        """Scrape exterior color options WITH screenshots"""
        print("    Scraping Exterior Colors...")
        colors = []
        seen = set()
        
        try:
            paint_section = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "paint-cstic"))
            )
            print("      ✓ Paint section found")
            
            color_groups = paint_section.find_elements(By.CLASS_NAME, "paint-cstic__group")
            print(f"      Found {len(color_groups)} color group(s)")
            
            all_colors = []
            
            for group_idx, group in enumerate(color_groups):
                try:
                    group_name = ""
                    try:
                        group_title = group.find_element(By.CSS_SELECTOR, 
                            ".paint-cstic__group-title, .group-title, h3, h4, .title")
                        group_name = group_title.text.strip()
                        print(f"\n        Group {group_idx + 1}: {group_name}")
                    except:
                        group_name = f"Group {group_idx + 1}"
                        print(f"\n        Group {group_idx + 1}")
                    
                    color_elements = group.find_elements(By.CLASS_NAME, "paint-cstic__value")
                    print(f"          Found {len(color_elements)} color(s) in this group")
                    
                    for color_idx, color_elem in enumerate(color_elements):
                        try:
                            color_name = (
                                color_elem.get_attribute("aria-label") or
                                color_elem.get_attribute("title") or
                                color_elem.get_attribute("data-color") or
                                color_elem.get_attribute("data-name") or
                                color_elem.text.strip()
                            )
                            
                            if not color_name:
                                try:
                                    img = color_elem.find_element(By.CLASS_NAME, "paint-cstic__value-image")
                                    color_name = img.get_attribute("alt") or img.get_attribute("title")
                                except:
                                    pass
                            
                            if not color_name:
                                color_name = f"Color {color_idx + 1}"
                            
                            price = "$0"
                            full_text = f"{color_elem.get_attribute('aria-label') or ''} {color_elem.text}"
                            price_match = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', full_text)
                            if price_match:
                                price = price_match.group(0).strip()
                                color_name = re.sub(r'\$\s*[\d,]+(?:\.\d{2})?', '', color_name).strip()
                            
                            color_key = f"{color_name}_{group_name}"
                            if color_key in seen:
                                continue
                            seen.add(color_key)
                            
                            swatch_image = ""
                            try:
                                img = color_elem.find_element(By.CLASS_NAME, "paint-cstic__value-image")
                                swatch_image = img.get_attribute("src")
                            except:
                                try:
                                    img = color_elem.find_element(By.TAG_NAME, "img")
                                    swatch_image = img.get_attribute("src")
                                except:
                                    pass
                            
                            elem_class = color_elem.get_attribute("class") or ""
                            is_selected = any(word in elem_class.lower() for word in ["active", "selected", "current"])
                            is_disabled = ("disabled" in elem_class.lower() or 
                                         color_elem.get_attribute("disabled"))
                            
                            color_data = {
                                "name": color_name,
                                "group": group_name,
                                "price": price,
                                "swatch_image": swatch_image,
                                "car_image": "",
                                "currently_selected": is_selected,
                                "disabled": is_disabled
                            }
                            
                            all_colors.append((color_elem, color_data, is_selected))
                            
                            status = []
                            if is_selected:
                                status.append("(selected)")
                            if is_disabled:
                                status.append("(disabled)")
                            print(f"            ✓ {color_name} - {price} {' '.join(status)}")
                            
                        except Exception as e:
                            print(f"            Error processing color: {e}")
                            continue
                            
                except Exception as e:
                    print(f"        Error processing group: {e}")
                    continue
            
            print(f"\n      Found {len(all_colors)} unique color(s)")
            print("\n      Capturing car images for each color...")
            final_colors = []
            
            for idx, (color_elem, color_data, is_selected) in enumerate(all_colors):
                try:
                    color_name = color_data["name"]
                    
                    if color_data["disabled"]:
                        print(f"        [{idx+1}/{len(all_colors)}] Skipping disabled: {color_name}")
                        final_colors.append(color_data)
                        continue
                    
                    if is_selected:
                        print(f"        [{idx+1}/{len(all_colors)}] Capturing selected: {color_name}")
                        car_image = self.capture_canvas_image(wait_time=2)
                        color_data["car_image"] = car_image
                        final_colors.append(color_data)
                        continue
                    
                    print(f"        [{idx+1}/{len(all_colors)}] Clicking: {color_name}")
                    
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        color_elem
                    )
                    time.sleep(0.5)
                    
                    try:
                        color_elem.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", color_elem)
                    
                    time.sleep(3)
                    
                    car_image = self.capture_canvas_image(wait_time=2)
                    color_data["car_image"] = car_image
                    
                    if car_image:
                        print(f"          ✓ Image captured")
                    else:
                        print(f"          ⚠ No image")
                    
                    final_colors.append(color_data)
                    
                except Exception as e:
                    print(f"          ✗ Error: {e}")
                    final_colors.append(color_data)
                    continue
            
            print(f"\n    ✓ Scraped {len(final_colors)} exterior colors")
            return final_colors
            
        except Exception as e:
            print(f"    ✗ Error scraping exterior colors: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_toggle_option(self, element_id, option_name, has_image=False):
        """Scrape toggle options WITHOUT screenshots - FIXED FOR YES/NO OPTIONS"""
        print(f"\n    Scraping {option_name}...")
        options = []
        
        try:
            edit_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, element_id))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_btn)
            time.sleep(0.5)
            
            try:
                edit_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", edit_btn)
            
            time.sleep(2)
            print(f"      ✓ {option_name} editor opened")
            
            toggle_options = self.driver.find_elements(By.CLASS_NAME, "toggle-cstic__name")
            print(f"      Found {len(toggle_options)} toggle option(s)")
            
            for idx, toggle_elem in enumerate(toggle_options):
                try:
                    toggle_name = toggle_elem.text.strip()
                    if not toggle_name:
                        toggle_name = f"{option_name} Option {idx + 1}"
                    
                    price = "$0"
                    full_text = f"{toggle_elem.get_attribute('aria-label') or ''} {toggle_elem.text}"
                    price_match = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', full_text)
                    if price_match:
                        price = price_match.group(0).strip()
                    
                    toggle_image = ""
                    if has_image:
                        try:
                            parent = toggle_elem.find_element(By.XPATH, "./..")
                            img = parent.find_element(By.CLASS_NAME, "toggle-cstic__image")
                            toggle_image = img.get_attribute("src")
                        except:
                            pass
                    
                    parent = toggle_elem.find_element(By.XPATH, "./..")
                    elem_class = parent.get_attribute("class") or ""
                    is_enabled = "toggle-cstic__value--checked" in elem_class
                    
                    if option_name in ["Bright Pack", "Exterior Details Pack", "Exterior Details - Carbon Fibre Pack", 
                                      "Underbody Carbon Pack", "Underbody - Carbon Fibre Pack", "Stealth Badge Pack", 
                                      "Privacy Glass", "Thermal Insulated Windscreen", "Rear Spoiler - Gloss Carbon Fibre",
                                      "Black Pack", "Upper Structure - Carbon Fibre Pack", "Interior Details - Carbon Fibre Pack",
                                      "Luggage Retention Strap", "Practicality Pack", "Premium Pack", 
                                      "Machined Aluminium Details Pack", "Vehicle Lift", "Volumetric Alarm Upgrade",
                                      "Vehicle Tracking System", "Lithium-ion Battery Charger", "Warning Triangle & First Aid",
                                      "Fire Extinguisher", "Branded Car Cover", "Ashtray", "Painted Vehicle Key – Body Colour",
                                      "Printed Owner's Handbook", "Gloss Black Interior Finish Pack", 
                                      "Interior Details – Carbon Fibre Pack", "Harness Bar", "McLaren Track Record Plaque",
                                      "Technology Pack", "Driving Assistant Pack", "Warning Triangle & First Aid Kit",
                                      "Warning Triangle & First Aid", "Sound Comfort Windscreen", "Titanium Harness Bar",
                                      "Double Glazed Engine Window", "McLaren Track Record Plaque", "Vehicle Lift",
                                      "360 Degree Park Assist", "Front & Rear Parking Sensors", "Rear View Camera & Sensors",
                                      "Volumetric Alarm Upgrade", "Vehicle Tracking System", "Homelink",
                                      "Lithium-ion Battery Charger", "Warning Triangle & First Aid", "Fire Extinguisher",
                                      "Branded Car Cover", "Ashtray", "Painted Vehicle Key – Body Colour", "Printed Owner's Handbook",
                                      "Track Brake Upgrade", "Gloss Finish Visual Carbon Fibre Extended Upper Trim"]:
                        return [{"state": "yes" if is_enabled else "no"}]
                    
                    toggle_data = {
                        "name": toggle_name,
                        "price": price,
                        "image": toggle_image,
                        "currently_enabled": is_enabled
                    }
                    
                    options.append(toggle_data)
                    print(f"          ✓ {toggle_name} - {price} ({'Enabled' if is_enabled else 'Disabled'})")
                    
                except Exception as e:
                    print(f"          ✗ Error processing toggle: {e}")
                    continue
            
            if not options:
                try:
                    toggle_container = self.driver.find_element(By.CLASS_NAME, "toggle-cstic__value")
                    elem_class = toggle_container.get_attribute("class") or ""
                    is_enabled = "toggle-cstic__value--checked" in elem_class
                    return [{"state": "yes" if is_enabled else "no"}]
                except:
                    pass
            
            print(f"    ✓ Scraped {len(options)} {option_name} option(s)")
            return options
            
        except Exception as e:
            print(f"    ✗ Error scraping {option_name}: {e}")
            return []
    
    def scrape_other_cstic_options(self, element_id, option_name, name_class="other-cstic__value-name", 
                                   has_swatch_image=False, has_product_image=False, take_screenshot=False,
                                   name_tag="span", special_case=False):
        """Scrape options from other-cstic containers, with optional screenshot"""
        print(f"\n    Scraping {option_name}...")
        options = []
        
        try:
            edit_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, element_id))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_btn)
            time.sleep(0.5)
            
            try:
                edit_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", edit_btn)
            
            time.sleep(2)
            print(f"      ✓ {option_name} editor opened")
            
            containers = self.driver.find_elements(By.CLASS_NAME, "other-cstic__value")
            if not containers:
                containers = self.driver.find_elements(By.CLASS_NAME, "other-cstic__image-value")
            
            print(f"      Found {len(containers)} {option_name} option(s)")
            
            for idx, container in enumerate(containers):
                try:
                    option_name_text = f"{option_name} {idx + 1}"
                    
                    if option_name == "Interior Theme" and special_case:
                        try:
                            name_elem = container.find_element(By.CSS_SELECTOR, "h1 span.specification-cstic__value-header")
                            option_name_text = name_elem.text.strip() or option_name_text
                        except:
                            pass
                    else:
                        try:
                            name_elem = container.find_element(By.CSS_SELECTOR, "p.other-cstic__text")
                            option_name_text = name_elem.text.strip() or option_name_text
                        except:
                            try:
                                name_elem = container.find_element(By.CLASS_NAME, name_class)
                                option_name_text = name_elem.text.strip() or option_name_text
                            except:
                                try:
                                    text_elem = container.find_element(By.CLASS_NAME, "other-cstic__text")
                                    option_name_text = text_elem.text.strip() or option_name_text
                                except:
                                    option_name_text = (
                                        container.get_attribute("aria-label") or
                                        container.get_attribute("title") or
                                        option_name_text
                                    )
                    
                    option_name_text = re.sub(r'\$\s*[\d,]+(?:\.\d{2})?', '', option_name_text).strip()
                    
                    price = "$0"
                    full_text = f"{container.get_attribute('aria-label') or ''} {container.text}"
                    price_match = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', full_text)
                    if price_match:
                        price = price_match.group(0).strip()
                    
                    swatch_image = ""
                    product_image = ""
                    
                    if has_swatch_image:
                        try:
                            img = container.find_element(By.CLASS_NAME, "other-cstic__image")
                            swatch_image = img.get_attribute("src")
                            print(f"          Found swatch image from other-cstic__image")
                        except:
                            try:
                                img = container.find_element(By.TAG_NAME, "img")
                                swatch_image = img.get_attribute("src")
                            except:
                                pass
                    
                    if has_product_image:
                        try:
                            img = container.find_element(By.CLASS_NAME, "other-cstic__image")
                            product_image = img.get_attribute("src")
                        except:
                            pass
                    
                    elem_class = container.get_attribute("class") or ""
                    is_selected = any(word in elem_class.lower() for word in ["active", "selected", "current"])
                    
                    option_data = {
                        "name": option_name_text,
                        "price": price,
                        "swatch_image": swatch_image,
                        "product_image": product_image,
                        "car_image": "",
                        "currently_selected": is_selected
                    }
                    
                    if take_screenshot:
                        if not is_selected:
                            print(f"        [{idx+1}/{len(containers)}] Clicking: {option_name_text}")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
                            time.sleep(0.5)
                            
                            try:
                                container.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", container)
                            
                            time.sleep(3)
                        else:
                            print(f"        [{idx+1}/{len(containers)}] Capturing selected: {option_name_text}")
                        
                        car_image = self.capture_canvas_image(wait_time=2)
                        option_data["car_image"] = car_image
                    else:
                        print(f"        [{idx+1}/{len(containers)}] Processing: {option_name_text}")
                    
                    options.append(option_data)
                    print(f"          ✓ {option_name_text} - {price}")
                    
                except Exception as e:
                    print(f"          ✗ Error processing {option_name}: {e}")
                    continue
            
            print(f"    ✓ Scraped {len(options)} {option_name} option(s)")
            return options
            
        except Exception as e:
            print(f"    ✗ Error scraping {option_name}: {e}")
            return []
    
    # ================= NEW METHODS =================
    
    def scrape_tonneau(self):
        """Scrape tonneau options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        tonneau_id = config.get("tonneau_id")
        
        if not tonneau_id or self.current_model not in ["ARTURA SPIDER"]:
            print(f"      ⚠ Tonneau not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            tonneau_id, 
            "Tonneau",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )

    def scrape_track_brake_upgrade(self):
        """Scrape track brake upgrade options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        track_brake_id = config.get("track_brake_upgrade_id")
        
        if not track_brake_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Track brake upgrade not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(track_brake_id, "Track Brake Upgrade", has_image=False)

    def scrape_roof_pan(self):
        """Scrape roof pan options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        roof_pan_id = config.get("roof_pan_id")
        
        if not roof_pan_id or self.current_model not in ["750S SPIDER"]:
            print(f"      ⚠ Roof pan not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            roof_pan_id, 
            "Roof",
            name_class="other-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )

    def scrape_gloss_finish_visual_carbon_fibre_extended_upper_trim(self):
        """Scrape gloss finish visual carbon fibre extended upper trim options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        carbon_trim_id = config.get("gloss_finish_visual_carbon_fibre_extended_upper_trim_id")
        
        if not carbon_trim_id or self.current_model not in ["750S SPIDER"]:
            print(f"      ⚠ Gloss Finish Visual Carbon Fibre Extended Upper Trim not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(
            carbon_trim_id, 
            "Gloss Finish Visual Carbon Fibre Extended Upper Trim", 
            has_image=False
        )
    
    # ================= EXISTING METHODS =================
    
    def scrape_wheel_bolts(self):
        """Scrape wheel bolts options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        wheel_bolts_id = config.get("wheel_bolts_id")
        
        if not wheel_bolts_id:
            print(f"      ⚠ Wheel bolts not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(wheel_bolts_id, "Lightweight Titanium Wheel Bolts", has_image=False)
    
    def scrape_tyre_type(self):
        """Scrape tyre type options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        tyre_type_id = config.get("tyre_type_id")
        
        if not tyre_type_id:
            print(f"      ⚠ Tyre type not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            tyre_type_id, 
            "Tyre Type",
            name_class="wheel-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_bright_pack(self):
        """Scrape bright pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        bright_pack_id = config.get("bright_pack_id")
        
        if not bright_pack_id:
            print(f"      ⚠ Bright pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(bright_pack_id, "Bright Pack", has_image=False)
    
    def scrape_exterior_details_pack(self):
        """Scrape exterior details pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            exterior_details_id = config.get("exterior_details_id")
            option_name = "Exterior Details Pack"
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            exterior_details_id = config.get("exterior_details_id")
            option_name = "Exterior Details Pack"
        elif self.current_model in ["750S", "750S SPIDER"]:
            exterior_details_id = config.get("exterior_carbon_pack_id")
            option_name = "Exterior Details - Carbon Fibre Pack"
        else:
            return []
        
        if not exterior_details_id:
            print(f"      ⚠ {option_name} not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(exterior_details_id, option_name, has_image=False)
    
    def scrape_underbody_carbon_pack(self):
        """Scrape underbody carbon pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            underbody_id = config.get("underbody_carbon_id")
            option_name = "Underbody Carbon Pack"
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            underbody_id = config.get("underbody_carbon_id")
            option_name = "Underbody Carbon Pack"
        elif self.current_model in ["750S", "750S SPIDER"]:
            underbody_id = config.get("underbody_carbon_pack_id")
            option_name = "Underbody - Carbon Fibre Pack"
        else:
            return []
        
        if not underbody_id:
            print(f"      ⚠ {option_name} not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(underbody_id, option_name, has_image=False)
    
    def scrape_stealth_badge_pack(self):
        """Scrape stealth badge pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            stealth_id = config.get("stealth_badge_pack_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            stealth_id = config.get("stealth_badge_pack_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            stealth_id = config.get("stealth_badge_pack_id")
        else:
            return []
        
        if not stealth_id:
            print(f"      ⚠ Stealth badge pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(stealth_id, "Stealth Badge Pack", has_image=False)
    
    def scrape_gts_side_badge(self):
        """Scrape GTS side badge options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        gts_side_badge_id = config.get("gts_side_badge_id")
        
        if not gts_side_badge_id:
            print(f"      ⚠ GTS side badge not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            gts_side_badge_id, 
            "GTS Side Badges",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
    
    def scrape_roof_colors(self):
        """Scrape roof color options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        roof_id = config.get("roof_id")
        
        if not roof_id:
            print(f"      ⚠ No roof configuration for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            roof_id, 
            "Roof",
            name_class="other-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_privacy_glass(self):
        """Scrape privacy glass options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        privacy_glass_id = config.get("privacy_glass_id")
        
        if not privacy_glass_id:
            print(f"      ⚠ Privacy glass not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(privacy_glass_id, "Privacy Glass", has_image=False)
    
    def scrape_exhaust_type(self):
        """Scrape exhaust type options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            exhaust_id = config.get("exhaust_type_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            exhaust_id = config.get("exhaust_type_id")
        else:
            return []
        
        if not exhaust_id:
            print(f"      ⚠ Exhaust type not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            exhaust_id, 
            "Exhaust Type",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
    
    def scrape_exhaust_finisher(self):
        """Scrape exhaust finisher options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            finisher_id = config.get("exhaust_finisher_id")
            option_name = "Exhaust Finisher"
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            finisher_id = config.get("exhaust_hot_vee_finishers_id")
            option_name = "Exhaust & Hot Vee Finishers"
        else:
            return []
        
        if not finisher_id:
            print(f"      ⚠ {option_name} not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            finisher_id, 
            option_name,
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_mirror_casings(self):
        """Scrape mirror casing options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        mirror_casings_id = config.get("mirror_casings_id")
        
        if not mirror_casings_id:
            print(f"      ⚠ Mirror casings not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            mirror_casings_id, 
            "Door Mirror Casings",
            name_class="other-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_front_fender_louvres(self):
        """Scrape front fender louvres options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        fender_id = config.get("front_fender_louvres_id")
        
        if not fender_id:
            print(f"      ⚠ Front fender louvres not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            fender_id, 
            "Front Fender Louvres",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_engine_cover(self):
        """Scrape engine cover options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        engine_id = config.get("engine_cover_id")
        
        if not engine_id:
            print(f"      ⚠ Engine cover not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            engine_id, 
            "Engine Cover",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_thermal_windscreen(self):
        """Scrape thermal insulated windscreen options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        thermal_id = config.get("thermal_windscreen_id")
        
        if not thermal_id:
            print(f"      ⚠ Thermal windscreen not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(thermal_id, "Thermal Insulated Windscreen", has_image=False)
    
    def scrape_rear_spoiler(self):
        """Scrape rear spoiler options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        spoiler_id = config.get("rear_spoiler_id")
        
        if not spoiler_id:
            print(f"      ⚠ Rear spoiler not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(spoiler_id, "Rear Spoiler - Gloss Carbon Fibre", has_image=False)
    
    def scrape_upper_structure_carbon_pack(self):
        """Scrape upper structure carbon pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        upper_id = config.get("upper_structure_carbon_pack_id")
        
        if not upper_id:
            print(f"      ⚠ Upper structure carbon pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(upper_id, "Upper Structure - Carbon Fibre Pack", has_image=False)
    
    def scrape_hood_colors(self):
        """Scrape hood color options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        hood_id = config.get("hood_id")
        
        if not hood_id:
            print(f"      ⚠ Hood not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            hood_id, 
            "Hood",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_front_fender(self):
        """Scrape front fender options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        fender_id = config.get("front_fender_id")
        
        if not fender_id:
            print(f"      ⚠ Front fender not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            fender_id, 
            "Front Fender",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_active_rear_spoiler(self):
        """Scrape active rear spoiler options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        spoiler_id = config.get("active_rear_spoiler_id")
        
        if not spoiler_id:
            print(f"      ⚠ Active rear spoiler not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            spoiler_id, 
            "Active Rear Spoiler",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_headlight_surround(self):
        """Scrape headlight surround options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        headlight_id = config.get("headlight_surround_id")
        
        if not headlight_id:
            print(f"      ⚠ Headlight surround not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            headlight_id, 
            "Headlight Surround",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_rear_bumper(self):
        """Scrape rear bumper options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        bumper_id = config.get("rear_bumper_id")
        
        if not bumper_id:
            print(f"      ⚠ Rear bumper not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            bumper_id, 
            "Rear Bumper",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_rear_bumper_ducts(self):
        """Scrape rear bumper ducts options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        ducts_id = config.get("rear_bumper_ducts_id")
        
        if not ducts_id:
            print(f"      ⚠ Rear bumper ducts not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            ducts_id, 
            "Rear Bumper Ducts",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_window_surrounds(self):
        """Scrape exterior window surrounds options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        window_id = config.get("window_surrounds_id")
        
        if not window_id:
            print(f"      ⚠ Window surrounds not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            window_id, 
            "Exterior Window Surrounds",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_black_pack(self):
        """Scrape black pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model in ["ARTURA", "ARTURA SPIDER", "750S", "750S SPIDER"]:
            black_pack_id = config.get("black_pack_id")
        else:
            return []
        
        if not black_pack_id:
            print(f"      ⚠ Black pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(black_pack_id, "Black Pack", has_image=False)
    
    # ================= GTS METHODS =================
    
    def scrape_wheel_finish(self):
        """Scrape wheel finish options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        wheel_finish_id = config.get("wheel_finish_id")
        
        if not wheel_finish_id or self.current_model != "GTS":
            print(f"      ⚠ Wheel finish not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            wheel_finish_id, 
            "Wheel Finish",
            name_class="wheel-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_contrast_stitch(self):
        """Scrape contrast stitch & seat piping options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        contrast_stitch_id = config.get("contrast_stitch_id")
        
        if not contrast_stitch_id or self.current_model != "GTS":
            print(f"      ⚠ Contrast stitch not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            contrast_stitch_id, 
            "Contrast Stitch & Seat Piping",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_interior_carbon_pack(self):
        """Scrape interior details carbon fibre pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        interior_carbon_id = config.get("interior_carbon_pack_id")
        
        if not interior_carbon_id or self.current_model != "GTS":
            print(f"      ⚠ Interior carbon pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(interior_carbon_id, "Interior Details - Carbon Fibre Pack", has_image=False)
    
    def scrape_luggage_retention_strap(self):
        """Scrape luggage retention strap options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        luggage_strap_id = config.get("luggage_strap_id")
        
        if not luggage_strap_id or self.current_model != "GTS":
            print(f"      ⚠ Luggage retention strap not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(luggage_strap_id, "Luggage Retention Strap", has_image=False)
    
    def scrape_option_packs(self):
        """Scrape all option packs for GTS"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model != "GTS":
            return {}
        
        practicality_pack = []
        premium_pack = []
        machined_aluminium_pack = []
        
        practicality_id = config.get("practicality_pack_id")
        if practicality_id:
            practicality_pack = self.scrape_toggle_option(practicality_id, "Practicality Pack", has_image=False)
        
        premium_id = config.get("premium_pack_id")
        if premium_id:
            premium_pack = self.scrape_toggle_option(premium_id, "Premium Pack", has_image=False)
        
        machined_id = config.get("machined_aluminium_pack_id")
        if machined_id:
            machined_aluminium_pack = self.scrape_toggle_option(machined_id, "Machined Aluminium Details Pack", has_image=False)
        
        return {
            "practicality_pack": practicality_pack,
            "premium_pack": premium_pack,
            "machined_aluminium_details_pack": machined_aluminium_pack
        }
    
    def scrape_individual_options(self):
        """Scrape individual options for GTS"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model != "GTS":
            return {}
        
        options = {}
        
        toggle_options = [
            ("vehicle_lift_id", "Vehicle Lift"),
            ("alarm_upgrade_id", "Volumetric Alarm Upgrade"),
            ("tracking_system_id", "Vehicle Tracking System"),
            ("battery_charger_id", "Lithium-ion Battery Charger"),
            ("warning_triangle_id", "Warning Triangle & First Aid"),
            ("fire_extinguisher_id", "Fire Extinguisher"),
            ("car_cover_id", "Branded Car Cover"),
            ("ashtray_id", "Ashtray"),
            ("painted_key_id", "Painted Vehicle Key – Body Colour"),
            ("printed_handbook_id", "Printed Owner's Handbook")
        ]
        
        for option_id, option_name in toggle_options:
            element_id = config.get(option_id)
            if element_id:
                option_data = self.scrape_toggle_option(element_id, option_name, has_image=False)
                options[option_name.lower().replace(" ", "_").replace("–", "_").replace("’", "")] = option_data
        
        return options
    
    def scrape_owners_manual(self):
        """Scrape owner's manual language options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        manual_id = config.get("owners_manual_id")
        
        if not manual_id or self.current_model != "GTS":
            print(f"      ⚠ Owner's manual not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            manual_id, 
            "Owner's Manual",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]
    
    def scrape_system_language(self):
        """Scrape system language options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        language_id = config.get("system_language_id")
        
        if not language_id or self.current_model != "GTS":
            print(f"      ⚠ System language not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            language_id, 
            "System Language",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]
    
    # ================= ARTURA/ARTURA SPIDER METHODS =================
    
    def scrape_wheel_finish_artura(self):
        """Scrape wheel finish options for Artura models WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        wheel_finish_id = config.get("wheel_finish_id")
        
        if not wheel_finish_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ Wheel finish not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            wheel_finish_id, 
            "Wheel Finish",
            name_class="wheel-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )

    def scrape_gloss_black_interior_finish(self):
        """Scrape gloss black interior finish pack options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        gloss_black_id = config.get("gloss_black_finish_id")
        
        if not gloss_black_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ Gloss Black Interior Finish Pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(gloss_black_id, "Gloss Black Interior Finish Pack", has_image=False)

    def scrape_interior_carbon_pack_artura(self):
        """Scrape interior details carbon fibre pack options for Artura WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        interior_carbon_id = config.get("interior_carbon_pack_id")
        
        if not interior_carbon_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ Interior Details – Carbon Fibre Pack not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(interior_carbon_id, "Interior Details – Carbon Fibre Pack", has_image=False)

    def scrape_harness_bar(self):
        """Scrape harness bar options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        harness_id = config.get("harness_bar_id")
        
        if not harness_id or self.current_model not in ["ARTURA"]:
            print(f"      ⚠ Harness Bar not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(harness_id, "Harness Bar", has_image=False)

    def scrape_track_plaque_artura(self):
        """Scrape McLaren track record plaque options for Artura WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        plaque_id = config.get("track_plaque_id")
        
        if not plaque_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ McLaren Track Record Plaque not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(plaque_id, "McLaren Track Record Plaque", has_image=False)

    def scrape_option_packs_artura(self):
        """Scrape all option packs for Artura models"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            return {}
        
        practicality_pack = []
        technology_pack = []
        driving_assistant_pack = []
        
        practicality_id = config.get("practicality_pack_id")
        if practicality_id:
            practicality_pack = self.scrape_toggle_option(practicality_id, "Practicality Pack", has_image=False)
        
        technology_id = config.get("technology_pack_id")
        if technology_id:
            technology_pack = self.scrape_toggle_option(technology_id, "Technology Pack", has_image=False)
        
        driving_id = config.get("driving_assistant_pack_id")
        if driving_id:
            driving_assistant_pack = self.scrape_toggle_option(driving_id, "Driving Assistant Pack", has_image=False)
        
        return {
            "practicality_pack": practicality_pack,
            "technology_pack": technology_pack,
            "driving_assistant_pack": driving_assistant_pack
        }

    def scrape_individual_options_artura(self):
        """Scrape individual options for Artura models"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            return {}
        
        options = {}
        
        toggle_options = [
            ("vehicle_lift_id", "Vehicle Lift"),
            ("alarm_upgrade_id", "Volumetric Alarm Upgrade"),
            ("tracking_system_id", "Vehicle Tracking System"),
            ("warning_triangle_id", "Warning Triangle & First Aid Kit"),
            ("fire_extinguisher_id", "Fire Extinguisher"),
            ("car_cover_id", "Branded Car Cover"),
            ("ashtray_id", "Ashtray"),
            ("painted_key_id", "Painted Vehicle Key – Body Colour"),
            ("printed_handbook_id", "Printed Owner's Handbook")
        ]
        
        for option_id, option_name in toggle_options:
            element_id = config.get(option_id)
            if element_id:
                option_data = self.scrape_toggle_option(element_id, option_name, has_image=False)
                options[option_name.lower().replace(" ", "_").replace("&", "and").replace("–", "_").replace("'", "").replace("’", "")] = option_data
        
        return options

    def scrape_owners_manual_artura(self):
        """Scrape owner's manual language options for Artura WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        manual_id = config.get("owners_manual_id")
        
        if not manual_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ Owner's manual not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            manual_id, 
            "Owner's Manual",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]

    def scrape_system_language_artura(self):
        """Scrape system language options for Artura WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        language_id = config.get("system_language_id")
        
        if not language_id or self.current_model not in ["ARTURA", "ARTURA SPIDER"]:
            print(f"      ⚠ System language not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            language_id, 
            "System Language",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]
    
    # ================= 750S/750S SPIDER METHODS =================
    
    def scrape_wheel_finish_750s(self):
        """Scrape wheel finish options for 750S models WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        wheel_finish_id = config.get("wheel_finish_id")
        
        if not wheel_finish_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Wheel finish not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            wheel_finish_id, 
            "Wheel Finish",
            name_class="wheel-cstic__value-name",
            has_swatch_image=True,
            take_screenshot=False
        )

    def scrape_exhaust_finisher_750s(self):
        """Scrape exhaust finisher options for 750S WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        exhaust_finisher_id = config.get("exhaust_finisher_id")
        
        if not exhaust_finisher_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Exhaust finisher not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            exhaust_finisher_id, 
            "Exhaust Finisher",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )

    def scrape_sound_comfort_windscreen(self):
        """Scrape sound comfort windscreen options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        sound_windscreen_id = config.get("sound_comfort_windscreen_id")
        
        if not sound_windscreen_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Sound comfort windscreen not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(sound_windscreen_id, "Sound Comfort Windscreen", has_image=False)

    def scrape_passenger_seat_position(self):
        """Scrape passenger seat position options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        seat_position_id = config.get("passenger_seat_position_id")
        
        if not seat_position_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Passenger seat position not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            seat_position_id, 
            "Passenger Seat Position",
            name_class="other-cstic__value-name",
            has_swatch_image=False,
            take_screenshot=False
        )

    def scrape_seat_size(self):
        """Scrape seat size options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        seat_size_id = config.get("seat_size_id")
        
        if not seat_size_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Seat size not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            seat_size_id, 
            "Seat Size",
            name_class="other-cstic__value-name",
            has_swatch_image=False,
            take_screenshot=False
        )

    def scrape_titanium_harness_bar(self):
        """Scrape titanium harness bar options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        harness_bar_id = config.get("titanium_harness_bar_id")
        
        if not harness_bar_id:
            print(f"      ⚠ Titanium harness bar not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(harness_bar_id, "Titanium Harness Bar", has_image=False)

    def scrape_double_glazed_engine_window(self):
        """Scrape double glazed engine window options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        engine_window_id = config.get("double_glazed_engine_window_id")
        
        if not engine_window_id or self.current_model not in ["750S"]:
            print(f"      ⚠ Double glazed engine window not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(engine_window_id, "Double Glazed Engine Window", has_image=False)

    def scrape_track_plaque_750s(self):
        """Scrape McLaren track record plaque options for 750S WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        plaque_id = config.get("track_plaque_id")
        
        if not plaque_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ McLaren track record plaque not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(plaque_id, "McLaren Track Record Plaque", has_image=False)

    def scrape_safety_security_packs_750s(self):
        """Scrape all safety & security options for 750S models"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model not in ["750S", "750S SPIDER"]:
            return {}
        
        safety_security_options = {}
        
        safety_options = [
            ("vehicle_lift_id", "Vehicle Lift"),
            ("park_assist_360_id", "360 Degree Park Assist"),
            ("parking_sensors_id", "Front & Rear Parking Sensors"),
            ("rear_camera_sensors_id", "Rear View Camera & Sensors"),
            ("alarm_upgrade_id", "Volumetric Alarm Upgrade"),
            ("tracking_system_id", "Vehicle Tracking System"),
            ("homelink_id", "Homelink")
        ]
        
        for option_id, option_name in safety_options:
            element_id = config.get(option_id)
            if element_id:
                option_data = self.scrape_toggle_option(element_id, option_name, has_image=False)
                safety_security_options[option_name.lower().replace(" ", "_").replace("&", "and").replace("degree", "").strip()] = option_data
        
        return safety_security_options

    def scrape_practical_options_750s(self):
        """Scrape all practical options for 750S models"""
        config = self.get_model_config(self.current_model)
        
        if self.current_model not in ["750S", "750S SPIDER"]:
            return {}
        
        practical_options = {}
        
        practical_toggle_options = [
            ("battery_charger_id", "Lithium-ion Battery Charger"),
            ("warning_triangle_id", "Warning Triangle & First Aid"),
            ("fire_extinguisher_id", "Fire Extinguisher"),
            ("car_cover_id", "Branded Car Cover"),
            ("ashtray_id", "Ashtray"),
            ("painted_key_id", "Painted Vehicle Key – Body Colour"),
            ("printed_handbook_id", "Printed Owner's Handbook")
        ]
        
        for option_id, option_name in practical_toggle_options:
            element_id = config.get(option_id)
            if element_id:
                option_data = self.scrape_toggle_option(element_id, option_name, has_image=False)
                key_name = option_name.lower().replace(" ", "_").replace("&", "and").replace("–", "_").replace("'", "").replace("’", "")
                practical_options[key_name] = option_data
        
        return practical_options

    def scrape_owners_manual_750s(self):
        """Scrape owner's manual language options for 750S WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        manual_id = config.get("owners_manual_id")
        
        if not manual_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ Owner's manual not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            manual_id, 
            "Owner's Manual",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]

    def scrape_system_language_750s(self):
        """Scrape system language options for 750S WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        language_id = config.get("system_language_id")
        
        if not language_id or self.current_model not in ["750S", "750S SPIDER"]:
            print(f"      ⚠ System language not available for {self.current_model}")
            return []
        
        options = self.scrape_other_cstic_options(
            language_id, 
            "System Language",
            name_class="other-cstic__value-name",
            take_screenshot=False
        )
        
        if options:
            selected_option = next((opt for opt in options if opt.get("currently_selected")), options[0])
            return [{"language": selected_option.get("name", "English (UK)")}]
        
        return [{"language": "English (UK)"}]
    
    # ================= INTERIOR SECTION METHODS =================
    
    def scrape_interior_theme(self):
        """Scrape interior theme options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            interior_id = config.get("interior_theme_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            interior_id = config.get("interior_theme_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            interior_id = config.get("interior_theme_id")
        else:
            return []
        
        if not interior_id:
            print(f"      ⚠ Interior theme not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            interior_id, 
            "Interior Theme",
            name_class="specification-cstic__value-header",
            take_screenshot=False,
            special_case=True
        )
    
    def scrape_interior_color(self):
        """Scrape interior color options WITH screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            color_id = config.get("interior_color_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            color_id = config.get("interior_color_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            color_id = config.get("interior_color_id")
        else:
            return []
        
        if not color_id:
            print(f"      ⚠ Interior color not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            color_id, 
            "Interior Colour",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=True
        )
    
    def scrape_steering_wheel(self):
        """Scrape steering wheel options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            steering_id = config.get("steering_wheel_id")
            return self.scrape_other_cstic_options(
                steering_id, 
                "Steering Wheel",
                name_class="other-cstic__text",
                has_swatch_image=True,
                take_screenshot=False
            )
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            steering_type = self.scrape_steering_wheel_type()
            steering_grip = self.scrape_steering_wheel_grip()
            return {
                "steering_wheel_type": steering_type, 
                "steering_wheel_grip": steering_grip
            }
        elif self.current_model in ["750S", "750S SPIDER"]:
            steering_id = config.get("steering_wheel_id")
            return self.scrape_other_cstic_options(
                steering_id, 
                "Steering Wheel",
                name_class="other-cstic__text",
                has_swatch_image=True,
                take_screenshot=False
            )
        else:
            return []
    
    def scrape_steering_wheel_type(self):
        """Scrape steering wheel type options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        steering_type_id = config.get("steering_wheel_type_id")
        
        if not steering_type_id:
            return []
        
        return self.scrape_other_cstic_options(
            steering_type_id, 
            "Steering Wheel Type",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_steering_wheel_grip(self):
        """Scrape steering wheel grip options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        steering_grip_id = config.get("steering_wheel_grip_id")
        
        if not steering_grip_id:
            return []
        
        return self.scrape_other_cstic_options(
            steering_grip_id, 
            "Steering Wheel Finish",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_seat_belts(self):
        """Scrape seat belts options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            belts_id = config.get("seat_belts_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            belts_id = config.get("seat_belts_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            belts_id = config.get("seat_belts_id")
        else:
            return []
        
        if not belts_id:
            print(f"      ⚠ Seat belts not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            belts_id, 
            "Seat Belts",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_seat_back(self):
        """Scrape seat back options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        seat_back_id = config.get("seat_back_id")
        
        if not seat_back_id:
            print(f"      ⚠ Seat back not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            seat_back_id, 
            "Seat Back",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_sill_finishers(self):
        """Scrape sill finishers options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            sill_id = config.get("sill_finishers_id")
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            sill_id = config.get("sill_finishers_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            sill_id = config.get("sill_finishers_id")
        else:
            return []
        
        if not sill_id:
            print(f"      ⚠ Sill finishers not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            sill_id, 
            "Sill Finishers",
            name_class="other-cstic__text",
            has_swatch_image=True,
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_luggage_bay_floor(self):
        """Scrape luggage bay floor options WITHOUT screenshots - FIXED"""
        config = self.get_model_config(self.current_model)
        luggage_id = config.get("luggage_bay_floor_id")
        
        if not luggage_id:
            print(f"      ⚠ Luggage bay floor not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            luggage_id, 
            "Luggage Bay Floor",
            name_class="other-cstic__text",
            has_swatch_image=True,
            take_screenshot=False
        )
    
    def scrape_armrest(self):
        """Scrape armrest options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            armrest_id = config.get("armrest_id")
            option_name = "Armrest with McLaren Branding"
        elif self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            armrest_id = config.get("armrest_id")
            option_name = "Armrest with McLaren Branding"
        else:
            return []
        
        if not armrest_id:
            print(f"      ⚠ Armrest not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(armrest_id, option_name, has_image=True)
    
    def scrape_track_plaque(self):
        """Scrape McLaren track record plaque options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model == "GTS":
            plaque_id = config.get("track_plaque_id")
        else:
            return []
        
        if not plaque_id:
            print(f"      ⚠ Track plaque not available for {self.current_model}")
            return []
        
        return self.scrape_toggle_option(plaque_id, "McLaren Track Record Plaque", has_image=False)
    
    def scrape_seat_type(self):
        """Scrape seat type options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            seat_id = config.get("seat_type_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            seat_id = config.get("seat_type_id")
        else:
            return []
        
        if not seat_id:
            print(f"      ⚠ Seat type not available for {self.current_model}")
            return []
        
        return self.scrape_other_cstic_options(
            seat_id, 
            "Seat Type",
            name_class="other-cstic__value-name",
            has_product_image=True,
            take_screenshot=False
        )
    
    def scrape_floor_mats(self):
        """Scrape McLaren branded floor mats options WITHOUT screenshots"""
        config = self.get_model_config(self.current_model)
        if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            mats_id = config.get("floor_mats_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            mats_id = config.get("floor_mats_id")
        else:
            return []
        
        if not mats_id:
            print(f"      ⚠ Floor mats not available for {self.current_model}")
            return []
        
        if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            return self.scrape_other_cstic_options(
                mats_id, 
                "McLaren Branded Floor Mats",
                name_class="other-cstic__value-name",
                has_product_image=True,
                take_screenshot=False
            )
        else:
            return self.scrape_toggle_option(mats_id, "McLaren Branded Floor Mats", has_image=False)
    
    # ================= ENTERTAINMENT SECTION =================
    
    def scrape_audio(self):
        """Scrape audio options WITHOUT screenshots - FIXED TO PREVENT DATA MIXING"""
        config = self.get_model_config(self.current_model)
        if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            audio_id = config.get("audio_id")
        elif self.current_model in ["750S", "750S SPIDER"]:
            audio_id = config.get("audio_id")
        else:
            return []
        
        if not audio_id:
            print(f"      ⚠ Audio not available for {self.current_model}")
            return []
        
        try:
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[class*='close'], button[aria-label*='close']")
            for btn in close_buttons:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
        except:
            pass
        
        if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
            return self.scrape_other_cstic_options(
                audio_id, 
                "Audio",
                name_class="other-cstic__text",
                has_swatch_image=True,
                take_screenshot=False
            )
        else:
            return self.scrape_other_cstic_options(
                audio_id, 
                "Audio",
                name_class="other-cstic__value-name",
                has_product_image=True,
                take_screenshot=False
            )
    
    def handle_popups(self):
        """Handle common popups"""
        print("  Checking for popups...")
        time.sleep(2)
        
        close_selectors = [
            "button[aria-label*='close']",
            "button[class*='close']",
            ".cookie-accept",
            "#accept-cookies"
        ]
        
        for selector in close_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        print("    Closed popup")
                        time.sleep(1)
            except:
                continue

    def process_model(self, model):
        """Process a single car model with organized structure"""
        print(f"\n📦 Processing: {model['name']}")
        self.current_model = model['name']
        
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
            self.wait_for_3d_model()
            
            print("\n  Starting category scraping...")
            
            # Section 1: Color Section (with screenshots)
            print("\n  --- Section 1: Color ---")
            exterior_colors = self.scrape_exterior_colors()
            
            print("\n  --- Opening Additional Features ---")
            self.click_summary_button()
            
            # Section 2: Wheels & Brakes
            print("\n  --- Section 2: Wheels & Brakes ---")
            wheels = self.scrape_wheels()
            brakes = self.scrape_brakes()
            wheel_bolts = self.scrape_wheel_bolts()
            
            # Section 3: Exterior
            print("\n  --- Section 3: Exterior ---")
            config = self.get_model_config(self.current_model)
            
            # Model-specific exterior features
            if self.current_model == "GTS":
                wheel_finish = self.scrape_wheel_finish()
                
                bright_pack = self.scrape_bright_pack()
                exterior_details = self.scrape_exterior_details_pack()
                underbody_carbon = self.scrape_underbody_carbon_pack()
                stealth_badge = self.scrape_stealth_badge_pack()
                gts_side_badge = self.scrape_gts_side_badge()
                roof = self.scrape_roof_colors()
                privacy_glass = self.scrape_privacy_glass()
                exhaust_type = self.scrape_exhaust_type()
                exhaust_finisher = self.scrape_exhaust_finisher()
                
                exterior_section = {
                    "bright_pack": bright_pack,
                    "exterior_details_carbon_fibre_pack": exterior_details,
                    "underbody_carbon_fibre_pack": underbody_carbon,
                    "stealth_badge_pack": stealth_badge,
                    "gts_side_badges": gts_side_badge,
                    "roof": roof,
                    "privacy_glass": privacy_glass,
                    "exhaust_type": exhaust_type,
                    "exhaust_finisher": exhaust_finisher
                }
                
                wheels_brakes_section = {
                    "wheels": wheels,
                    "brakes": brakes,
                    "lightweight_titanium_wheel_bolts": wheel_bolts,
                    "wheel_finish": wheel_finish
                }
                
            elif self.current_model == "ARTURA":
                wheel_finish = self.scrape_wheel_finish_artura()
                
                tyre_type = self.scrape_tyre_type()
                bright_pack = self.scrape_bright_pack()
                stealth_badge = self.scrape_stealth_badge_pack()
                underbody_carbon = self.scrape_underbody_carbon_pack()
                exterior_details = self.scrape_exterior_details_pack()
                mirror_casings = self.scrape_mirror_casings()
                front_fender_louvres = self.scrape_front_fender_louvres()
                exhaust_type = self.scrape_exhaust_type()
                exhaust_finisher = self.scrape_exhaust_finisher()
                roof = self.scrape_roof_colors()
                engine_cover = self.scrape_engine_cover()
                thermal_windscreen = self.scrape_thermal_windscreen()
                rear_spoiler = self.scrape_rear_spoiler()
                
                exterior_section = {
                    "bright_pack": bright_pack,
                    "stealth_badge_pack": stealth_badge,
                    "underbody_carbon_fibre_pack": underbody_carbon,
                    "exterior_details_carbon_fibre_pack": exterior_details,
                    "door_mirror_casings": mirror_casings,
                    "front_fender_louvres": front_fender_louvres,
                    "exhaust_type": exhaust_type,
                    "exhaust_hot_vee_finishers": exhaust_finisher,
                    "roof": roof,
                    "engine_cover": engine_cover,
                    "thermal_insulated_windscreen": thermal_windscreen,
                    "rear_spoiler_gloss_carbon_fibre": rear_spoiler
                }
                
                wheels_brakes_section = {
                    "wheels": wheels,
                    "brakes": brakes,
                    "lightweight_titanium_wheel_bolts": wheel_bolts,
                    "tyre_type": tyre_type,
                    "wheel_finish": wheel_finish
                }
                
            elif self.current_model == "ARTURA SPIDER":
                wheel_finish = self.scrape_wheel_finish_artura()
                
                tyre_type = self.scrape_tyre_type()
                bright_pack = self.scrape_bright_pack()
                stealth_badge = self.scrape_stealth_badge_pack()
                underbody_carbon = self.scrape_underbody_carbon_pack()
                exterior_details = self.scrape_exterior_details_pack()
                mirror_casings = self.scrape_mirror_casings()
                front_fender_louvres = self.scrape_front_fender_louvres()
                tonneau = self.scrape_tonneau()
                exhaust_type = self.scrape_exhaust_type()
                exhaust_finisher = self.scrape_exhaust_finisher()
                roof = self.scrape_roof_colors()
                thermal_windscreen = self.scrape_thermal_windscreen()
                rear_spoiler = self.scrape_rear_spoiler()
                
                exterior_section = {
                    "bright_pack": bright_pack,
                    "stealth_badge_pack": stealth_badge,
                    "underbody_carbon_fibre_pack": underbody_carbon,
                    "exterior_details_carbon_fibre_pack": exterior_details,
                    "door_mirror_casings": mirror_casings,
                    "front_fender_louvres": front_fender_louvres,
                    "tonneau": tonneau,
                    "exhaust_type": exhaust_type,
                    "exhaust_hot_vee_finishers": exhaust_finisher,
                    "roof": roof,
                    "thermal_insulated_windscreen": thermal_windscreen,
                    "rear_spoiler_gloss_carbon_fibre": rear_spoiler
                }
                
                wheels_brakes_section = {
                    "wheels": wheels,
                    "brakes": brakes,
                    "lightweight_titanium_wheel_bolts": wheel_bolts,
                    "tyre_type": tyre_type,
                    "wheel_finish": wheel_finish
                }
                
            elif self.current_model == "750S":
                tyre_type = self.scrape_tyre_type()
                black_pack = self.scrape_black_pack()
                stealth_badge = self.scrape_stealth_badge_pack()
                underbody_carbon = self.scrape_underbody_carbon_pack()
                exterior_details = self.scrape_exterior_details_pack()
                upper_structure_carbon = self.scrape_upper_structure_carbon_pack()
                hood = self.scrape_hood_colors()
                front_fender = self.scrape_front_fender()
                exhaust_finisher = self.scrape_exhaust_finisher_750s()
                active_rear_spoiler = self.scrape_active_rear_spoiler()
                headlight_surround = self.scrape_headlight_surround()
                rear_bumper = self.scrape_rear_bumper()
                rear_bumper_ducts = self.scrape_rear_bumper_ducts()
                window_surrounds = self.scrape_window_surrounds()
                sound_comfort_windscreen = self.scrape_sound_comfort_windscreen()
                
                exterior_section = {
                    "black_pack": black_pack,
                    "stealth_badge_pack": stealth_badge,
                    "underbody_carbon_fibre_pack": underbody_carbon,
                    "exterior_details_carbon_fibre_pack": exterior_details,
                    "upper_structure_carbon_fibre_pack": upper_structure_carbon,
                    "hood": hood,
                    "front_fender": front_fender,
                    "exhaust_finisher": exhaust_finisher,
                    "active_rear_spoiler": active_rear_spoiler,
                    "headlight_surround": headlight_surround,
                    "rear_bumper": rear_bumper,
                    "rear_bumper_ducts": rear_bumper_ducts,
                    "exterior_window_surrounds": window_surrounds,
                    "sound_comfort_windscreen": sound_comfort_windscreen
                }
                
                wheels_brakes_section = {
                    "wheels": wheels,
                    "brakes": brakes,
                    "lightweight_titanium_wheel_bolts": wheel_bolts,
                    "tyre_type": tyre_type,
                    "wheel_finish": self.scrape_wheel_finish_750s(),
                    "track_brake_upgrade": self.scrape_track_brake_upgrade()
                }
                
            elif self.current_model == "750S SPIDER":
                tyre_type = self.scrape_tyre_type()
                black_pack = self.scrape_black_pack()
                stealth_badge = self.scrape_stealth_badge_pack()
                underbody_carbon = self.scrape_underbody_carbon_pack()
                exterior_details = self.scrape_exterior_details_pack()
                upper_structure_carbon = self.scrape_upper_structure_carbon_pack()
                roof_pan = self.scrape_roof_pan()
                hood = self.scrape_hood_colors()
                front_fender = self.scrape_front_fender()
                exhaust_finisher = self.scrape_exhaust_finisher_750s()
                active_rear_spoiler = self.scrape_active_rear_spoiler()
                headlight_surround = self.scrape_headlight_surround()
                rear_bumper = self.scrape_rear_bumper()
                rear_bumper_ducts = self.scrape_rear_bumper_ducts()
                sound_comfort_windscreen = self.scrape_sound_comfort_windscreen()
                
                exterior_section = {
                    "black_pack": black_pack,
                    "stealth_badge_pack": stealth_badge,
                    "underbody_carbon_fibre_pack": underbody_carbon,
                    "exterior_details_carbon_fibre_pack": exterior_details,
                    "upper_structure_carbon_fibre_pack": upper_structure_carbon,
                    "roof": roof_pan,
                    "hood": hood,
                    "front_fender": front_fender,
                    "exhaust_finisher": exhaust_finisher,
                    "active_rear_spoiler": active_rear_spoiler,
                    "headlight_surround": headlight_surround,
                    "rear_bumper": rear_bumper,
                    "rear_bumper_ducts": rear_bumper_ducts,
                    "sound_comfort_windscreen": sound_comfort_windscreen
                }
                
                wheels_brakes_section = {
                    "wheels": wheels,
                    "brakes": brakes,
                    "lightweight_titanium_wheel_bolts": wheel_bolts,
                    "tyre_type": tyre_type,
                    "wheel_finish": self.scrape_wheel_finish_750s(),
                    "track_brake_upgrade": self.scrape_track_brake_upgrade()
                }
            
            # Section 4: Interior Specification
            print("\n  --- Section 4: Interior Specification ---")
            interior_theme = self.scrape_interior_theme()
            
            # Section 5: Interior
            print("\n  --- Section 5: Interior ---")
            interior_color = self.scrape_interior_color()
            
            if self.current_model == "GTS":
                contrast_stitch = self.scrape_contrast_stitch()
                steering_wheel = self.scrape_steering_wheel()
                seat_belts = self.scrape_seat_belts()
                seat_back = self.scrape_seat_back()
                sill_finishers = self.scrape_sill_finishers()
                luggage_bay_floor = self.scrape_luggage_bay_floor()
                luggage_strap = self.scrape_luggage_retention_strap()
                armrest = self.scrape_armrest()
                track_plaque = self.scrape_track_plaque()
                interior_carbon_pack = self.scrape_interior_carbon_pack()
                
                interior_section = {
                    "interior_colour": interior_color,
                    "contrast_stitch_seat_piping": contrast_stitch,
                    "steering_wheel": steering_wheel,
                    "seat_belts": seat_belts,
                    "seat_back": seat_back,
                    "sill_finishers": sill_finishers,
                    "luggage_bay_floor": luggage_bay_floor,
                    "luggage_retention_strap": luggage_strap,
                    "armrest_with_mclaren_branding": armrest,
                    "mclaren_track_record_plaque": track_plaque,
                    "interior_details_carbon_fibre_pack": interior_carbon_pack
                }
                
                print("\n  --- Section: Option Packages ---")
                option_packages = self.scrape_option_packs()
                
                print("\n  --- Section: Options ---")
                individual_options = self.scrape_individual_options()
                
                owners_manual = self.scrape_owners_manual()
                system_language = self.scrape_system_language()
                
                individual_options["owners_manual"] = owners_manual
                individual_options["system_language"] = system_language
                
            elif self.current_model == "ARTURA":
                seat_type = self.scrape_seat_type()
                seat_belts = self.scrape_seat_belts()
                steering_wheel = self.scrape_steering_wheel()
                sill_finishers = self.scrape_sill_finishers()
                floor_mats = self.scrape_floor_mats()
                armrest = self.scrape_armrest()
                
                interior_section = {
                    "interior_colour": interior_color,
                    "gloss_black_interior_finish_pack": self.scrape_gloss_black_interior_finish(),
                    "interior_details_carbon_fibre_pack": self.scrape_interior_carbon_pack_artura(),
                    "seat_type": seat_type,
                    "seat_belts": seat_belts,
                    "harness_bar": self.scrape_harness_bar(),
                    "steering_wheel_type": steering_wheel.get("steering_wheel_type", []),
                    "steering_wheel_finish": steering_wheel.get("steering_wheel_grip", []),
                    "sill_finishers": sill_finishers,
                    "mclaren_branded_floor_mats": floor_mats,
                    "armrest_with_mclaren_branding": armrest,
                    "mclaren_track_record_plaque": self.scrape_track_plaque_artura()
                }
                
                print("\n  --- Section: Option Packages ---")
                option_packages = self.scrape_option_packs_artura()
                
                print("\n  --- Section: Options ---")
                individual_options = self.scrape_individual_options_artura()
                
                individual_options["owners_manual"] = self.scrape_owners_manual_artura()
                individual_options["system_language"] = self.scrape_system_language_artura()
                
            elif self.current_model == "ARTURA SPIDER":
                seat_type = self.scrape_seat_type()
                seat_belts = self.scrape_seat_belts()
                steering_wheel = self.scrape_steering_wheel()
                sill_finishers = self.scrape_sill_finishers()
                floor_mats = self.scrape_floor_mats()
                armrest = self.scrape_armrest()
                
                interior_section = {
                    "interior_colour": interior_color,
                    "gloss_black_interior_finish_pack": self.scrape_gloss_black_interior_finish(),
                    "interior_details_carbon_fibre_pack": self.scrape_interior_carbon_pack_artura(),
                    "seat_type": seat_type,
                    "seat_belts": seat_belts,
                    "steering_wheel_type": steering_wheel.get("steering_wheel_type", []),
                    "steering_wheel_finish": steering_wheel.get("steering_wheel_grip", []),
                    "sill_finishers": sill_finishers,
                    "mclaren_branded_floor_mats": floor_mats,
                    "armrest_with_mclaren_branding": armrest,
                    "mclaren_track_record_plaque": self.scrape_track_plaque_artura()
                }
                
                print("\n  --- Section: Option Packages ---")
                option_packages = self.scrape_option_packs_artura()
                
                print("\n  --- Section: Options ---")
                individual_options = self.scrape_individual_options_artura()
                
                individual_options["owners_manual"] = self.scrape_owners_manual_artura()
                individual_options["system_language"] = self.scrape_system_language_artura()
                
            elif self.current_model == "750S":
                seat_type = self.scrape_seat_type()
                passenger_seat_position = self.scrape_passenger_seat_position()
                seat_size = self.scrape_seat_size()
                seat_belts = self.scrape_seat_belts()
                steering_wheel = self.scrape_steering_wheel()
                sill_finishers = self.scrape_sill_finishers()
                floor_mats = self.scrape_floor_mats()
                track_plaque = self.scrape_track_plaque_750s()
                
                interior_section = {
                    "interior_colour": interior_color,
                    "seat_type": seat_type,
                    "passenger_seat_position": passenger_seat_position,
                    "seat_size": seat_size,
                    "seat_belts": seat_belts,
                    "steering_wheel_finish": steering_wheel,
                    "sill_finishers": sill_finishers,
                    "double_glazed_engine_window": self.scrape_double_glazed_engine_window(),
                    "mclaren_branded_floor_mats": floor_mats,
                    "mclaren_track_record_plaque": track_plaque
                }
                
            elif self.current_model == "750S SPIDER":
                seat_type = self.scrape_seat_type()
                passenger_seat_position = self.scrape_passenger_seat_position()
                seat_size = self.scrape_seat_size()
                seat_belts = self.scrape_seat_belts()
                steering_wheel = self.scrape_steering_wheel()
                sill_finishers = self.scrape_sill_finishers()
                floor_mats = self.scrape_floor_mats()
                track_plaque = self.scrape_track_plaque_750s()
                
                interior_section = {
                    "interior_colour": interior_color,
                    "gloss_finish_visual_carbon_fibre_extended_upper_trim": 
                        self.scrape_gloss_finish_visual_carbon_fibre_extended_upper_trim(),
                    "seat_type": seat_type,
                    "passenger_seat_position": passenger_seat_position,
                    "seat_size": seat_size,
                    "seat_belts": seat_belts,
                    "steering_wheel_finish": steering_wheel,
                    "sill_finishers": sill_finishers,
                    "mclaren_branded_floor_mats": floor_mats,
                    "mclaren_track_record_plaque": track_plaque
                }
            
            # Section 6: Entertainment
            print("\n  --- Section 6: Entertainment ---")
            if self.current_model in ["ARTURA", "ARTURA SPIDER", "750S", "750S SPIDER"]:
                audio = self.scrape_audio()
                entertainment_section = {
                    "audio": audio
                }
            else:
                entertainment_section = {}
            
            # Safety & Security Section for 750S models
            if self.current_model in ["750S", "750S SPIDER"]:
                print("\n  --- Section: Safety & Security ---")
                safety_security = self.scrape_safety_security_packs_750s()
            
            # Practical Section for 750S models
            if self.current_model in ["750S", "750S SPIDER"]:
                print("\n  --- Section: Practical ---")
                practical_options = self.scrape_practical_options_750s()
                
                practical_options["owners_manual"] = self.scrape_owners_manual_750s()
                practical_options["system_language"] = self.scrape_system_language_750s()
            
            # Organize all data
            configuration_data = {
                "configuration_name": "Default Configuration",
                "sections": {
                    "color": exterior_colors,
                    "wheels_brakes": wheels_brakes_section,
                    "exterior": exterior_section,
                    "interior_specification": {
                        "interior_theme": interior_theme
                    },
                    "interior": interior_section
                }
            }
            
            if entertainment_section:
                configuration_data["sections"]["entertainment"] = entertainment_section
            
            if self.current_model == "GTS":
                configuration_data["sections"]["option_packages"] = option_packages
                configuration_data["sections"]["options"] = individual_options
            
            if self.current_model in ["ARTURA", "ARTURA SPIDER"]:
                configuration_data["sections"]["option_packages"] = option_packages
                configuration_data["sections"]["options"] = individual_options
            
            if self.current_model in ["750S", "750S SPIDER"]:
                configuration_data["sections"]["safety_security"] = safety_security
                configuration_data["sections"]["practical"] = practical_options
            
            model_data["configurations"].append(configuration_data)
            
            # Print summary
            print(f"\n  ✅ Successfully processed {model['name']}")
            print(f"     Color options: {len(exterior_colors)}")
            print(f"     Wheels: {len(wheels)}")
            print(f"     Brakes: {len(brakes)}")
            print(f"     Exterior features: {len(exterior_section)}")
            print(f"     Interior features: {len(interior_section)}")
            if entertainment_section:
                print(f"     Entertainment features: {len(entertainment_section)}")
            if self.current_model == "GTS" and 'option_packages' in locals() and option_packages:
                print(f"     Option packages: {len(option_packages)}")
            if self.current_model == "GTS" and 'individual_options' in locals() and individual_options:
                print(f"     Individual options: {len(individual_options)}")
            if self.current_model in ["ARTURA", "ARTURA SPIDER"] and 'option_packages' in locals() and option_packages:
                print(f"     Option packages: {len(option_packages)}")
            if self.current_model in ["ARTURA", "ARTURA SPIDER"] and 'individual_options' in locals() and individual_options:
                print(f"     Individual options: {len(individual_options)}")
            if self.current_model in ["750S", "750S SPIDER"] and 'safety_security' in locals() and safety_security:
                print(f"     Safety & Security options: {len(safety_security)}")
            if self.current_model in ["750S", "750S SPIDER"] and 'practical_options' in locals() and practical_options:
                print(f"     Practical options: {len(practical_options)}")
            
            return model_data
            
        except Exception as e:
            print(f"  ❌ Error processing model: {e}")
            import traceback
            traceback.print_exc()
            return model_data
    
    def save_json(self, data):
        """Save data to JSON file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Data saved to {self.output_file}")
    
    def run(self):
        """Run the scraper"""
        print("🚀 Starting McLaren Car Scraper")
        print("=" * 60)
        
        try:
            models = self.load_initial_models()
            print(f"Loaded {len(models)} model(s) to scrape")
            
            for model_idx, model in enumerate(models):
                print(f"\n📋 Processing model {model_idx+1}/{len(models)}")
                model_data = self.process_model(model)
                
                self.data.append(model_data)
                self.save_json(self.data)
                
                print(f"\n✅ Completed: {model['name']}")
            
            print("\n" + "=" * 60)
            print("🎉 All scraping completed!")
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

if __name__ == "__main__":
    scraper = McLarenScraper()
    scraper.run()