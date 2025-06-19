# schedule_extractor_utils.py
# This file contains utility functions for the schedule extractor script.
# Utils Version: 0.0.5 # Added refactored functions for browser setup, login, minimize sequence, and OCR

import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import psutil # For checking running processes

# Import configuration variables here, as these utility functions will need them
# Note: config is imported with '*' to keep functions concise, assume necessary vars are present
from schedule_extractor_config import (
    CHROMEDRIVER_PATH, CHROME_MAJOR_VERSION, CHROME_USER_DATA_DIR,
    LOGIN_USERNAME_LOCATOR, LOGIN_PASSWORD_LOCATOR, LOGIN_BUTTON_LOCATOR,
    FLUTTER_VIEW_LOCATOR, SECURITY_CHECK_CONTINUE_BUTTON_LOCATOR,
    SCHEDULE_MINIMIZE_PRIMARY_X, SCHEDULE_MINIMIZE_PRIMARY_Y,
    SCHEDULE_MINIMIZE_SECONDARY_X, SCHEDULE_MINIMIZE_SECONDARY_Y,
    DRAG_AMOUNT_Y_PIXELS,
    SCREENSHOT_OUTPUT_DIR, SCREENSHOT_BASE_NAME,
    ENABLE_SCREENSHOT_CROPPING, CROP_COORDINATES,
    ENABLE_IMAGE_PREPROCESSING, TESSERACT_PATH
)
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io
import pytesseract # For OCR


def check_for_running_chrome_processes():
    """
    Checks if any Chrome processes are running and prints a warning.
    Returns True if processes are found, False otherwise.
    """
    print("Checking for running Chrome processes before launch...")
    found_chrome_process = False
    for proc in psutil.process_iter(['name', 'exe', 'pid']): # Request 'pid' explicitly
        try:
            pinfo = proc.info # Get process info dict
            
            # Get raw values, then safely convert to lowercase strings
            process_name_raw = pinfo.get('name')
            process_exe_raw = pinfo.get('exe')

            process_name = process_name_raw.lower() if process_name_raw is not None else ''
            process_exe = process_exe_raw.lower() if process_exe_raw is not None else ''

            if 'chrome.exe' in process_name or (process_exe and process_exe.endswith('chrome.exe')):
                print(f"\n{'='*70}")
                print(f"!!!!!!!  WARNING: CHROME BROWSER ALREADY RUNNING  !!!!!!!")
                # Use proc.pid directly for PID, and the safely converted strings for name/exe
                print(f"!!! Found process: PID={proc.pid}, Name='{process_name}', Executable='{process_exe}' !!!")
                print("!!! Please close ALL Chrome browser windows and    !!!")
                print("!!! end any lingering 'Google Chrome' or 'chromedriver.exe' processes in Task Manager. !!!")
                print("!!! Exiting to prevent conflicts and ensure a clean automated launch. !!!")
                print("!!! (This is to prevent conflicts and ensure a clean automated launch.) !!!")
                print(f"{'='*70}\n")
                found_chrome_process = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Handle cases where process disappears or access is denied during iteration
            continue
    return found_chrome_process


def initialize_undetected_chrome_driver():
    """
    Sets up Chrome options and initializes undetected_chromedriver.
    Returns the initialized driver instance.
    """
    print("Setting up Chrome browser options...")
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu-shader_disk_cache")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-service-autorun")
    chrome_options.add_argument("--password-store=basic")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-client-side-phishing_detection")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--enable-automation")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-notifications")

    service = Service(CHROMEDRIVER_PATH)
    
    print("Initializing undetected_chromedriver...")
    driver = uc.Chrome(service=service, options=chrome_options, user_data_dir=CHROME_USER_DATA_DIR, version_main=CHROME_MAJOR_VERSION)
    print("Chrome browser launched successfully by the script, with undetected_chromedriver.")
    return driver


