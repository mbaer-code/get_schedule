# =============================================================================
# schedule_extractor_config.py
# -----------------------------------------------------------------------------
# Configuration file for schedule_extractor.py.
# Stores constants and settings for browser automation, element locations,
# and other script parameters used throughout the extraction process.
#
# Author: Martin Baer
# Version: 0.0.80
# Created: 2024-06-26
# License: MIT
# -----------------------------------------------------------------------------
# Notes:
#   - Update these values to match your environment and web app structure.
#   - Used by both the main script and utility functions.
# =============================================================================

from selenium.webdriver.common.by import By # Imports By for locator definitions

# IMPORTANT:
# 1. Download ChromeDriver: With undetected_chromedriver, you often don't need to
#    manually download ChromeDriver, as it tries to manage it automatically.
#    However, if you encounter issues, ensure your Chrome browser is up-to-date.
# 2. Download Tesseract OCR: Install Tesseract OCR on your system.
#    Windows installer: https://tesseract-ocr.github.io/tessdoc/Installation.html#windows
#    After installation, locate the tesseract.exe path.
#    If tesseract.exe is not in your system PATH, you must specify its location here.

# Path to your ChromeDriver executable (undetected_chromedriver often finds its own, but can provide if needed)
CHROMEDRIVER_PATH = r'C:\\Program Files\\Google\Webdrivers\\chromedriver-win64\\chromedriver.exe' # Kept for potential fallback

# Path to your Tesseract executable (e.g., 'C:\\Program Files\\TESSERACT-OCR\\tesseract.exe')
# Using raw string (r'...') to avoid "invalid escape sequence" warnings
TESSERACT_PATH = r'C:\\Program Files\\TESSERACT-OCR\\tesseract.exe' # Corrected common install path for Tesseract, verify yours

# URL of the web application you want to access
WEB_APP_URL = 'https://wft.homedepot.com/'

# --- ABSOLUTE PATH FOR SCREENSHOT OUTPUT ---
# Screenshots will now always be saved here, regardless of CWD.
SCREENSHOT_OUTPUT_DIR = 'C:\\temp\\ScheduleScreenshots'
SCREENSHOT_BASE_NAME = 'flutter_view_screenshot' # Base name, will add _0, _1, etc.

# User data directory for Chrome. This stores your browser profile (cookies, login sessions).
# undetected_chromedriver can use this for persistence.
CHROME_USER_DATA_DIR = "C:\\SeleniumChromeProfile"

# --- Chrome Browser Version for undetected_chromedriver ---
# IMPORTANT: Replace 0 with YOUR Chrome browser's major version number (e.g., 125, 126).
# You can find this by typing chrome://version into your Chrome browser's address bar.
CHROME_MAJOR_VERSION = 137 # <--- IMPORTANT: YOU NEED TO PROVIDE THIS (e.g., 137, based on your previous output)


# --- USER CREDENTIALS (for automated login) ---
# IMPORTANT: These will be prompted at runtime and NOT stored in the script file.
USERNAME_PROMPT = "" # Will be filled by user input
PASSWORD_PROMPT = "" # Will be filled by user input

# --- LOGIN PAGE ELEMENT LOCATORS ---
# These were identified by user.
LOGIN_USERNAME_LOCATOR = (By.ID, "inputUsername")
LOGIN_PASSWORD_LOCATOR = (By.ID, "inputPassword")
LOGIN_BUTTON_LOCATOR = (By.ID, "buttonSignOn")


# --- NEW CONFIGURATION FOR FLUTTER VIEW TARGETING ---
# Identified from the provided Elements window content:
# The Flutter application is contained within a <flutter-view> element.
FLUTTER_VIEW_LOCATOR = (By.TAG_NAME, "flutter-view")

# --- INTERMEDIATE PAGE LOCATORS (for potential security checks or navigation) ---
# If a "Continue" or similar button appears after initial login but before the main app,
# define its locator here. Otherwise, set to None.
SECURITY_CHECK_CONTINUE_BUTTON_LOCATOR = None # <--- IMPORTANT: FIND AND SET THIS if needed, e.g., (By.ID, "continueButton")

