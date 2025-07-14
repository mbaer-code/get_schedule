import csv
import datetime
import os.path
import json
import argparse
from datetime import timezone
from schedule_extractor_config import OCR_FILEPATH

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# The 'calendar' scope allows full read/write access to calendars.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_thd_events_from_csv(service, calendar_id, ocr_csv_filepath):
    with open(ocr_csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Skip if essential fields are missing
            if not row.get('month') or not row.get('date') or not row.get('shift_start') or not row.get('shift_end'):
                print(f"Skipping row due to missing date or shift times: {row}")
                continue

            # Parse date and times
            year = datetime.datetime.now().year  # Or use a specific year if you have it
            month_str = row['month']
            day = int(row['date'])
            try:
                month = datetime.datetime.strptime(month_str, "%b").month  # "Jul" -> 7
            except ValueError:
                try:
                    month = datetime.datetime.strptime(month_str, "%B").month  # "July" -> 7
                except ValueError:
                    print(f"Skipping row due to invalid month: {row}")
                    continue

            # Parse start and end times
            try:
                start_time_str = f"{year}-{month:02d}-{day:02d} {row['shift_start']}"
                end_time_str = f"{year}-{month:02d}-{day:02d} {row['shift_end']}"
                start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %I:%M %p")
                end_dt = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %I:%M %p")
            except Exception as e:
                print(f"Skipping row due to invalid time format: {row}")
                continue

            # Build event
            meal_start = row.get('meal_start', '')
            meal_end = row.get('meal_end', '')
            # Add more meal info here if you have other fields
            meal_info = ""
            if meal_start and meal_end:
                meal_info += f"Meal: {meal_start} - {meal_end}\n"
            elif meal_start:
                meal_info += f"Meal start: {meal_start}\n"
            elif meal_end:
                meal_info += f"Meal end: {meal_end}\n"

            # You can add more fields to the description as needed
            description = meal_info.strip()

            event = {
                'summary': 'THD',
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/New_York',  # <-- Add this line (or your local time zone)
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/New_York',  # <-- Add this line (or your local time zone)
                },
                'description': description
            }

            # Insert event into Google Calendar
            try:
                created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"Event created: {created_event.get('htmlLink')}")
            except Exception as e:
                print(f"Failed to create event for row: {row}\nError: {e}")

