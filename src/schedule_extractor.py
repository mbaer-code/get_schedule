# =============================================================================
# schedule_extractor.py
# -----------------------------------------------------------------------------
# Main script to automate extraction of schedule data from a web app using
# Selenium and OCR. Handles browser automation, login, navigation, screenshot
# capture, and text extraction.
#
# Author: Martin Baer
# Version: 0.0.80
# Created: 2024-06-26
# License: MIT
# -----------------------------------------------------------------------------
# Usage:
#   python schedule_extractor.py
#
# Notes:
#   - Requires ChromeDriver and compatible Chrome version.
#   - Configuration is managed in schedule_extractor_config.py.
#   - Utility functions are in schedule_extractor_utils.py.
# =============================================================================

import os
import time
import shutil
import random
import pytesseract
import datetime
import csv
#import argparse
from PIL import Image

# utils imports
from schedule_extractor_utils import (
    check_for_running_chrome_processes,
    initialize_undetected_chrome_driver,
    perform_login,
    perform_minimization_sequence,
    drag_element_to_scroll,
    capture_and_ocr_segment,
    perform_mouse_click_on_element,
    parse_ocr_csv, COLUMN_NAMES
)

# config imports
from schedule_extractor_config import (
    WEB_APP_URL, WEB_APP_LOGIN_URL, SCREENSHOT_OUTPUT_DIR, CHROME_USER_DATA_DIR, CHROMEDRIVER_PATH,
    SCHEDULE_CLICK_X_OFFSET, SCHEDULE_CLICK_Y_OFFSET, FLUTTER_VIEW_LOCATOR,
    MAX_DRAG_ATTEMPTS, DRAG_AMOUNT_Y_PIXELS, DRAG_START_X_OFFSET,
    DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT,
    END_OF_SCROLL_INDICATOR_LOCATOR,
    SCROLL_FLUTTER_VIEW_AND_CAPTURE
)

# selenium imports
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def cleanup_environment():

    """Remove old Chrome user data and screenshots for a fresh run."""
    print(f"Cleaning up old Chrome user data directory: {CHROME_USER_DATA_DIR}")

    if os.path.exists(CHROME_USER_DATA_DIR):
        try:
            shutil.rmtree(CHROME_USER_DATA_DIR)
            print("Old user data directory removed.")
        except Exception as e:
            print(f"WARNING: Could not remove user data directory: {e}")

    print(f"Cleaning up old screenshots in: {SCREENSHOT_OUTPUT_DIR}")
    if os.path.exists(SCREENSHOT_OUTPUT_DIR):
        try:
            shutil.rmtree(SCREENSHOT_OUTPUT_DIR)
            print("Old screenshot directory removed.")
        except Exception as e:
            print(f"WARNING: Could not remove screenshot directory: {e}")
    os.makedirs(SCREENSHOT_OUTPUT_DIR, exist_ok=True)
    print(f"Ensured screenshot output directory exists: {SCREENSHOT_OUTPUT_DIR}")


