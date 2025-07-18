import datetime
import os.path
import sys # Added for command-line argument handling
import tkinter as tk # Added for GUI dialog
from tkinter import simpledialog # Added for GUI dialog
from PIL import Image
import csv
import json
import argparse
import hashlib # For generating consistent iCalUIDs
import uuid # For generating UUIDs

# Assuming schedule_extractor_config.py is accessible and defines OCR_FILEPATH
from schedule_extractor_config import OCR_FILEPATH 

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# The 'calendar' scope allows full read/write access to calendars.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json" # Your downloaded Google API credentials file

# Removed get_events_by_date_and_title and delete_event as they are no longer needed for iCalUID approach.
"""
def get_calendar_id_gui():
    # Prompts the user for the Google Calendar ID using a simple GUI dialog.
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
"""

def create_event(service, calendar_id, event_body):
    """
    Creates or updates a new event in the calendar using iCalUID for idempotency.

    Args:
        service: The authenticated Google Calendar API service object.
        calendar_id: The ID of the calendar.
        event_body: A dictionary containing the event's details, including 'iCalUID'.

    Returns:
        The created/updated event resource if successful, None otherwise.
    """
    try:
        # When iCalUID is provided, insert acts as an upsert (update if exists, create if new)
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all" # Set to 'all', 'externalOnly', or 'none' for notifications
        ).execute()
        print(f"Event created/updated: {event.get('htmlLink')}")
        return event
    except HttpError as error:
        print(f"Error creating/updating event: {error}")
        return None

def upsert_event_icaluid(service, calendar_id, event_data, calendar_timezone):
    """
    Upserts an event using the iCalUID approach for idempotency.
    This function replaces the previous add_event_idempotently.

    Args:
        service: The authenticated Google Calendar API service object.
        calendar_id: The ID of the calendar (e.g., 'primary').
        event_data: A dictionary containing the new event's details.
        calendar_timezone (str): The timezone of the target Google Calendar.
    """
    event_title = event_data.get('summary')
    
    # Determine if it's a dateTime event or an all-day date event
    start_time_str = None
    if 'dateTime' in event_data['start']:
        start_time_str = event_data['start']['dateTime']
        event_date = datetime.datetime.fromisoformat(start_time_str).date()
    elif 'date' in event_data['start']: # All-day event
        start_time_str = event_data['start']['date']
        event_date = datetime.datetime.strptime(start_time_str, '%Y-%m-%d').date()
    else:
        print("Error: Event start time must contain 'dateTime' or 'date'. Skipping event.")
        return

    if not event_title or not event_date or not start_time_str:
        print("Error: Event data must contain 'summary' and 'start' information. Skipping event.")
        return

    # Generate a consistent iCalUID for the event
    # This ensures that if the script runs multiple times, the same logical event
    # (defined by its title, start time, and date) will have the same iCalUID,
    # allowing Google Calendar to update it instead of creating a duplicate.
    unique_id_string = f"{event_title}-{start_time_str}-{event_data['end']['dateTime'] if 'dateTime' in event_data['end'] else event_data['end']['date']}-{calendar_id}"
    ical_uid = uuid.uuid5(uuid.NAMESPACE_URL, unique_id_string.encode('utf-8')).hex
    
    # Add iCalUID to the event body
    event_data['iCalUID'] = ical_uid
    event_data['timeZone'] = calendar_timezone # Ensure timezone is part of the event body

    print(f"\nAttempting to create/update event: '{event_title}' on {event_date} (iCalUID: {ical_uid})")

    # Call the create_event function, which now handles upsert logic via iCalUID
    create_event(service, calendar_id, event_data)
    print(f"Operation complete for event: '{event_title}' on {event_date}")


def main(calendar_id=None):

    """Shows basic usage of the Google Calendar API.
    Reads a CSV file and creates events in a specified Google Calendar.
    """
    #parser = argparse.ArgumentParser(description="Create Google Calendar events for schedule_extractor.")
    #parser.add_argument('--calendar', type=str, help='Google Calendar ID (e.g., primary or your_email@group.calendar.google.com)')
    #args = parser.parse_args()

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    # --- Calendar ID Input Handling ---
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

    try:
        service = build('calendar', 'v3', credentials=creds)

        # see above
        #calendar_id = args.calendar or input("Please enter the Google Calendar ID (e.g., your_email@group.calendar.google.com or primary): ")

        if not calendar_id:
            print("Calendar ID cannot be empty. Exiting.")
            return

        # Fetch the calendar's time zone
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        calendar_timezone = calendar.get('timeZone', 'America/New_York') # Default to New York if not found
        print(f"Using calendar time zone: {calendar_timezone}")

        ocr_csv_filepath = OCR_FILEPATH
        if not os.path.exists(ocr_csv_filepath):
            print(f"Error: CSV file not found at '{ocr_csv_filepath}'. Exiting.")
            return

        print(f"Attempting to read CSV from: {ocr_csv_filepath}")
        
        # Read events directly from CSV and process them
        with open(ocr_csv_filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Skip if essential fields are missing
                if not row.get('month') or not row.get('date') or not row.get('shift_start') or not row.get('shift_end'):
                    print(f"Skipping row due to missing date or shift times: {row}")
                    continue

                year = datetime.datetime.now().year # Or use a specific year if you have it
                month_str = row['month']
                day = int(row['date'])
                try:
                    month = datetime.datetime.strptime(month_str, "%b").month # "Jul" -> 7
                except ValueError:
                    try:
                        month = datetime.datetime.strptime(month_str, "%B").month # "July" -> 7
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
                    print(f"Skipping row due to invalid time format: {row}. Error: {e}")
                    continue

                # Build event body for the main shift
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

                event_body = {
                    'summary': 'THD', # Your desired event title
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
                
                # --- Use the new upsert function here with iCalUID ---
                upsert_event_icaluid(service, calendar_id, event_body, calendar_timezone)

    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
        if error.resp.status == 404:
            print(f"Calendar with ID '{calendar_id}' not found. Please check the Calendar ID.")
        elif error.resp.status == 403:
            print("Permission denied. Ensure the authenticated user has write access to the calendar.")
        elif error.resp.status == 400:
            print(f"Bad request. Check event data format or API limits.")
    except FileNotFoundError:
        print(f"The CSV file '{ocr_csv_filepath}' was not found. Please ensure it exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main(calendar_id)