def main():
    """Shows basic usage of the Google Calendar API.
    Reads a CSV file and creates events in a specified Google Calendar.
    """
    #parser = argparse.ArgumentParser(description="Create Google Calendar events from a CSV file.")
    parser = argparse.ArgumentParser(description="Create Google Calendar events for schedule_extractor.")
    parser.add_argument('--calendar', type=str, help='Google Calendar ID (e.g., primary or your_email@group.calendar.google.com)')
    #parser.add_argument('--csv', type=str, help='Path to the CSV file')
    args = parser.parse_args()

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        calendar_id = args.calendar or input("Please enter the Google Calendar ID (e.g., your_email@group.calendar.google.com or primary): ")
        if not calendar_id:
            print("Calendar ID cannot be empty. Exiting.")
            return

        # Fetch the calendar's time zone
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        calendar_timezone = calendar.get('timeZone', 'America/New_York')
        print(f"Using calendar time zone: {calendar_timezone}")

        ocr_csv_filepath = OCR_FILEPATH
        #ocr_csv_filepath = args.csv or input("Enter path to OCR CSV file else hit Enter for default: ")
        if not os.path.exists(ocr_csv_filepath):
            print(f"Error: CSV file not found at '{ocr_csv_filepath}'. Exiting.")
            return

        print(f"Attempting to read CSV from: {ocr_csv_filepath}")
        events_to_create = []
        try:
            with open(ocr_csv_filepath, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not row.get('month') or not row.get('date') or not row.get('shift_start') or not row.get('shift_end'):
                        print(f"Skipping row due to missing date or shift times: {row}")
                        continue

                    year = datetime.datetime.now().year
                    month_str = row['month']
                    day = int(row['date'])
                    try:
                        month = datetime.datetime.strptime(month_str, "%b").month
                    except ValueError:
                        try:
                            month = datetime.datetime.strptime(month_str, "%B").month
                        except ValueError:
                            print(f"Skipping row due to invalid month: {row}")
                            continue

                    try:
                        start_time_str = f"{year}-{month:02d}-{day:02d} {row['shift_start']}"
                        end_time_str = f"{year}-{month:02d}-{day:02d} {row['shift_end']}"
                        start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %I:%M %p")
                        end_dt = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %I:%M %p")
                    except Exception as e:
                        print(f"Skipping row due to invalid time format: {row}")
                        continue

                    meal_start = row.get('meal_start', '')
                    meal_end = row.get('meal_end', '')
                    meal_info = ""
                    if meal_start and meal_end:
                        meal_info += f"Meal: {meal_start} - {meal_end}\n"
                    elif meal_start:
                        meal_info += f"Meal start: {meal_start}\n"
                    elif meal_end:
                        meal_info += f"Meal end: {meal_end}\n"

                    description = meal_info.strip()

                    event = {
                        'summary': 'THD',
                        'start': {
                            'dateTime': start_dt.isoformat(),
                            'timeZone': calendar_timezone,
                        },
                        'end': {
                            'dateTime': end_dt.isoformat(),
                            'timeZone': calendar_timezone,
                        },
                        'description': description
                    }
                    event['_start_dt'] = start_dt
                    event['_end_dt'] = end_dt
                    events_to_create.append(event)

                    # --- Add a separate meal event if both meal_start and meal_end exist ---
                    """
                    if meal_start and meal_end:
                        try:
                            meal_start_dt = datetime.datetime.strptime(
                                f"{year}-{month:02d}-{day:02d} {meal_start}", "%Y-%m-%d %I:%M %p"
                            )
                            meal_end_dt = datetime.datetime.strptime(
                                f"{year}-{month:02d}-{day:02d} {meal_end}", "%Y-%m-%d %I:%M %p"
                            )
                            meal_event = {
                                'summary': 'Meal',
                                'start': {
                                    'dateTime': meal_start_dt.isoformat(),
                                    'timeZone': calendar_timezone,
                                },
                                'end': {
                                    'dateTime': meal_end_dt.isoformat(),
                                    'timeZone': calendar_timezone,
                                },
                                'description': f"Meal break during shift"
                            }
                            meal_event['_start_dt'] = meal_start_dt
                            meal_event['_end_dt'] = meal_end_dt
                            events_to_create.append(meal_event)
                        except Exception as e:
                            print(f"Could not create meal event for row: {row}\nError: {e}")
                    """

            if not events_to_create:
                print("No valid events found in the CSV file. Please check the CSV format and data.")
                return

            print(f"Found {len(events_to_create)} events to create.")
            for event in events_to_create:
                try:
                    # Remove overwrite logic: just insert every event
                    event.pop('_start_dt', None)
                    event.pop('_end_dt', None)
                    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
                    print(f"Event created: {created_event.get('htmlLink')}")
                except HttpError as error:
                    print(f"An error occurred creating event '{event.get('summary')}': {error}")
                    if error.resp.status == 404:
                        print(f"Calendar with ID '{calendar_id}' not found. Please check the Calendar ID.")
                    elif error.resp.status == 403:
                        print("Permission denied. Ensure the authenticated user has write access to the calendar.")
                    elif error.resp.status == 400:
                        print(f"Bad request for event '{event.get('summary')}'. Check event data format.")

        except FileNotFoundError:
            print(f"The CSV file '{ocr_csv_filepath}' was not found.")
        except Exception as e:
            print(f"An unexpected error occurred while reading the CSV: {e}")

    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
    except Exception as e:
        print(f"An unexpected error occurred during API interaction: {e}")

if __name__ == '__main__':
    main()
