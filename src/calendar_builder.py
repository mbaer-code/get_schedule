import datetime
import os.path
import sys
import tkinter as tk
from tkinter import simpledialog
import csv
import json
import argparse
import hashlib
import uuid

# Assuming schedule_extractor_config.py is accessible and defines OCR_FILEPATH
from schedule_extractor_config import OCR_FILEPATH

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

def get_calendar_id_gui():
    """Prompts the user for the Google Calendar ID using a simple GUI dialog."""
    try:
        root = tk.Tk()
        root.withdraw()
        calendar_id = simpledialog.askstring("Input", "Please enter the Google Calendar ID (e.g., 'primary'):")
        root.destroy()
        return calendar_id
    except Exception as e:
        print(f"ERROR: Exception in get_calendar_id_gui: {e}")
        return None

def create_event(service, calendar_id, event_body):
    """
    Creates or updates a new event in the calendar using iCalUID for idempotency.
    """
    try:
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all"
        ).execute()
        print(f"Event created/updated: {event.get('htmlLink')}")
        return event
    except HttpError as error:
        print(f"Error creating/updating event: {error}")
        return None

def upsert_event_icaluid(service, calendar_id, event_data, calendar_timezone):
    """
    Upserts an event using the iCalUID approach for idempotency.
    """
    event_title = event_data.get('summary')
    start_time_str = event_data['start'].get('dateTime', event_data['start'].get('date'))
    end_time_str = event_data['end'].get('dateTime', event_data['end'].get('date'))

    if not event_title or not start_time_str or not end_time_str:
        print("Error: Event data is missing essential fields. Skipping event.")
        return

    try:
        # Use hashlib to create a consistent, reproducible UID.
        unique_id_string = f"{str(event_title).strip()}-{str(start_time_str).strip()}-{str(end_time_str).strip()}-{str(calendar_id).strip()}"
        
        # Create a SHA-1 hash of the unique string.
        hash_object = hashlib.sha1(unique_id_string.encode('utf-8'))
        hex_digest = hash_object.hexdigest()

        # Format the hash into a UUID string.
        ical_uid = f"{hex_digest[:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}-{hex_digest[16:20]}-{hex_digest[20:32]}"

    except Exception as e:
        print(f"Error generating iCalUID for event '{event_title}': {e}")
        return
    
    event_data['iCalUID'] = ical_uid
    event_data['timeZone'] = calendar_timezone

    create_event(service, calendar_id, event_data)

def main(calendar_id=None):
    """
    Reads a CSV file, validates the data, and creates events in a Google Calendar with user confirmation.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    # Set a default calendar name for the script to use
    calendar_name = 'work-schedule-cloud'

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Check if the calendar exists
        calendar_list = service.calendarList().list().execute()
        existing_calendar = None
        for calendar_entry in calendar_list.get('items', []):
            if calendar_entry.get('summary') == calendar_name:
                existing_calendar = calendar_entry
                break

        if existing_calendar:
            # If the calendar exists, use its ID
            calendar_id = existing_calendar['id']
            print(f"The script will update the calendar: '{calendar_name}' with ID '{calendar_id}'")
        else:
            # If the calendar doesn't exist, create it
            print(f"Calendar '{calendar_name}' not found. Creating a new one...")
            new_calendar_body = {
                'summary': calendar_name,
                'timeZone': 'America/Los_Angeles' 
            }
            new_calendar = service.calendars().insert(body=new_calendar_body).execute()
            calendar_id = new_calendar['id']
            print(f"Successfully created new calendar: '{calendar_name}' with ID '{calendar_id}'")
            print(f"Using calendar time zone: America/Los_Angeles")
        
        calendar_timezone = 'America/Los_Angeles'

        ocr_csv_filepath = OCR_FILEPATH
        if not os.path.exists(ocr_csv_filepath):
            print(f"Error: CSV file not found at '{ocr_csv_filepath}'. Exiting.")
            return

        print(f"Attempting to read CSV from: {ocr_csv_filepath}")

        events_to_create = []
        fieldnames = ['png_filename', 'username', 'store_number', 'weekday', 'month', 'date', 'shift_start', 'meal_start', 'meal_end', 'shift_end', 'department']

        with open(ocr_csv_filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file, fieldnames=fieldnames, skipinitialspace=True)
            next(reader)  # Skip the header row

            for row in reader:
                # Robust data validation
                if not all(row.get(key) and row.get(key).strip() for key in ['month', 'date', 'shift_start', 'shift_end']):
                    print(f"Skipping row due to missing essential shift data: {row}")
                    continue

                year = datetime.datetime.now().year
                month_str = row['month']
                try:
                    day = int(row['date'])
                except (ValueError, KeyError) as e:
                    print(f"Skipping row due to invalid 'date' value: {row}. Error: {e}")
                    continue

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
                    print(f"Skipping row due to invalid time format: {row}. Error: {e}")
                    continue

                # Validate meal data to prevent errors.
                meal_start = row.get('meal_start', '').strip()
                meal_end = row.get('meal_end', '').strip()
                description = ""
                if meal_start and meal_end:
                    description = f"Meal: {meal_start} - {meal_end}"
                elif meal_start and not meal_end:
                    print(f"Skipping meal info for row with filename {row.get('png_filename')} due to missing end time.")
                elif meal_end and not meal_start:
                    print(f"Skipping meal info for row with filename {row.get('png_filename')} due to missing start time.")

                event_body = {
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
                events_to_create.append(event_body)
        
        print("\n--- Proposed Calendar Changes ---")
        for event in events_to_create:
            start_dt_obj = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_dt_obj = datetime.datetime.fromisoformat(event['end']['dateTime'])
            print(f"Event: {event['summary']} from {start_dt_obj.strftime('%b %d, %Y at %I:%M %p')} to {end_dt_obj.strftime('%I:%M %p')}")
            if event.get('description'):
                print(f"  - Description: {event['description']}")

        confirm = input("\nDo you want to add these events to your calendar? (Y/n): ")
        if confirm.lower() == 'y' or confirm == '':
            print("\nUpdating calendar...")
            for event_body in events_to_create:
                upsert_event_icaluid(service, calendar_id, event_body, calendar_timezone)
            print("\nCalendar update complete.")
        else:
            print("\nOperation cancelled by user. No changes were made.")

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
    main()
