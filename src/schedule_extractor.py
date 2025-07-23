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
import sys # Added for command-line argument handling
import tkinter as tk # Added for GUI dialog
from tkinter import simpledialog # Added for GUI dialog
from PIL import Image

# utils imports
from schedule_extractor_utils import (
    is_chrome_running,          # NEW: For checking if Chrome is running
    kill_chrome_processes,      # NEW: For terminating Chrome processes
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
    OCR_FILEPATH, OCR_RESULTS_FILEPATH, OCR_CSV_FILEPATH,
    MAX_DRAG_ATTEMPTS, DRAG_AMOUNT_Y_PIXELS, DRAG_START_X_OFFSET,
    DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT,
    END_OF_SCROLL_INDICATOR_LOCATOR,
    SCROLL_FLUTTER_VIEW_AND_CAPTURE
)

# calendar_builder imports
# Assuming calendar_builder.main will be updated to accept calendar_id and structured_csv_path
from calendar_builder import main as create_calendar_events

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
    chrome_options.add_argument("--disable-prompt-on_repost")
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
    prev_url = WEB_APP_LOGIN_URL
    sleep_time = 30

    current_url = driver.current_url.split("?")[0]
    print(current_url)

    print("current URL:", current_url)

    while current_url == prev_url:
        # Wait for the URL to change
        print("waiting for change in current URL:", current_url)
        current_url = driver.current_url.split("?")[0]
        time.sleep(sleep_time)

    # Print the new URL
    current_url = driver.current_url.split("?")[0]
    prev_url = driver.current_url.split("?")[0]
    print("NEW current URL:", current_url)

    while current_url == prev_url:
        # Wait for the URL to change
        current_url = driver.current_url.split("?")[0]
        print("waiting for next change in current URL:", current_url)
        time.sleep(sleep_time)

    # Print the new URL
    current_url = driver.current_url.split("?")[0]
    prev_url = driver.current_url.split("?")[0]
    print("New current URL:", driver.current_url)

    # all of this is awful, but it works
    #while current_url == prev_url:
    while current_url != "https://wft.homedepot.com/": 

        # Wait for the URL to change
        current_url = driver.current_url.split("?")[0]
        print("waiting for next change in current URL:", current_url)
        time.sleep(sleep_time)

    # Print the new URL
    current_url = driver.current_url.split("?")[0]
    prev_url = driver.current_url.split("?")[0]
    print("New current URL:", driver.current_url)


    try:
        #WebDriverWait(driver, 10).until( # Original commented line, keeping it as is
        WebDriverWait(driver, 600).until(
            EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
        )
        print("Login and CAPTCHA complete. Proceeding with automation.")
    except Exception as e:
        print("Timeout waiting for dashboard after login. Please check the browser window.")
        driver.quit()
        exit(1)


