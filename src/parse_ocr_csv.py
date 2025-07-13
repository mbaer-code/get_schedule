import csv
import os
import re
from datetime import datetime, timedelta

CSV_PATH = r"C:\temp\ScheduleScreenshots\ocr_results.csv"  # Adjust if needed

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


# -- MAIN --

if __name__ == "__main__":

    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
    else:
        entries = parse_ocr_csv(CSV_PATH)
        print(f"Found {len(entries)} valid entries.")
        with open('ocr_results_structured.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=COLUMN_NAMES)
            writer.writeheader()
            for entry in entries:
                writer.writerow(entry)
        print("Structured CSV written as ocr_results_structured.csv")


