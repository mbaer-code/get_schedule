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
from PIL import Image

from schedule_extractor_utils import (
    check_for_running_chrome_processes,
    initialize_undetected_chrome_driver,
    perform_login,
    perform_minimization_sequence,
    drag_element_to_scroll,
    capture_and_ocr_segment,
    perform_mouse_click_on_element, # <-- Replace swipe with click
    parse_ocr_csv, COLUMN_NAMES
)

from schedule_extractor_config import (
    WEB_APP_URL, SCREENSHOT_OUTPUT_DIR, CHROME_USER_DATA_DIR, CHROMEDRIVER_PATH,
    SCHEDULE_CLICK_X_OFFSET, SCHEDULE_CLICK_Y_OFFSET, FLUTTER_VIEW_LOCATOR,
    MAX_DRAG_ATTEMPTS, DRAG_AMOUNT_Y_PIXELS, DRAG_START_X_OFFSET,
    DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT,
    END_OF_SCROLL_INDICATOR_LOCATOR,
    SCROLL_FLUTTER_VIEW_AND_CAPTURE
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

SCRIPT_VERSION = "0.0.80"

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

def launch_browser():
    """Launch Chrome with required options."""
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
    driver = initialize_undetected_chrome_driver()
    return driver

def wait_for_login(driver):
    """Wait for user to log in and solve any CAPTCHA."""
    print("\n--- ATTENTION REQUIRED ---")
    print("Please log in and solve any CAPTCHA in the Chrome window.")
    input("Press ENTER here after you are logged in and see the dashboard...\n")
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
        )
        print("Login and CAPTCHA complete. Proceeding with automation.")
    except Exception as e:
        print("Timeout waiting for dashboard after login. Please check the browser window.")
        driver.quit()
        exit(1)

def interactive_find_click_coordinates(driver, flutter_view_element, num_clicks=5):
    """
    Guide the user through a process to find and record click coordinates.
    After each click, a screenshot is saved so the user can use Paint or another tool
    to determine the next coordinates.
    """
    print("\n--- INTERACTIVE CLICK COORDINATE DISCOVERY ---")
    click_coords = []
    for i in range(num_clicks):
        print(f"\nStep {i+1} of {num_clicks}:")
        x = input(f"Enter X offset for click #{i+1} (pixels, relative to schedule area): ")
        y = input(f"Enter Y offset for click #{i+1} (pixels, relative to schedule area): ")
        try:
            x = int(x)
            y = int(y)
        except ValueError:
            print("Invalid input. Please enter integer values.")
            continue

        perform_mouse_click_on_element(driver, flutter_view_element, x, y)
        print(f"Clicked at ({x}, {y}). Waiting for UI to update...")
        time.sleep(2)  # Wait for UI to update

        # Take a screenshot after the click
        snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"step_{i+1}_snapshot.png")
        flutter_view_element.screenshot(snapshot_path)
        print(f"Snapshot saved: {snapshot_path}")
        print("Use Paint or another tool to inspect this image and determine the next click coordinates.")

        click_coords.append((x, y))

    print("\nInteractive click coordinate discovery complete.")
    print("Collected click coordinates (in order):")
    for idx, (x, y) in enumerate(click_coords, 1):
        print(f"  Click #{idx}: ({x}, {y})")
    print("You can now use these coordinates in your automation sequence.")

    return click_coords

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

def js_swipe(driver, element, start_x, start_y, end_x, end_y):
    driver.execute_script("""
        const rect = arguments[0].getBoundingClientRect();
        const startX = rect.left + arguments[1];
        const startY = rect.top + arguments[2];
        const endX = rect.left + arguments[3];
        const endY = rect.top + arguments[4];
        const dataTransfer = new DataTransfer();
        arguments[0].dispatchEvent(new PointerEvent('pointerdown', {clientX: startX, clientY: startY, bubbles: true}));
        arguments[0].dispatchEvent(new PointerEvent('pointermove', {clientX: endX, clientY: endY, bubbles: true}));
        arguments[0].dispatchEvent(new PointerEvent('pointerup', {clientX: endX, clientY: endY, bubbles: true}));
    """, element, start_x, start_y, end_x, end_y)

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

def random_canvas_clicks(driver, canvas_element, num_clicks=10):
    """
    Perform a series of pseudo-random clicks on the canvas to test for interaction.
    """
    rect = canvas_element.rect
    width = int(rect['width'])
    height = int(rect['height'])
    print(f"Canvas element size: width={width}, height={height}")

    for i in range(num_clicks):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        print(f"Random click #{i+1} at ({x}, {y})")
        click_canvas_at(driver, canvas_element, x, y)
        time.sleep(1)  # Short pause to observe any effect