def take_a_snapshot(driver, flutter_view_element, step_name="step"):
    """
    Take a snapshot of the current view, save it, and exit the script.
    The user can then open the image in Paint to determine the next click coordinates.
    """
    snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"{step_name}_snapshot.png")
    flutter_view_element.screenshot(snapshot_path)
    print(f"\nSnapshot saved: {snapshot_path}")
    #print("Open this image in Paint or another tool to determine the next click coordinates.") # Original commented line, keeping it as is
    #print("Exit the script now, update your code/config with the new coordinates, and rerun when ready.") # Original commented line, keeping it as is
    #driver.quit() # Original commented line, keeping it as is
    #exit(0) # Original commented line, keeping it as is


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
    #time.sleep(20) # Original commented line, keeping it as is
    #print("Waiting 5 seconds before clicking through navigation steps...") # Original commented line, keeping it as is
    take_a_snapshot(driver, flutter_view_element, step_name="dashboard")
    #time.sleep(10) # Original commented line, keeping it as is

    # Click the schedule tile
    click_canvas_at(driver, flutter_view_element, 300, 300)
    time.sleep(2)
    take_a_snapshot(driver, flutter_view_element, step_name="schedule_tile")

    # Minimize first graphic
    #click_canvas_at(driver, flutter_view_element, 1200, 645) # Original commented line, keeping it as is
    click_canvas_at(driver, flutter_view_element, 1200, 550)
    time.sleep(2)
    take_a_snapshot(driver, flutter_view_element, step_name="minimize_one")

    # Minimize second graphic
    click_canvas_at(driver, flutter_view_element, 1200, 300)
    time.sleep(2)
    take_a_snapshot(driver, flutter_view_element, step_name="minimize_two")
    time.sleep(2)

    # Scroll and snapshot pipeline
    print("Scrolling up to the top of the day of the month view...")
    scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=-120, steps=10, delay=0.2, x=1200, y=350)
    take_a_snapshot(driver, flutter_view_element, step_name="after_scroll_up")
    time.sleep(2)

    print("Beginning snapshot and scroll loop...")
    num_scrolls = 21   # Capture 21 day entries

    for i in range(num_scrolls):
        print(f"iter {i} for the scroll loop...")

        # 0. Scroll down past the weekly hours summary
        print(f"testing for mod == {i % 7}...")
        if i % 7 == 0:

            print(f"i is mod 7: 0...")
            snap_name = f"weekly_summary_{i}"
            save_canvas_snapshot(flutter_view_element, snap_name)

            absy = 195

            if i > 0:
                #wsdelta = 250 # Original commented line, keeping it as is
                #wsdelta = 190 # Original commented line, keeping it as is
                wsdelta = 150
            else:
                #wsdelta = 200 # Original commented line, keeping it as is
                #wsdelta = 100
                wsdelta = 70


            #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=95, steps=1, delay=1, x=1200, y=350) # Original commented line, keeping it as is
            #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=95, steps=1, delay=1, x=1200, y=190) # Original commented line, keeping it as is
            scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=wsdelta, steps=1, delay=1, x=1200, y=absy)
            snap_name = f"after_summary_{i}"
            save_canvas_snapshot(flutter_view_element, snap_name)
            print(f"Snapshot taken for detail view {i}")
            time.sleep(1)

        # 1. Click the button at (x=1200, y=270) before scrolling down
        #print(f"Clicking button at (1200, 270) before scroll {i+1}...") # Original commented line, keeping it as is
        print(f"Clicking button at (1200, {absy}) before scroll {i+1}...")
        click_canvas_at(driver, flutter_view_element, 1200, absy)
        time.sleep(1)

        # 2. Take a snapshot of the new view after the click
        snap_name = f"detail_view_{i+1}"
        save_canvas_snapshot(flutter_view_element, snap_name)
        print(f"Snapshot taken for detail view {i+1}")

        # 3. Return to the DOM canvas using browser back
        print("Returning to DOM canvas...")
        # driver.back()
        # driver.execute_script("window.history.go(-1)")
        print("calling click_canvas_at...")
        click_canvas_at(driver, flutter_view_element, 492, 36 )

        print("sleeping for 3 ...")
        time.sleep(3)   # Give time for the view to update
                         # if it ever expires again set it to 15

        # 4. Re-locate the canvas element after navigation
        flutter_view_element = WebDriverWait(driver, 600).until(
            EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
        )

        # 5. Scroll down for the next day tile, except after last
        #if i < num_scrolls - 1: # Original commented line, keeping it as is
        if i < num_scrolls:

            # Calculate the day of the week for the next tile # Original commented line, keeping it as is

            #print(f"\nnext_day_of_week is: ", next_day_of_week ) # Original commented line, keeping it as is
            #print(f"Scrolling down for next day tile (scroll {i+2})...\n") # Original commented line, keeping it as is
            #scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=120, steps=1, delay=0.5, x=1200, y=350) # Original commented line, keeping it as is

            delta = 114

            #yabs  = 350 # Original commented line, keeping it as is
            #yabs  = 210 # Original commented line, keeping it as is
            yabs  = 290

            print("Advancing wheel by {delta} px to next tile...")
            #print(f"Scrolling down for next day tile (scroll {i+2})...\n") # Original commented line, keeping it as is
            scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=delta, steps=1, delay=1, x=1200, y=yabs)

            # If the next tile is Monday, skip the extra text tile # Original commented line, keeping it as is
            #if next_day_of_week == 0: # Original commented line, keeping it as is
            #   print("Advancing wheel by extra 160 px to skip over text before Monday...") # Original commented line, keeping it as is
            #   scroll_canvas_with_wheel(driver, flutter_view_element, delta_y=130, steps=1, delay=1, x=1200, y=350) # Original commented line, keeping it as is
            time.sleep(1)

    # OCR all snapshots and write results to file

    output_path = OCR_RESULTS_FILEPATH
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

    #print(f"OCR results saved to {output_path}") # Original commented line, keeping it as is

    # Save OCR results to CSV
    output_csv_path = OCR_CSV_FILEPATH
    output_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results.csv")
    with open(output_csv_path, "w", encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "ocr_text"])   # Header row

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

    #print(f"OCR CSV results saved to {output_csv_path}") # Original commented line, keeping it as is

    # After writing ocr_results.csv
    # structured_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results_structured.csv")
    structured_csv_path = OCR_FILEPATH

    entries = parse_ocr_csv(output_csv_path)
    with open(structured_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMN_NAMES)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)
    #print(f"Structured CSV written to {structured_csv_path}") # Original commented line, keeping it as is
    return output_path, output_csv_path, structured_csv_path   # Return all paths