def perform_login(driver, username, password):
    """
    Performs login steps for the web application.
    Assumes driver is already navigated to the login page.
    """
    print("\n--- Performing Login ---")
    if not (LOGIN_USERNAME_LOCATOR and LOGIN_PASSWORD_LOCATOR and LOGIN_BUTTON_LOCATOR):
        print("ERROR: Login element locators are not defined in config. Cannot automate login.")
        return False

    try:
        print("Attempting to find and enter credentials...")
        username_field = WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(LOGIN_USERNAME_LOCATOR)
        )
        username_field.send_keys(username)
        print("Username entered.")

        password_field = WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(LOGIN_PASSWORD_LOCATOR)
        )
        password_field.send_keys(password)
        print("Password entered.")

        login_button = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable(LOGIN_BUTTON_LOCATOR)
        )
        login_button.click()
        print("Login button clicked. Waiting for intermediate page or app to load...")
        time.sleep(7) # Initial pause after login click

        # Handle potential security check page
        if SECURITY_CHECK_CONTINUE_BUTTON_LOCATOR:
            print("\n--- Checking for Security Check 'Continue' button ---")
            try:
                continue_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(SECURITY_CHECK_CONTINUE_BUTTON_LOCATOR)
                )
                print("Security Check 'Continue' button found. Clicking it...")
                continue_button.click()
                print("'Continue' button clicked. Waiting for page to load after security check...")
                time.sleep(10)
            except Exception as e:
                print(f"No security check 'Continue' button found within timeout, or error clicking it: {e}")
                print("Proceeding without clicking a security check button.")
        else:
            print("No SECURITY_CHECK_CONTINUE_BUTTON_LOCATOR defined in config. Skipping security check click.")
        return True
    except Exception as e:
        print(f"Error during login process: {e}")
        return False


def perform_minimization_sequence(driver, flutter_view_element):
    """
    Performs the two-step minimization sequence for the schedule view.
    Assumes the driver is on the schedule view with the primary graphic.
    """
    print("\n--- Starting Minimization Sequence ---")
    try:
        # --- PRIMARY MINIMIZE: Minimize the large calendar graphic ---
        print(f"\n--- PERFORMING PRIMARY MINIMIZE: Clicking at ({SCHEDULE_MINIMIZE_PRIMARY_X}, {SCHEDULE_MINIMIZE_PRIMARY_Y}) ---")
        try:
            # Re-locate flutter_view_element, as it might have become stale
            flutter_view_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(FLUTTER_VIEW_LOCATOR)
            )
            perform_swipe_on_element(
                driver,
                flutter_view_element,
                SCHEDULE_MINIMIZE_PRIMARY_X,
                SCHEDULE_MINIMIZE_PRIMARY_Y,
                0, 0 # Pure tap
            )
            print("    Primary minimize click executed. Waiting for graphic to disappear...")
            time.sleep(3) # Give graphic time to disappear

        except Exception as e:
            print(f"    Error during PRIMARY minimize click: {e}")
            print("    Primary minimize failed. Cannot proceed to secondary minimize.")
            return False # Indicate failure

        # Only proceed to secondary if primary minimize was attempted (or succeeded)
        # We need to re-locate flutter_view_element before secondary minimize
        flutter_view_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(FLUTTER_VIEW_LOCATOR)
        )

        # --- SECONDARY MINIMIZE: Minimize the subsequent element ---
        print(f"\n--- PERFORMING SECONDARY MINIMIZE: Clicking at ({SCHEDULE_MINIMIZE_SECONDARY_X}, {SCHEDULE_MINIMIZE_SECONDARY_Y}) ---")
        try:
            perform_swipe_on_element(
                driver,
                flutter_view_element,
                SCHEDULE_MINIMIZE_SECONDARY_X,
                SCHEDULE_MINIMIZE_SECONDARY_Y,
                0, 0 # Pure tap
            )
            print("    Secondary minimize click executed. Waiting for element to disappear...")
            time.sleep(3) # Give element time to disappear

        except Exception as e:
            print(f"    Error during SECONDARY minimize click: {e}")
            print("    Secondary minimize failed.")
            return False # Indicate failure
        
        return True # Indicate success
    except Exception as e:
        print(f"Error during overall minimization sequence: {e}")
        return False


def drag_element_to_scroll(driver, element, drag_y_pixels, start_x_offset, start_y_offset_ratio):
    """
    Simulates a mouse drag/swipe on an element to cause scrolling.
    drag_y_pixels: positive to drag downwards, negative to drag upwards.
    start_x_offset: X coordinate relative to the element's top-left corner to start the drag.
    start_y_offset_ratio: Y coordinate relative to the element's height (0.0-1.0) to start the drag.
    """
    print(f"Attempting to drag element for scrolling by {drag_y_pixels} pixels.")
    action = ActionChains(driver)

    element_location = element.location # Top-left corner of the element relative to the viewport
    element_size = element.size      # Width and height of the element
    
    # Calculate absolute coordinates for the start of the drag
    start_x_abs = element_location['x'] + start_x_offset
    start_y_abs = element_location['y'] + (element_size['height'] * start_y_offset_ratio)

    # Move pointer to the absolute start point
    action.w3c_actions.pointer_action.move_to_location(start_x_abs, start_y_abs)
    action.click_and_hold()
    # Now drag (move by offset) relative to where the pointer currently is
    action.move_by_offset(0, drag_y_pixels) 
    action.release()
    action.perform()
    
    print("Drag attempt executed.")
    time.sleep(3) # Give the element time to render after drag