def swipe_canvas(driver, canvas_element, start_x, start_y, end_x, end_y, duration_ms=300, steps=10):
    """
    Simulate a swipe (drag) gesture on a canvas from (start_x, start_y) to (end_x, end_y).
    Sends multiple pointermove events to mimic a real swipe.
    """
    driver.execute_script("""
        const canvas = arguments[0];
        const rect = canvas.getBoundingClientRect();
        const startX = rect.left + arguments[1];
        const startY = rect.top + arguments[2];
        const endX = rect.left + arguments[3];
        const endY = rect.top + arguments[4];
        const duration = arguments[5];
        const steps = arguments[6];

        function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

        async function swipe() {
            const downEvent = new PointerEvent('pointerdown', {
                clientX: startX,
                clientY: startY,
                bubbles: true,
                pointerType: 'touch'
            });
            canvas.dispatchEvent(downEvent);

            for (let i = 1; i <= steps; i++) {
                const progress = i / steps;
                const moveX = startX + (endX - startX) * progress;
                const moveY = startY + (endY - startY) * progress;
                const moveEvent = new PointerEvent('pointermove', {
                    clientX: moveX,
                    clientY: moveY,
                    bubbles: true,
                    pointerType: 'touch'
                });
                canvas.dispatchEvent(moveEvent);
                await sleep(duration / steps);
            }

            const upEvent = new PointerEvent('pointerup', {
                clientX: endX,
                clientY: endY,
                bubbles: true,
                pointerType: 'touch'
            });
            canvas.dispatchEvent(upEvent);
        }
        swipe();
    """, canvas_element, start_x, start_y, end_x, end_y, duration_ms, steps)
    print(f"Swipe gesture from ({start_x}, {start_y}) to ({end_x}, {end_y}) dispatched on canvas.")

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

def move_mouse_to_canvas(driver, canvas_element, x, y):
    """
    Move the mouse pointer to (x, y) relative to the top-left of the canvas element.
    This does not click, just moves the pointer.
    """
    driver.execute_script("""
        const canvas = arguments[0];
        const rect = canvas.getBoundingClientRect();
        const x = arguments[1];
        const y = arguments[2];
        const moveEvent = new PointerEvent('pointermove', {
            clientX: rect.left + x,
            clientY: rect.top + y,
            bubbles: true,
            pointerType: 'mouse'
        });
        canvas.dispatchEvent(moveEvent);
    """, canvas_element, x, y)
    print(f"Mouse pointer moved to ({x}, {y}) on canvas.")

def save_canvas_snapshot(canvas_element, step_name):
    """
    Save a screenshot of the canvas element for OCR processing.
    """
    snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"{step_name}_canvas.png")
    canvas_element.screenshot(snapshot_path)
    print(f"Canvas snapshot saved: {snapshot_path}")
    return snapshot_path

def navigate_to_schedule(driver):
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

    # OCR all snapshots and write results to file
    output_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "all_ocr_results.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(1, num_scrolls + 1):
            img_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"dom_scroll_{i}_canvas.png")
            if not os.path.exists(img_path):
                print(f"File not found: {img_path}")
                continue
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            print(f"--- OCR Result {i} ---\n{text}\n{'-'*40}")
            f.write(f"--- OCR Result {i} ---\n{text}\n{'-'*40}\n")

    print(f"OCR results saved to {output_path}")

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

    print(f"OCR CSV results saved to {output_csv_path}")

    # After writing ocr_results.csv
    structured_csv_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "ocr_results_structured.csv")
    entries = parse_ocr_csv(output_csv_path)
    with open(structured_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMN_NAMES)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)
    print(f"Structured CSV written to {structured_csv_path}")

    return flutter_view_element


# -- EXECUTION START ---

print(f"--- Schedule Extractor Script (v{SCRIPT_VERSION}) ---")
cleanup_environment()
driver = launch_browser()
driver.get(WEB_APP_URL)

# Step 1: Perform login (manual, so skip or comment out)
# perform_login(driver)

# Step 2: Wait for login and handle CAPTCHA
wait_for_login(driver)

# Step 3: Navigate to schedule and discover click coordinates
navigate_to_schedule(driver)

print("\n--- SCRIPT COMPLETED ---")
print("Review the saved snapshots and update your code/config with the new coordinates.")
print("Rerun the script when ready to continue with automation.")
driver.quit()