def get_calendar_id_gui():
    #Prompts the user for the Google Calendar ID using a simple GUI dialog.
    print("DEBUG: Entering get_calendar_id_gui()")
    try:
        root = tk.Tk()
        root.withdraw() # Hide the main tkinter window
        print("DEBUG: Tkinter root created and hidden.")
        calendar_id = simpledialog.askstring("Input", "Please enter the Google Calendar ID (e.g., 'primary'):",
                                             parent=root)
        print(f"DEBUG: simpledialog.askstring returned: '{calendar_id}'")
        root.destroy() # Destroy the hidden root window after use
        print("DEBUG: Tkinter root destroyed.")
        return calendar_id
    except Exception as e:
        print(f"ERROR: Exception in get_calendar_id_gui: {e}")
        # If Tkinter fails for some reason (e.g., missing DLLs in bundle),
        # we might want to provide a fallback or a clear error message.
        # For now, returning None will trigger the sys.exit(1) below.
        return None

# Updated to accept calendar_id and structured_csv_path
print("calling create_Calendar_events!")
#def create_calendar_events_from_results(calendar_id, structured_csv_path):
def create_calendar_events_from_results(calendar_id):
#def create_calendar_events_from_results():
    """Optional final step to create Google Calendar events"""
    try:
        # Import and use build_calendar functionality
        print(f"\n=== STEP 3: CREATING CALENDAR EVENTS ===")
        #print(f"Using calendar: {calendar_id}")
        print(f"Using CSV: {structured_csv_path}")

        # Call the calendar creation logic, passing the obtained calendar_id and CSV path
        create_calendar_events(calendar_id)

        print("Calendar events created successfully!")

    except Exception as e:
        print(f"Error creating calendar events: {e}")


""" ----------------------------------------------------------------------------------- """

if __name__ == "__main__":

    # --- Calendar ID Input Handling ---
    #output_path = OCR_FILEPATH
    calendar_id = None
    print("DEBUG: Starting calendar ID input handling in __main__.")
    # 1. Check for command-line argument first
    if len(sys.argv) > 1:
        calendar_id = sys.argv[1]
        print(f"DEBUG: Calendar ID from command line: '{calendar_id}'")
    else:
        # 2. If no command-line argument, prompt with GUI
        print("DEBUG: No calendar ID provided via command line. Attempting GUI prompt...")
        calendar_id = get_calendar_id_gui()
        if calendar_id is None: # User clicked Cancel or GUI failed
            print("DEBUG: Calendar ID GUI input cancelled or failed (returned None). Exiting.")
            sys.exit(1)
        elif calendar_id == "": # User clicked OK with empty input
            print("DEBUG: Calendar ID GUI input empty (returned ''). Exiting.")
            sys.exit(1)
        else:
            print(f"DEBUG: Calendar ID from GUI: '{calendar_id}'")
    print(f"DEBUG: Finished calendar ID input handling in __main__. Final calendar_id: '{calendar_id}'")
    # --- End Calendar ID Input Handling ---

    output_path         = OCR_RESULTS_FILEPATH
    structured_csv_path = OCR_FILEPATH 

    # turn off scraping here for debugging

    # Prepare the environment for the script run
    # --- Ensure no other Chrome instances are running ---
    # First, check if Chrome is running and kill it if necessary
    if is_chrome_running():
        print("Chrome is currently running. Attempting to terminate existing instances...")
        kill_chrome_processes()
    else:
        print("Chrome is not currently running.")
    # --- End of Chrome process management ---

    # cleanup from prevous run, start browser and login to website
    cleanup_environment()
    driver = launch_browser(headless=False)
    driver.get(WEB_APP_URL)
    # structured_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results_structured.csv") # Original line
    structured_csv_path = OCR_FILEPATH # Using OCR_FILEPATH from config for consistency

    # handle login and hop to home depot dashboard
    print("calling handle_thd_login()")
    handle_thd_login (driver)

    # traverse the schedule and take snapshots of schedule entires
    print("calling snapshot_schedule_entries()")
    output_path, output_csv_path, structured_csv_path = snapshot_schedule_entries(driver)

    # turn off scraping end of block


    # here is the call to create calendar entires
    print(f"DEBUG: About to call create_calendar_events_from_results in calendar_builder.pywith no arguments'")
    #create_calendar_events_from_results(calendar_id, structured_csv_path)
    create_calendar_events_from_results(calendar_id)
    print("DEBUG: create_calendar_events_from_results call completed.")

    # script Wrap-up
    print("\n--- SCRIPT COMPLETED ---")
    print(f"OCR results saved to: {output_path}")
    #print(f"OCR CSV results saved to: {output_csv_path}") # Original commented line, keeping it as is
    print(f"Structured CSV written to: {structured_csv_path}")


    # Always ensure the browser is closed properly at the end of the script
    # This also ensures the undetected_chromedriver process is terminated.
    if 'driver' in locals() and driver:
        print("Closing Chrome browser.")
        driver.quit()
