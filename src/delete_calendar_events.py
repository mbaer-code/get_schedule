import os.path
import argparse
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


def delete_all_events_in_range(service, calendar_id, date_range_days=90):
    """Delete ALL events within a date range (use with caution!)"""
    try:
        # Calculate date range
        now = datetime.now()
        time_min = (now - timedelta(days=30)).isoformat() + 'Z'
        time_max = (now + timedelta(days=date_range_days)).isoformat() + 'Z'
        
        print(f"Searching for ALL events from {(now - timedelta(days=30)).strftime('%Y-%m-%d')} to {(now + timedelta(days=date_range_days)).strftime('%Y-%m-%d')}")
        
        # Get all events in the time range (no search query)
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print("No events found in the specified date range.")
            return
        
        print(f"Found {len(events)} total events:")
        
        # Show events and ask for confirmation
        for i, event in enumerate(events[:10], 1):  # Show first 10 events
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No Title')
            ical_uid = event.get('iCalUID', 'No iCalUID')
            print(f"  {i}. {summary} - {start} (iCalUID: {ical_uid[:8]}...)")
        
        if len(events) > 10:
            print(f"  ... and {len(events) - 10} more events")
        
        # Ask for confirmation
        confirm = input(f"\nDo you want to delete ALL {len(events)} events? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("Deletion cancelled.")
            return
        
        # Delete events
        deleted_count = 0
        failed_count = 0
        
        for event in events:
            try:
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No Title')
                print(f"✓ Deleted: {summary} - {start}")
                deleted_count += 1
            except HttpError as error:
                print(f"✗ Failed to delete event {event['id']}: {error}")
                failed_count += 1
            except Exception as e:
                print(f"✗ Unexpected error deleting event {event['id']}: {e}")
                failed_count += 1
        
        print(f"\n--- DELETION SUMMARY ---")
        print(f"Events deleted: {deleted_count}")
        print(f"Failed deletions: {failed_count}")
        print(f"Total processed: {len(events)}")
        
    except Exception as e:
        print(f"Error searching for events: {e}")


def list_all_events_in_range(service, calendar_id, date_range_days=90):
    """List ALL events within a date range"""
    try:
        # Calculate date range
        now = datetime.now()
        time_min = (now - timedelta(days=30)).isoformat() + 'Z'
        time_max = (now + timedelta(days=date_range_days)).isoformat() + 'Z'
        
        print(f"Searching for ALL events from {(now - timedelta(days=30)).strftime('%Y-%m-%d')} to {(now + timedelta(days=date_range_days)).strftime('%Y-%m-%d')}")
        
        # Get all events in the time range (no search query)
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print("No events found.")
            return
        
        print(f"Found {len(events)} total events:")
        
        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No Title')
            ical_uid = event.get('iCalUID', 'No iCalUID')
            description = event.get('description', '')
            print(f"  {i}. {summary} - {start}")
            print(f"     iCalUID: {ical_uid}")
            if description:
                print(f"     Description: {description}")
            print()
        
    except Exception as e:
        print(f"Error searching for events: {e}")


def main():
    """Delete THD events from Google Calendar"""
    parser = argparse.ArgumentParser(description="Delete or list THD events from Google Calendar.")
    parser.add_argument('--calendar', type=str, help='Google Calendar ID (e.g., primary or your_email@group.calendar.google.com)')
    parser.add_argument('--action', type=str, choices=['list', 'delete'], default='list', help='Action to perform: list or delete events')
    parser.add_argument('--summary', type=str, default='THD', help='Event summary to search for (default: THD)')
    parser.add_argument('--days', type=int, default=90, help='Number of days in the future to search (default: 90)')
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

        calendar_id = args.calendar or input("Please enter the Google Calendar ID (e.g., mbaer.home@gmail.com or primary): ")
        if not calendar_id:
            print("Calendar ID cannot be empty. Exiting.")
            return

        # Verify calendar exists
        try:
            calendar = service.calendars().get(calendarId=calendar_id).execute()
            print(f"Working with calendar: {calendar.get('summary', calendar_id)}")
        except HttpError as error:
            if error.resp.status == 404:
                print(f"Calendar with ID '{calendar_id}' not found.")
                return
            else:
                print(f"Error accessing calendar: {error}")
                return

        if args.action == 'list':
            if args.summary == 'ALL':
                list_all_events_in_range(service, calendar_id, args.days)
            else:
                print(f"Searching specifically for '{args.summary}' events...")
                list_all_events_in_range(service, calendar_id, args.days)
        elif args.action == 'delete':
            if args.summary == 'ALL':
                delete_all_events_in_range(service, calendar_id, args.days)
            else:
                print(f"Will delete events containing '{args.summary}' in title...")
                delete_all_events_in_range(service, calendar_id, args.days)

    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
