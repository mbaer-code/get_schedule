# schedule_extractor.py
# This is the main script to run the schedule extraction process.
# Script Version: 0.0.80 # Corrected initial swipe up parameters

import os
import time
import shutil # For deleting directories

# Import functions from schedule_extractor_utils
from schedule_extractor_utils import (
    check_for_running_chrome_processes,
    initialize_undetected_chrome_driver,
    perform_login,
    perform_minimization_sequence,
    drag_element_to_scroll,
    capture_and_ocr_segment,
    perform_swipe_on_element # Explicitly import perform_swipe_on_element as it's used directly here
)

# Import configuration variables directly
from schedule_extractor_config import (
    WEB_APP_URL, SCREENSHOT_OUTPUT_DIR, SCREENSHOT_BASE_NAME, CHROME_USER_DATA_DIR,
    SCHEDULE_CLICK_X_OFFSET, SCHEDULE_CLICK_Y_OFFSET, FLUTTER_VIEW_LOCATOR,
    MAX_DRAG_ATTEMPTS, DRAG_AMOUNT_Y_PIXELS, DRAG_START_X_OFFSET,
    DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT,
    END_OF_SCROLL_INDICATOR_LOCATOR
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


# --- Configuration (Local to Main Script for direct access) ---
# This SCRIPT_VERSION is defined here to ensure it's always available for printing.
# It should be kept consistent with the version in schedule_extractor_config.py for true version tracking.
SCRIPT_VERSION = "0.0.80" # Updated version for corrected initial swipe up


# --- Main Extraction Function ---
def extract_text_from_flutter_view():
    """
    Automates Browse to a web app by launching Chrome, logging in,
    taking screenshots of the Flutter view (with simulated scrolling),
    and extracting text using OCR.
    """
    print("Automating browser launch and login sequence...")
    print(f"Script Version: {SCRIPT_VERSION}") # Prints the script version

    # --- Check for running Chrome processes before proceeding ---
    if check_for_running_chrome_processes():
        return # Exit the script if Chrome is already running

    # --- CLEANUP OLD DATA (Screenshots & Profile) ---
    print(f"Cleaning up old Chrome user data directory for fresh start: {CHROME_USER_DATA_DIR}")
    if os.path.exists(CHROME_USER_DATA_DIR):
        try:
            shutil.rmtree(CHROME_USER_DATA_DIR)
            print("Old user data directory removed successfully.")
        except Exception as e:
            print(f"WARNING: Error removing old user data directory: {e}. This might be OK if Chrome is already closed. Proceeding.")

    # --- ENHANCED SCREENSHOT CLEANUP ---
    print(f"Cleaning up all old screenshots in the output directory: {SCREENSHOT_OUTPUT_DIR}")
    if os.path.exists(SCREENSHOT_OUTPUT_DIR):
        try:
            shutil.rmtree(SCREENSHOT_OUTPUT_DIR)
            print("Old screenshot directory removed successfully.")
        except Exception as e:
            print(f"WARNING: Error removing old screenshot directory: {e}. Proceeding but folder might not be clean: {e}")
    
    os.makedirs(SCREENSHOT_OUTPUT_DIR, exist_ok=True)
    print(f"Ensured screenshot output directory exists: {SCREENSHOT_OUTPUT_DIR}")
    # --- END CLEANUP ---

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
    driver = None

    try: # OUTER TRY BLOCK START
        driver = initialize_undetected_chrome_driver()
        
        print(f"Navigating to {WEB_APP_URL}...")
        driver.get(WEB_APP_URL)

        print("\n--- ATTENTION REQUIRED ---")
        print(f"Waiting for the initial 'Are you human?' challenge to resolve and redirect to the login page (up to 90 seconds)...")
        print("If the 'Are you human?' test does not resolve automatically within the first 10-15 seconds,")
        print("PLEASE MANUALLY SOLVE IT IN THE CHROME WINDOW and observe if the login page then appears.")

        try:
            WebDriverWait(driver, 90).until(
                EC.url_contains("identity.homedepot.com/as/authorization.oauth2")
            )
            print(f"Successfully redirected to login page: {driver.current_url}")
            time.sleep(5) # Small pause after successful redirect
        except Exception as e:
            print(f"Timed out waiting for redirect to login page. Current URL: {driver.current_url}")
            print(f"Error details: {e}")
            print("Please ensure you manually solved any 'Are you human?' challenges if they appeared.")
            print("Proceeding with fixed delay to allow for manual intervention if needed.")
            time.sleep(15) # Extended pause for manual intervention
            print(f"Current URL after manual intervention (if any): {driver.current_url}")

        username = input("Please enter your username: ")
        password = input("Please enter your password: ")

        if not perform_login(driver, username, password):
            print("Login failed. Exiting script.")
            driver.quit()
            return

        # --- Dashboard to Schedule Navigation and Minimization Sequence ---
        flutter_view_element = None # Initialize flutter_view_element here
        try: # INNER TRY BLOCK START (for app navigation and minimize sequence)
            # Find the Flutter view element
            flutter_view_element = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located(FLUTTER_VIEW_LOCATOR)
            )
            print("Flutter view element confirmed and visible for interaction.")
            print("Pausing for 15 seconds to allow Flutter dashboard content to render...")
            time.sleep(15) # Delay for dashboard content to render
            
            # Perform a small swipe/drag on the Flutter view element at the specified offset
            print(f"Attempting small swipe at relative coordinates: ({SCHEDULE_CLICK_X_OFFSET}, {SCHEDULE_CLICK_Y_OFFSET}) to navigate to schedule.")
            perform_swipe_on_element(
                driver,
                flutter_view_element,
                SCHEDULE_CLICK_X_OFFSET,
                SCHEDULE_CLICK_Y_OFFSET,
                5, 0 # Simulate a tap
            )
            print("Swipe attempt executed. Assuming successful navigation to schedule view.")
            time.sleep(5) # Pause for schedule content to start loading

            # Take initial snapshot of the SCHEDULE VIEW
            schedule_initial_snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "schedule_initial_snapshot.png")
            flutter_view_element = WebDriverWait(driver, 30).until(EC.presence_of_element_located(FLUTTER_VIEW_LOCATOR))
            flutter_view_element.screenshot(schedule_initial_snapshot_path)
            print(f"SUCCESS: Initial snapshot of schedule view saved to: {schedule_initial_snapshot_path}")
            print("--- Waiting for SCHEDULE VIEW CONTENT to load (fixed 10-second delay) ---")
            time.sleep(10) # Fixed delay for full schedule content rendering

            if not perform_minimization_sequence(driver, flutter_view_element):
                print("Minimization sequence failed. Proceeding with potential issues.")
                flutter_view_element = None # Indicate that interactions in this phase failed.
                
            # --- INITIAL SWIPE UP: Position schedule to the top ---
            print("\n--- PERFORMING INITIAL SWIPE UP to expose top of schedule ---")
            try:
                if flutter_view_element: # Ensure element is still valid
                    # Swipe upwards visually (drag mouse down) near the middle of the view, with a larger drag amount
                    drag_element_to_scroll(
                        driver,
                        flutter_view_element,
                        DRAG_AMOUNT_Y_PIXELS, # Use positive Y to scroll content UPWARDS (by dragging mouse DOWN)
                        flutter_view_element.size['width'] // 2, # Start X at center of element
                        0.1 # Start Y near top of element (relative to its height)
                    )
                    print("    Initial swipe up executed.")
                    time.sleep(3) # Give time for content to settle

                    post_initial_swipe_snapshot_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "post_initial_swipe_up.png")
                    flutter_view_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(FLUTTER_VIEW_LOCATOR))
                    flutter_view_element.screenshot(post_initial_swipe_snapshot_path)
                    print(f"    Post-initial swipe up snapshot saved to: {post_initial_swipe_snapshot_path}")
                    print("    *** MANUALLY CHECK THIS SNAPSHOT TO CONFIRM SCHEDULE IS AT THE TOP! ***")

            except Exception as e:
                print(f"    Error during initial swipe up: {e}")
                print("    Initial swipe up failed.")


        except Exception as e: # INNER EXCEPT BLOCK END (for app navigation and minimize sequence)
            print(f"Error during app navigation or minimization sequence: {e}")
            print("Please manually verify the current page state and logs.")
            flutter_view_element = None # If this phase failed, set element to None
            print("Continuing to main scrolling loop with potential issues...")


        # --- Main Scrolling and Capture Loop (for schedule content) ---
        print("\n--- Starting main content scrolling and capture loop ---")
        if flutter_view_element: # Only proceed if flutter_view_element is valid
            try: # Ensure flutter_view_element is fresh for the loop
                flutter_view_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(FLUTTER_VIEW_LOCATOR)
                )
            except Exception as e:
                print(f"WARNING: Flutter view element became stale before scrolling loop: {e}")
                flutter_view_element = None # Cannot proceed with scrolling

        all_extracted_text_segments = []
        unique_lines_seen = set() # Keep track of all unique lines extracted so far
        drag_attempt_count = 0
        last_total_unique_lines_count = 0 # To detect if new content was added after a drag
        initial_content_empty = True

        while drag_attempt_count < MAX_DRAG_ATTEMPTS and flutter_view_element:
            # Check for end-of-scroll indicator *before* taking screenshot/dragging
            if END_OF_SCROLL_INDICATOR_LOCATOR:
                try:
                    WebDriverWait(driver, 5).until(EC.invisibility_of_element_located(END_OF_SCROLL_INDICATOR_LOCATOR))
                    print(f"End-of-scroll indicator '{END_OF_SCROLL_INDICATOR_LOCATOR}' is invisible. Assuming end of content.")
                    break # Exit loop if indicator is gone
                except:
                    print(f"End-of-scroll indicator '{END_OF_SCROLL_INDICATOR_LOCATOR}' is still visible or not found as invisible. Proceeding.")
                    pass

            current_extracted_text_lines = capture_and_ocr_segment(driver, flutter_view_element, drag_attempt_count)
            
            if current_extracted_text_lines:
                new_lines_in_this_segment = False
                for line in current_extracted_text_lines:
                    if line not in unique_lines_seen:
                        unique_lines_seen.add(line)
                        new_lines_in_this_segment = True

                if new_lines_in_this_segment or not all_extracted_text_segments:
                    all_extracted_text_segments.append("\n".join(current_extracted_text_lines))
                    initial_content_empty = False

            print(f"OCR performed. Total unique lines found: {len(unique_lines_seen)}")

            # Decide whether to scroll again
            if SCROLL_FLUTTER_VIEW_AND_CAPTURE and flutter_view_element:
                if len(unique_lines_seen) == last_total_unique_lines_count and drag_attempt_count > 0:
                    print("No new unique lines found after drag. Reached end of scrollable content or no more content.")
                    break

                drag_element_to_scroll(driver, flutter_view_element, DRAG_AMOUNT_Y_PIXELS, DRAG_START_X_OFFSET, DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT)
                last_total_unique_lines_count = len(unique_lines_seen)
            else:
                break

            drag_attempt_count += 1
            time.sleep(2) # Small delay between drag attempts to allow content to render

        if initial_content_empty and not unique_lines_seen:
            print("\nWARNING: Initial content OCR was empty and no unique lines were extracted across all attempts.")
            print("Please check: 1) If the schedule actually loaded in the browser. 2) If CROP_COORDINATES are correct. 3) OCR quality.")


        print("\n--- All Extracted Schedule Text (Raw Segments) ---")
        # Print raw segments as extracted
        for i, segment_text in enumerate(all_extracted_text_segments):
            print(f"\n--- Segment {i} Text ---")
            print(segment_text)
            print("-------------------------")

        # --- NEW: Save unique lines to a text file for accessibility ---
        if unique_lines_seen:
            output_text_filename = os.path.join(SCREENSHOT_OUTPUT_DIR, "extracted_schedule.txt")
            try:
                with open(output_text_filename, 'w', encoding='utf-8') as f:
                    # Sort lines for consistent output, if they are not inherently ordered
                    for line in sorted(list(unique_lines_seen)):
                        f.write(line + "\n")
                print(f"\n--- Extracted schedule saved to: {output_text_filename} ---")
            except Exception as e:
                print(f"Error saving extracted text to file: {e}")
        else:
            print("No unique schedule text extracted.")
        print("\n------------------------------------")


    except Exception as e: # OUTER EXCEPT BLOCK START (catches overall errors)
        print(f"An error occurred during web automation. Please ensure Chrome is launched with remote debugging:")
        print(f"Error details: {e}")
    finally: # FINALLY BLOCK START (ensures driver quits)
        # IMPORTANT: Do NOT close the browser if connecting to an external session,
        # otherwise it will shut down the manually launched Chrome instance.
        if driver: # Only call quit if driver was successfully initialized
            driver.quit()
            print("Chrome browser closed by script.")
        else:
            print("Script finished. Chrome browser was not launched or failed to initialize.")

# EOF