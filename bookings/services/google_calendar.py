"""
Creates an event on the teacher's Google Calendar when a booking is approved.

Setup (one time, in Google Cloud Console):
  1. Create a project, enable the "Google Calendar API".
  2. Create OAuth 2.0 Client credentials (type: Desktop app).
  3. Run `python manage.py get_google_refresh_token` and follow the printed
     URL to authorize your Google account; it prints a refresh token.
  4. Put GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in your
     .env (locally) or your host's environment variables (production).

If those env vars are not set, calendar sync is skipped (useful for local
development / tests) rather than raising.
"""

import datetime
from typing import Optional

from django.conf import settings

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def is_configured() -> bool:
    return bool(
        settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and settings.GOOGLE_REFRESH_TOKEN
    )


def _get_credentials():
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def create_lesson_event(slot, booking_request) -> Optional[str]:
    """Creates a calendar event for an approved booking. Returns the event id, or None if skipped."""
    if not is_configured():
        return None

    from googleapiclient.discovery import build

    credentials = _get_credentials()
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    start = datetime.datetime.combine(slot.date, slot.start_time)
    end = datetime.datetime.combine(slot.date, slot.end_time)
    tz = settings.TIME_ZONE

    event = {
        "summary": f"Voice Lesson - {booking_request.student_name}",
        "description": (
            f"Student: {booking_request.student_name}\n"
            f"Email: {booking_request.student_email}\n"
            f"Phone: {booking_request.student_phone}\n"
            f"Message: {booking_request.message}"
        ),
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
    }

    created = service.events().insert(
        calendarId=settings.GOOGLE_CALENDAR_ID, body=event
    ).execute()
    return created.get("id")


def delete_lesson_event(event_id: str) -> None:
    if not is_configured() or not event_id:
        return

    from googleapiclient.discovery import build

    credentials = _get_credentials()
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    service.events().delete(
        calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id
    ).execute()
