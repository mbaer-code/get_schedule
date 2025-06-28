# =============================================================================
# schedule_extractor_utils.py
# -----------------------------------------------------------------------------
# Utility functions for schedule_extractor.py.
# Contains helpers for browser process checks, Chrome driver initialization,
# login automation, UI interactions, screenshot capture, and OCR processing.
#
# Author: Martin Baer
# Version: 0.0.80
# Created: 2024-06-26
# License: MIT
# -----------------------------------------------------------------------------
# Notes:
#   - Designed to be imported by schedule_extractor.py.
#   - Update or extend functions as needed for your workflow.
# =============================================================================

import os
import subprocess
import time

def check_for_running_chrome_processes():
    """Check if Chrome is running and prompt the user to close it if so."""
    if os.name == "nt":
        tasks = subprocess.check_output('tasklist', shell=True).decode()
        if "chrome.exe" in tasks:
            print("Please close all Chrome windows before running this script.")
            input("Press ENTER after closing Chrome...")
            return True
    else:
        try:
            tasks = subprocess.check_output(['pgrep', 'chrome'])
            if tasks:
                print("Please close all Chrome windows before running this script.")
                input("Press ENTER after closing Chrome...")
                return True
        except subprocess.CalledProcessError:
            pass
    return False

def initialize_undetected_chrome_driver():
    """Initialize and return an undetected Chrome driver instance."""
    import undetected_chromedriver as uc
    from schedule_extractor_config import CHROMEDRIVER_PATH
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    driver = uc.Chrome(driver_executable_path=CHROMEDRIVER_PATH, options=options)
    return driver

def perform_login(driver, username, password):
    """Stub for login automation if needed in the future."""
    # This function is not used in the new flow, but kept for compatibility.
    return True

def perform_minimization_sequence(driver):
    """Stub for any UI minimization steps needed after login."""
    pass

def drag_element_to_scroll(driver, element, amount_y):
    """Deprecated: Use mouse click to advance instead of drag/swipe."""
    pass

def capture_and_ocr_segment(driver, element, attempt_num):
    """Capture a screenshot of the element and perform OCR."""
    import pytesseract
    from PIL import Image
    import io

    screenshot_path = f"screenshots/schedule_segment_{attempt_num}.png"
    element.screenshot(screenshot_path)
    print(f"Captured screenshot: {screenshot_path}")

    # OCR processing
    try:
        img = Image.open(screenshot_path)
        text = pytesseract.image_to_string(img)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines
    except Exception as e:
        print(f"OCR failed: {e}")
        return []

def perform_mouse_click_on_element(driver, element, x_offset, y_offset):
    """Clicks at a specific offset within a given element."""
    from selenium.webdriver.common.action_chains import ActionChains
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(element, x_offset, y_offset).click().perform()
    print(f"Mouse click performed at offset ({x_offset}, {y_offset}) within element.")