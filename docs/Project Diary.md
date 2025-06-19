# Project Diary: Schedule Extractor Application

## 1. Project Goal
The primary goal of this Python application is to automate the login process for the Home Depot WorkForce Tools (WFT) web application, navigate to the employee's schedule, minimize any obstructing graphical elements (like a calendar overlay), scroll through the entire schedule, capture screenshots, and extract the schedule data using OCR (Optical Character Recognition).

## 2. Collaborative Workflow with Gemini
* **Gemini's Role:** Provides complete, updated Python code files (one at a time) and detailed instructions.
* **User's Role:**
    * Requests the next file when ready.
    * Copies the provided code using the copy icon.
    * Pastes the code into the designated local file in VS Code, replacing its entire content.
    * Saves the file immediately.
    * Executes the main Python script (`py schedule_extractor.py`) in a Bash shell.
    * Carefully observes the browser's behavior during execution.
    * Reports the full console output back to Gemini.
    * Visually inspects generated screenshot files (`C:\temp\ScheduleScreenshots`) and reports findings (e.g., successful minimization, unexpected interactions, specific coordinates from filenames).
    * Uses browser Developer Tools for inspection of web elements if necessary.

## 3. Key Tools & Technologies
* **Python:** Programming language for the application logic.
* **Selenium:** Web automation framework.
* **undetected_chromedriver:** A patched ChromeDriver that attempts to evade detection by anti-bot systems.
* **Pillow (PIL):** Python Imaging Library for image manipulation (cropping screenshots).
* **pytesseract:** Python wrapper for Tesseract OCR.
* **Tesseract OCR:** Open-source OCR engine (requires system installation).
* **psutil:** For checking running Chrome processes to prevent conflicts.
* **VS Code:** Integrated Development Environment for editing code.
* **Bash Shell:** For executing Python scripts.
* **Flutter:** The web application is built with Flutter, which renders to a single canvas, making traditional DOM element identification difficult and requiring coordinate-based interaction.

## 4. Project Files
* `schedule_extractor_config.py`: Configuration variables (paths, URLs, coordinates, locators).
* `schedule_extractor_utils.py`: Utility functions (e.g., drag/swipe, process checks).
* `schedule_extractor.py`: Main script orchestrating the automation and data extraction.
* `project_diary.md`: This very file, for project documentation and continuity.

## 5. Key Challenges & Solutions Explored
* **Anti-bot Detection:** Addressed by `undetected_chromedriver` and various Chrome options.
* **Flutter Element Interaction:**
    * Standard Selenium locators (ID, class) are ineffective.
    * **Solution:** Rely on pixel-based X, Y coordinates relative to the `flutter-view` element.
    * **Solution:** Implemented "hunt and peck" (grid search) strategy to find correct X, Y coordinates by trial and error, visually verifying results via screenshots.
    * **Solution:** Used `perform_swipe_on_element` with `(0,0)` movement for precise "taps."
* **Screenshot Management:** Implemented `shutil.rmtree` and `os.makedirs` for robust cleanup of `C:\temp\ScheduleScreenshots` before each run.
* **Inconsistent Click Behavior:** Experienced cases where previously successful clicks (e.g., `750, 375`) stopped working or had different effects (e.g., clicking day buttons instead of minimizing). This necessitated re-hunting and precise observation.
* **Multi-step Minimization:** Discovered that two distinct minimization steps are required to fully expose the schedule, followed by an initial scroll.

## 6. Current Status (June 13, 2025)

**Successful Steps (Confirmed & Robust):**
* Chrome browser launch with `undetected_chromedriver`.
* Cleanup of Chrome user data and screenshot directories.
* Navigation to `WEB_APP_URL`.
* Handling of login page (user input for credentials).
* Successful navigation from Dashboard to **Schedule View** by clicking `(100, 200)`.
* **PRIMARY CALENDAR MINIMIZE CONFIRMED:** Found the precise coordinates to minimize the **large calendar graphic**: **`(730, 440)`**.

**Key Coordinates Confirmed So Far:**
* `SCHEDULE_CLICK_X_OFFSET = 100`
* `SCHEDULE_CLICK_Y_OFFSET = 200`
    * *(Purpose: Click "My Schedule" tile on Dashboard)*
* `SCHEDULE_MINIMIZE_PRIMARY_X = 730`
* `SCHEDULE_MINIMIZE_PRIMARY_Y = 440`
    * *(Purpose: Minimize the large calendar graphic on the Schedule View)*
* `SCHEDULE_MINIMIZE_SECONDARY_X = 215`
* `SCHEDULE_MINIMIZE_SECONDARY_Y = 284`
    * *(Purpose: Minimize the *second* element that appears after the primary calendar graphic is minimized. Bbox: 144,183 x 141,202)*

**Current File Versions:**
* `schedule_extractor_config.py`: **0.0.17**
* `schedule_extractor_utils.py`: **0.0.4**
* `schedule_extractor.py` (Main): **0.0.74**

## 7. Future Plans (Next Steps)

1.  **Implement Full Minimization Sequence:**
    * Modify the `schedule_extractor.py` (Main) script to:
        * Perform the primary minimize click (`SCHEDULE_MINIMIZE_PRIMARY_X/Y`).
        * Add a wait (e.g., `time.sleep()`) for the secondary element to appear.
        * Perform the secondary minimize click (`SCHEDULE_MINIMIZE_SECONDARY_X/Y`).
        * Add a wait after the secondary minimize.
        * Implement an initial "swipe up" to ensure the schedule content starts from the very top before main scrolling begins.
2.  **Robust Scrolling for All Schedule Views:**
    * Confirm `DRAG_AMOUNT_Y_PIXELS` and `DRAG_START_X_OFFSET` work optimally.
    * Refine `END_OF_SCROLL_INDICATOR_LOCATOR` to reliably detect the end of the schedule content.
3.  **Refine OCR & Data Processing:**
    * Review extracted `extracted_schedule.txt` for accuracy and formatting issues.
    * Implement more advanced image preprocessing (if `ENABLE_IMAGE_PREPROCESSING` is needed).
    * Potentially parse extracted text into structured data (e.g., CSV, JSON).

## 8. Important Notes for Handover
* **Chrome Browser Version:** Ensure `CHROME_MAJOR_VERSION` in `schedule_extractor_config.py` always matches the user's installed Chrome browser's major version (`chrome://version`).
* **Tesseract OCR:** Must be installed on the system, and `TESSERACT_PATH` in `schedule_extractor_config.py` must point to its executable.
* **Manual CAPTCHA:** Be prepared to manually solve the "Are you human?" CAPTCHA if it appears during initial navigation. The script pauses for this.
* **Visual Confirmation is Key:** For Flutter apps, always rely on visual inspection of screenshots and browser behavior, as direct element access is limited.