import csv
import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# The 'calendar' scope allows full read/write access to calendars.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    """Shows basic usage of the Google Calendar API.
    Reads a CSV file and creates events in a specified Google Calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # The 'credentials.json' file is downloaded from Google Cloud Console.
            # Make sure it's in the same directory as this script.
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Prompt user for the calendar ID
        calendar_id = input("Please enter the Google Calendar ID (e.g., your_email@group.calendar.google.com or primary): ")
        if not calendar_id:
            print("Calendar ID cannot be empty. Exiting.")
            return

        # Prompt user for the CSV file path
        csv_file_path = input("Please enter the full path to your CSV file: ")
        if not os.path.exists(csv_file_path):
            print(f"Error: CSV file not found at '{csv_file_path}'. Exiting.")
            return

        print(f"Attempting to read CSV from: {csv_file_path}")
        events_to_create = []
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                # Expected CSV headers: Subject, Start Date, Start Time, End Date, End Time, Description, Location
                # Date format: YYYY-MM-DD (e.g., 2023-10-27)
                # Time format: HH:MM (e.g., 09:00)
                for row in reader:
                    try:
                        summary = row.get('Subject')
                        start_date_str = row.get('Start Date')
                        start_time_str = row.get('Start Time')
                        end_date_str = row.get('End Date')
                        end_time_str = row.get('End Time')
                        description = row.get('Description', '')
                        location = row.get('Location', '')

                        if not all([summary, start_date_str, start_time_str, end_date_str, end_time_str]):
                            print(f"Skipping row due to missing required fields: {row}")
                            continue

                        # Combine date and time strings and parse them
                        start_datetime_str = f"{start_date_str} {start_time_str}"
                        end_datetime_str = f"{end_date_str} {end_time_str}"

                        start_datetime = datetime.datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
                        end_datetime = datetime.datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')

                        event = {
                            'summary': summary,
                            'location': location,
                            'description': description,
                            'start': {
                                'dateTime': start_datetime.isoformat(),
                                'timeZone': 'America/Los_Angeles', # You can change this to your desired timezone
                            },
                            'end': {
                                'dateTime': end_datetime.isoformat(),
                                'timeZone': 'America/Los_Angeles', # You can change this to your desired timezone
                            },
                        }
                        events_to_create.append(event)
                    except ValueError as e:
                        print(f"Error parsing date/time in row {reader.line_num}: {row} - {e}. Skipping row.")
                    except KeyError as e:
                        print(f"Missing expected CSV column: {e} in row {reader.line_num}: {row}. Please check your CSV headers. Skipping row.")

            if not events_to_create:
                print("No valid events found in the CSV file. Please check the CSV format and data.")
                return

            print(f"Found {len(events_to_create)} events to create.")
            for event in events_to_create:
                try:
                    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
                    print(f"Event created: {created_event.get('htmlLink')}")
                except HttpError as error:
                    print(f"An error occurred creating event '{event.get('summary')}': {error}")
                    if error.resp.status == 404:
                        print(f"Calendar with ID '{calendar_id}' not found. Please check the Calendar ID.")
                    elif error.resp.status == 403:
                        print("Permission denied. Ensure the service account or authenticated user has write access to the calendar.")
                    elif error.resp.status == 400:
                        print(f"Bad request for event '{event.get('summary')}'. Check event data format.")


        except FileNotFoundError:
            print(f"The CSV file '{csv_file_path}' was not found.")
        except Exception as e:
            print(f"An unexpected error occurred while reading the CSV: {e}")

    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
    except Exception as e:
        print(f"An unexpected error occurred during API interaction: {e}")

if __name__ == '__main__':
    main()
