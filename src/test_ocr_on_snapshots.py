import os
from PIL import Image
import pytesseract

SCREENSHOT_OUTPUT_DIR = r"C:\temp\ScheduleScreenshots"
num_snapshots = 10  # Adjust if you have more/less

output_path = os.path.join(SCREENSHOT_OUTPUT_DIR, "all_ocr_results.txt")

with open(output_path, "w", encoding="utf-8") as f:
    for i in range(1, num_snapshots + 1):
        img_path = os.path.join(SCREENSHOT_OUTPUT_DIR, f"dom_scroll_{i}_canvas.png")
        if not os.path.exists(img_path):
            print(f"File not found: {img_path}")
            continue

        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        print(f"--- OCR Result {i} ---\n{text}\n{'-'*40}")
        f.write(f"--- OCR Result {i} ---\n{text}\n{'-'*40}\n")

print(f"OCR results saved to {output_path}")