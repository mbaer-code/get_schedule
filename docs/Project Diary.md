# Project Diary: Schedule Extractor Application

## 1. Project Goal
The primary goal of this Python application is to automate the login process for the Home Depot WorkForce Tools (WFT) web application, navigate to the employee's schedule, minimize any obstructing graphical elements (like a calendar overlay), scroll through the entire schedule, capture screenshots, and extract the schedule data using OCR (Optical Character Recognition).

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