# Coordinates to click/swipe on the intermediate dashboard page to activate the schedule.
# These are relative to the 'flutter-view' element's top-left corner.
SCHEDULE_CLICK_X_OFFSET = 100 # Keep X as is
SCHEDULE_CLICK_Y_OFFSET = 90 # Adjusted Y to target "Schedule" tile (higher up)


# Coordinates for clicking the PRIMARY calendar graphic to minimize it.
# This is the large graphic obscuring the schedule data.
SCHEDULE_MINIMIZE_PRIMARY_X = 730 # CONFIRMED: X coordinate for primary calendar graphic minimize
SCHEDULE_MINIMIZE_PRIMARY_Y = 440 # CONFIRMED: Y coordinate for primary calendar graphic minimize

# Coordinates for clicking the SECONDARY element (e.g., detail box) to minimize it.
# This appears AFTER the primary graphic is minimized.
SCHEDULE_MINIMIZE_SECONDARY_X = 215 # CONFIRMED from Bounding Box (Center X for secondary minimizer)
SCHEDULE_MINIMIZE_SECONDARY_Y = 284 # CONFIRMED from Bounding Box (Center Y for secondary minimizer)


# --- OCR IMAGE CROPPING AND PRE-PROCESSING SETTINGS ---
# Set to True if you want to crop the screenshot before OCR.
# You will need to determine the crop coordinates by inspecting 'flutter_view_screenshot.png'.
ENABLE_SCREENSHOT_CROPPING = True
# Coordinates for cropping: (left, top, right, bottom)
# These should define the bounding box of the *schedule content itself*, excluding the sidebar.
# NOTE: These coordinates might need adjustment for smaller windows.
CROP_COORDINATES = (540, 88, 1045, 584)

# Set to True if you want to apply image pre-processing for better OCR results.
ENABLE_IMAGE_PREPROCESSING = False

# --- LOCATOR FOR WAITING FOR INITIAL DASHBOARD CONTENT LOAD ---
# This is CRUCIAL for robust initial dashboard loading.
# This was identified in previous discussions but not fully used for a specific element.
# For now, the time.sleep(15) handles this after flutter_view_element is found.

# --- LOCATOR FOR WAITING FOR SCHEDULE PAGE CONTENT TO LOAD ---
# This is CRUCIAL for robust initial loading *after* navigating to the schedule view.
# This will likely be the LOADING ICON disappearing or a key element appearing on the schedule itself.
# IMPORTANT: YOU NEED TO PROVIDE THIS.
SCHEDULE_PAGE_LOAD_INDICATOR = None


# --- LOCATOR FOR END-OF-SCROLL INDICATOR ---
# This element should indicate the end of the scrollable content.
# Reverted to None to allow all drag attempts and to diagnose with screenshots.
# IMPORTANT: YOU NEED TO FIND A RELIABLE ONE.
END_OF_SCROLL_INDICATOR_LOCATOR = None


# --- SCROLLING SETTINGS FOR FLUTTER VIEW ---
# Use mouse drag/swipe to scroll the Flutter canvas
SCROLL_FLUTTER_VIEW_AND_CAPTURE = True
# Amount to drag (positive Y for dragging downwards on screen, negative for upwards)
# This will effectively scroll the content upwards (showing content further down)
# Set to a value that scrolls approximately one "page" of content.
# NOTE: This might need adjustment for smaller windows.
DRAG_AMOUNT_Y_PIXELS = 400 # Positive to drag mouse DOWNWARDS (scrolls content UPWARDS visually)

# Starting X position for the drag (within the element's width)
# This is relative to the element's top-left corner
DRAG_START_X_OFFSET = 200 # Adjust based on your schedule content's X position within the Flutter view
# Starting Y position for the drag (relative to element's height). 0.1 is near the top.
DRAG_START_Y_OFFSET_RELATIVE_TO_ELEMENT_HEIGHT = 0.1

MAX_DRAG_ATTEMPTS = 10

# EOF