def perform_swipe_on_element(driver, element, start_x_offset, start_y_offset, swipe_x_pixels, swipe_y_pixels):
    """
    Performs a swipe action on an element, starting at a specific offset within the element.
    start_x_offset: X coordinate relative to the element's top-left corner to start the swipe.
    start_y_offset: Y coordinate relative to the element's top-left corner to start the swipe.
    swipe_x_pixels: The horizontal distance to swipe (positive for right, negative for left).
    swipe_y_pixels: The vertical distance to swipe (positive for down, negative for up).
    """
    print(f"Attempting to swipe element from offset ({start_x_offset}, {start_y_offset}) by ({swipe_x_pixels}, {swipe_y_pixels}) pixels.")
    action = ActionChains(driver)

    element_location = element.location # Top-left corner of the element relative to the viewport
    
    # Calculate absolute coordinates for the start of the swipe
    start_x_abs = element_location['x'] + start_x_offset
    start_y_abs = element_location['y'] + start_y_offset

    # Move pointer to the absolute start point
    action.w3c_actions.pointer_action.move_to_location(start_x_abs, start_y_abs)
    action.click_and_hold()
    # Now drag (move by offset) relative to where the pointer currently is
    action.move_by_offset(swipe_x_pixels, swipe_y_pixels) 
    action.release()
    action.perform()
    
    print("Swipe attempt executed.")
    time.sleep(3) # Give the element time to render after swipe


def capture_and_ocr_segment(driver, flutter_view_element, segment_count):
    """
    Captures a screenshot of the flutter_view_element, crops it, and performs OCR.
    Returns a list of unique extracted text lines.
    """
    print(f"\n--- Capture Attempt {segment_count + 1} ---")
    screenshot_file_full_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"{SCREENSHOT_BASE_NAME}_{segment_count}.png")

    screenshot_data = None
    if flutter_view_element:
        try:
            screenshot_data = flutter_view_element.screenshot_as_png
            print(f"Screenshot of Flutter view element taken successfully for segment {segment_count}.")
        except Exception as e:
            print(f"WARNING: Could not take screenshot of specific Flutter element for segment {segment_count}: {e}")
            print("Falling back to full page screenshot.")
            screenshot_data = driver.get_screenshot_as_png()
    else:
        print("Flutter view element not found, taking full page screenshot.")
        screenshot_data = driver.get_screenshot_as_png()

    # Save the screenshot data to a file for manual inspection
    with open(screenshot_file_full_path, 'wb') as f:
        f.write(screenshot_data)
    print(f"Screenshot saved to: {screenshot_file_full_path}")

    # Perform OCR
    current_extracted_text_lines = []
    if screenshot_data:
        try:
            img = Image.open(io.BytesIO(screenshot_data))

            if ENABLE_SCREENSHOT_CROPPING:
                print(f"Cropping image using coordinates: {CROP_COORDINATES}")
                img = img.crop(CROP_COORDINATES)

            if ENABLE_IMAGE_PREPROCESSING:
                print("Applying image pre-processing...")
                img = img.convert("L") # Grayscale
                img = img.point(lambda x: 0 if x < 128 else 255, '1') # Corrected syntax

            extracted_text = pytesseract.image_to_string(img).strip()
            current_extracted_text_lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]

            print(f"OCR performed. Extracted lines count for current segment: {len(current_extracted_text_lines)}.")
            return current_extracted_text_lines

        except FileNotFoundError:
            print(f"Error: Tesseract is not installed or not found at '{TESSERACT_PATH}'. "
                    "Please install Tesseract OCR and configure its path correctly.")
        except pytesseract.TesseractNotFoundError:
            print(f"Error: Tesseract executable not found. Please ensure it's installed "
                    f"and its path is correctly set in TESSERACT_PATH or in your system's PATH.")
        except Exception as e:
            print(f"An error occurred during image processing or OCR for segment {segment_count}: {e}")
    return []

# EOF