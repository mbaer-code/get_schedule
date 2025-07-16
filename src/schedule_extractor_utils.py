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

import csv
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

# Import psutil for robust process management
import psutil

def is_chrome_running():
    """
    Checks if any Google Chrome or ChromeDriver process is currently running using psutil.
    Returns True if any are found, False otherwise.
    """
    for proc in psutil.process_iter(['name']):
        try:
            process_name = proc.info['name'].lower()
            if 'chrome.exe' in process_name or \
               'google chrome' in process_name or \
               'chromedriver.exe' in process_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process may have terminated between check and access, or access denied
            continue
    return False

def kill_chrome_processes():
    """
    Terminates all Google Chrome and ChromeDriver processes found using psutil.
    Provides feedback on termination status.
    """
    print("Checking for and terminating existing Chrome/ChromeDriver processes...")
    killed_any = False
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            process_name = proc.info['name'].lower()
            if 'chrome.exe' in process_name or \
               'chromedriver.exe' in process_name or \
               'google chrome' in process_name:
                print(f"Terminating process: {proc.info['name']} (PID: {proc.info['pid']})")
                proc.terminate() # Request graceful termination
                killed_any = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if killed_any:
        print("Waiting for processes to terminate...")
        time.sleep(2) # Give some time for processes to actually terminate

        # Verify if any Chrome processes are still running after termination attempt
        if is_chrome_running():
            print("Warning: Some Chrome processes might still be running after termination attempt.")
            print("Consider using 'proc.kill()' for a more forceful termination if issues persist.")
        else:
            print("All detected Chrome/ChromeDriver processes have been terminated.")
    else:
        print("No Chrome/ChromeDriver processes were found running.")

# The original check_for_running_chrome_processes is now replaced by the psutil ones.
# You can remove the old one entirely or rename it if you still need it for some reason.
# For simplicity and automation, the new psutil functions are preferred.
# def check_for_running_chrome_processes():
#     """Check if Chrome is running and prompt the user to close it if so."""
#     if os.name == "nt":
#         tasks = subprocess.check_output('tasklist', shell=True).decode()
#         if "chrome.exe" in tasks:
#             print("Please close all Chrome windows before running this script.")
#             input("Press ENTER after closing Chrome...")
#             return True
#     else:
#         try:
#             tasks = subprocess.check_output(['pgrep', 'chrome'])
#             if tasks:
#                 print("Please close all Chrome windows before running this script.")
#                 input("Press ENTER after closing Chrome...")
#                 return True
#         except subprocess.CalledProcessError:
#             pass
#     return False

def initialize_undetected_chrome_driver(options=None):
    import undetected_chromedriver as uc
    from schedule_extractor_config import CHROMEDRIVER_PATH # Ensure this is correctly imported or passed
    if options is None:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
    driver = uc.Chrome(driver_executable_path=CHROMEDRIVER_PATH, options=options)
    return driver

def perform_login(driver, username, password):
    print("Starting perform_login...")
    try:
        username_field = driver.find_element(By.ID, "inputUsername")
        password_field = driver.find_element(By.ID, "inputPassword")
        username_field.clear()
        username_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
        # Use the correct login button ID (case-sensitive: buttonSignOn)
        login_button = driver.find_element(By.ID, "buttonSignOn")
        login_button.click()
        print("Login form submitted.")
    except Exception as e:
        print(f"Error during perform_login: {e}")

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

COLUMN_NAMES = [
    'png_filename', 'username', 'store_number', 'weekday', 'month', 'date',
    'shift_start', 'meal_start', 'meal_end', 'shift_end', 'department'
]

def extract_username(text):
    # Find first occurrence of a name followed by a single uppercase letter
    match = re.search(r'\b([A-Z][a-zA-Z]*) ([A-Z])\b', text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return ''

def parse_ocr_csv(csv_path):
    time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
    results = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            text = row['ocr_text']
            if "not assigned" in text.lower() or "not scheduled" in text.lower():
                continue

            png_filename = row['filename']
            username = extract_username(text)
            store_number = re.search(r'#\d{4}', text)
            store_number = store_number.group(0) if store_number else ''
            weekday = re.search(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b', text)
            weekday = weekday.group(0) if weekday else ''
            month = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', text)
            month = month.group(0) if month else ''
            date = re.search(r'\b([12][0-9]|3[01]|[1-9])\b', text)
            date = date.group(0) if date else ''

            # Extract all time values
            times = time_pattern.findall(text)
            shift_start = times[0] if len(times) > 0 else ''
            meal_start = times[1] if len(times) > 1 else ''
            meal_end = ''
            shift_end = times[-1] if times else ''

            # Find meal_end as the next time 30 or 60 mins after meal_start
            def parse_time(t):
                return datetime.strptime(t.strip().upper(), "%I:%M %p")
            if meal_start:
                try:
                    meal_start_dt = parse_time(meal_start)
                    for t in times[2:]:
                        t_dt = parse_time(t)
                        diff = (t_dt - meal_start_dt).total_seconds() / 60
                        if diff in (30, 60):
                            meal_end = t
                            break
                except Exception:
                    meal_end = times[2] if len(times) > 2 else ''

            # Department: match "0xx - " followed by department name, stopping before any trailing number
            dept_match = re.search(r'0\d{2}\s*-\s*[A-Za-z &]+', text)
            department = dept_match.group(0).strip() if dept_match else ''

            entry = {
                'png_filename': png_filename,
                'username': username,
                'store_number': store_number,
                'weekday': weekday,
                'month': month,
                'date': date,
                'shift_start': shift_start,
                'meal_start': meal_start,
                'meal_end': meal_end,
                'shift_end': shift_end,
                'department': department
            }
            results.append(entry)
    return results

# The `driver.quit()` calls at the end of the original utils file
# are typically handled in the main script's `finally` block or at the end of `if __name__ == "__main__":`.
# Keeping them here can lead to issues if the driver object isn't available or if the utils file is
# imported in a context where a driver isn't meant to be immediately quit.
# I've removed them from this version of the utils file.
# You already have `driver.quit()` in your main script's `finally` block.