def launch_browser(headless=False):
    """Launch Chrome with required options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
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
    driver = initialize_undetected_chrome_driver(options=chrome_options)
    return driver


def handle_thd_login (driver):


    # Define the current URL
    current_url = driver.current_url
    prev_url  = WEB_APP_LOGIN_URL
    sleep_time  = 10

    current_url = driver.current_url.split("?") [0]
    print(current_url)

    print("current URL:", current_url)

    while current_url == prev_url:

        # Wait for the URL to change
        print("waiting for change in  current URL:", current_url)
        current_url = driver.current_url.split("?") [0]
        time.sleep(sleep_time)

    # Print the new URL
    current_url = driver.current_url.split("?") [0]
    prev_url = driver.current_url.split("?") [0]
    print("NEW current URL:", current_url)

    while current_url == prev_url:
        # Wait for the URL to change
        current_url = driver.current_url.split("?") [0]
        print("waiting for next change in  current URL:", current_url)
        time.sleep(sleep_time)
    
    # Print the new URL
    current_url = driver.current_url.split("?") [0]
    prev_url = driver.current_url.split("?") [0]
    print("New current URL:", driver.current_url)

    while current_url == prev_url:
        # Wait for the URL to change
        current_url = driver.current_url.split("?") [0]
        print("waiting for next change in  current URL:", current_url)
        time.sleep(sleep_time)

    # Print the new URL
    current_url = driver.current_url.split("?") [0]
    prev_url = driver.current_url.split("?") [0]
    print("New current URL:", driver.current_url)


    try:
        #WebDriverWait(driver, 10).until(
        WebDriverWait(driver, 600).until(
            EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
        )
        print("Login and CAPTCHA complete. Proceeding with automation.")
    except Exception as e:
        print("Timeout waiting for dashboard after login. Please check the browser window.")
        driver.quit()
        exit(1)


def interactive_snapshot_and_exit(driver, flutter_view_element, step_name="step"):
    """
    Take a snapshot of the current view, save it, and exit the script.
    The user can then open the image in Paint to determine the next click coordinates.
    """
    snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"{step_name}_snapshot.png")
    flutter_view_element.screenshot(snapshot_path)
    print(f"\nSnapshot saved: {snapshot_path}")
    #print("Open this image in Paint or another tool to determine the next click coordinates.")
    #print("Exit the script now, update your code/config with the new coordinates, and rerun when ready.")
    #driver.quit()
    #exit(0)


def perform_mouse_click_on_element(driver, element, x_offset, y_offset):
    """Clicks at a specific offset within a given element."""
    from selenium.webdriver.common.action_chains import ActionChains
    print(f"Attempting to click at offset ({x_offset}, {y_offset}) within element: {element}")
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(element, x_offset, y_offset).click().perform()
    print(f"Mouse click performed at offset ({x_offset}, {y_offset}) within element.")


def click_canvas_at(driver, canvas_element, x, y):
    """
    Dispatch a pointerdown and pointerup event at (x, y) relative to the top-left of the canvas element.
    """
    driver.execute_script("""
        const canvas = arguments[0];
        const rect = canvas.getBoundingClientRect();
        const x = arguments[1];
        const y = arguments[2];
        const downEvent = new PointerEvent('pointerdown', {
            clientX: rect.left + x,
            clientY: rect.top + y,
            bubbles: true,
            pointerType: 'mouse'
        });
        const upEvent = new PointerEvent('pointerup', {
            clientX: rect.left + x,
            clientY: rect.top + y,
            bubbles: true,
            pointerType: 'mouse'
        });
        canvas.dispatchEvent(downEvent);
        canvas.dispatchEvent(upEvent);
    """, canvas_element, x, y)
    print(f"Canvas pointerdown/pointerup dispatched at ({x}, {y}) relative to canvas.")


def scroll_canvas_with_wheel(driver, canvas_element, delta_y, steps=1, delay=0.2, x=1200, y=300):
    """
    Simulate mouse wheel scrolling on the canvas at a specific (x, y) coordinate.
    delta_y: positive for scroll down, negative for scroll up.
    steps: number of wheel events to send.
    delay: seconds to wait between events.
    x, y: coordinates relative to the top-left of the canvas.
    """
    for i in range(steps):
        print(f"top of wheel event loop #{i+1} with deltaY={delta_y} at ({x}, {y})")
        driver.execute_script("""
            const canvas = arguments[0];
            const rect = canvas.getBoundingClientRect();
            const wheelEvent = new WheelEvent('wheel', {
                clientX: rect.left + arguments[2],
                clientY: rect.top + arguments[3],
                deltaY: arguments[1],
                bubbles: true
            });
            canvas.dispatchEvent(wheelEvent);
        """, canvas_element, delta_y, x, y)
        print(f"Dispatched wheel event #{i+1} with deltaY={delta_y} at ({x}, {y})")
        time.sleep(delay)


def save_canvas_snapshot(canvas_element, step_name):
    """
    Save a screenshot of the canvas element for OCR processing.
    """
    snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"{step_name}_canvas.png")
    canvas_element.screenshot(snapshot_path)
    print(f"Canvas snapshot saved: {snapshot_path}")
    return snapshot_path


def snapshot_schedule_entries (driver):
    
    # scroll through the schedule canvas and snapshot them

    flutter_view_element = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
    )
    #time.sleep(20)
    #print("Waiting 5 seconds before clicking through navigation steps...")
    interactive_snapshot_and_exit(driver, flutter_view_element, step_name="dashboard")
    #time.sleep(10)

    # Click the schedule tile
    click_canvas_at(driver, flutter_view_element, 300, 300)
    time.sleep(2)
    interactive_snapshot_and_exit(driver, flutter_view_element, step_name="schedule_tile")

    # Minimize first graphic
    #click_canvas_at(driver, flutter_view_element, 1200, 645)
    click_canvas_at(driver, flutter_view_element, 1200, 550)
    time.sleep(2)
    interactive_snapshot_and_exit(driver, flutter_view_element, step_name="minimize_one")

    # Minimize second graphic
    click_canvas_at(driver, flutter_view_element, 1200, 300)
    time.sleep(2)
    interactive_snapshot_and_exit(driver, flutter_view_element, step_name="minimize_two")
    time.sleep(2)

    # Scroll and snapshot pipeline
    print("Scrolling up to the top of the day of the month view...")
    scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=-120, steps=10, delay=0.2, x=1200, y=350)
    interactive_snapshot_and_exit(driver, flutter_view_element, step_name="after_scroll_up")
    time.sleep(2)

    print("Beginning snapshot and scroll loop...")
    num_scrolls = 21  # Capture 21 day entries

    for i in range(num_scrolls):
        print(f"iter {i} for the scroll loop...")

        # 0. Scroll down past the weekly hours summary

        # jump over the devide
        print(f"testing for mod == {i % 7}...")
        if i % 7 == 0:

            print(f"i is mod 7: 0...")
            snap_name = f"weekly_summary_{i}"
            save_canvas_snapshot(flutter_view_element, snap_name)
            

            absy = 195

            if i > 0:
                #wsdelta = 250
                #wsdelta = 190
                wsdelta = 150
            else:
                #wsdelta = 200
                wsdelta = 100


            #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=95, steps=1, delay=1, x=1200, y=350)
            #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=95, steps=1, delay=1, x=1200, y=190)
            scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=wsdelta, steps=1, delay=1, x=1200, y=absy)
            snap_name = f"after_summary_{i}"
            save_canvas_snapshot(flutter_view_element, snap_name)
            print(f"Snapshot taken for detail view {i}")
            time.sleep(1)

        # 1. Click the button at (x=1200, y=270) before scrolling down
        #print(f"Clicking button at (1200, 270) before scroll {i+1}...")
        print(f"Clicking button at (1200, {absy}) before scroll {i+1}...")
        click_canvas_at(driver, flutter_view_element, 1200, absy)
        time.sleep(1)

        # 2. Take a snapshot of the new view after the click
        snap_name = f"detail_view_{i+1}"
        save_canvas_snapshot(flutter_view_element, snap_name)
        print(f"Snapshot taken for detail view {i+1}")

        # 3. Return to the DOM canvas using browser back
        print("Returning to DOM canvas...")
        driver.back()
        time.sleep(2)  # Give time for the view to update

        # 4. Re-locate the canvas element after navigation
        flutter_view_element = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
        )

        # 5. Scroll down for the next day tile, except after last
        #if i < num_scrolls - 1:
        if i < num_scrolls:

            # Calculate the day of the week for the next tile

           #print(f"\nnext_day_of_week is: ", next_day_of_week )
           #print(f"Scrolling down for next day tile (scroll {i+2})...\n")
           #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=120, steps=1, delay=0.5, x=1200, y=350)

           delta = 114

           #yabs  = 350
           #yabs  = 210
           yabs  = 290

           print("Advancing wheel by {delta} px to next tile...")
           #print(f"Scrolling down for next day tile (scroll {i+2})...\n")
           scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=delta, steps=1, delay=1, x=1200, y=yabs)

           # If the next tile is Monday, skip the extra text tile
           #if next_day_of_week == 0:
           #    print("Advancing wheel by extra 160 px to skip over text before Monday...")
           #    scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=130, steps=1, delay=1, x=1200, y=350)
           time.sleep(1)


#def ocr_schedule_snapshots():
    
    # OCR all snapshots and write results to file

    output_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "all_ocr_results.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(1, num_scrolls + 1):
            img_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"detail_view_{i}_canvas.png")
            if not os.path.exists(img_path):
                print(f"File not found: {img_path}")
                continue
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            print(f"--- OCR Result {i} ---\n{text}\n{'-'*40}")
            f.write(f"--- OCR Result {i} ---\n{text}\n{'-'*40}\n")

    #print(f"OCR results saved to {output_path}")

    # Save OCR results to CSV
    output_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results.csv")
    with open(output_csv_path, "w", encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "ocr_text"])  # Header row

        for i in range(1, num_scrolls + 1):
            img_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"detail_view_{i}_canvas.png")
            if not os.path.exists(img_path):
                print(f"File not found: {img_path}")
                continue
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            if "Not Scheduled" in text:
                print(f"Skipping {img_path} (Not Scheduled)")
                continue
            # Write filename and OCR text as a row
            writer.writerow([os.path.basename(img_path), text.strip().replace('\n', ' ')])

    #print(f"OCR CSV results saved to {output_csv_path}")

    # After writing ocr_results.csv
    structured_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results_structured.csv")
    entries = parse_ocr_csv(output_csv_path)
    with open(structured_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMN_NAMES)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)
    #print(f"Structured CSV written to {structured_csv_path}")


    return output_path, output_csv_path, structured_csv_path  # Return all paths


""" ----------------------------------------------------------------------------------- """

if __name__ == "__main__":

   
    # cleanup from prevous run, start browser and login to website
    cleanup_environment()
    driver = launch_browser(headless=False)
    driver.get(WEB_APP_URL)

    # handle login and hop to home depot dashboard
    print("calling hand_thd_login()")
    handle_thd_login (driver)

    # traverse the schedule and take snapshots of schedule entires
    print("calling snapshot_schedule_entries()")
    output_path, output_csv_path, structured_csv_path = snapshot_schedule_entries(driver)

    # script Wrap-up 
    print("\n--- SCRIPT COMPLETED ---")
    print(f"OCR results saved to: {output_path}")
    print(f"OCR CSV results saved to: {output_csv_path}")
    print(f"Structured CSV written to: {structured_csv_path}")

