"""
One-time helper: run this locally to authorize your Google account and print
a refresh token to put in GOOGLE_REFRESH_TOKEN.

Usage:
    python manage.py get_google_refresh_token --client-id ... --client-secret ...

or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in your .env first and just run:
    python manage.py get_google_refresh_token
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bookings.services.google_calendar import SCOPES


class Command(BaseCommand):
    help = "Runs a local OAuth flow and prints a Google Calendar refresh token."

    def add_arguments(self, parser):
        parser.add_argument("--client-id", default=None)
        parser.add_argument("--client-secret", default=None)

    def handle(self, *args, **options):
        from google_auth_oauthlib.flow import InstalledAppFlow

        client_id = options["client_id"] or settings.GOOGLE_CLIENT_ID
        client_secret = options["client_secret"] or settings.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            raise CommandError(
                "Pass --client-id/--client-secret or set GOOGLE_CLIENT_ID/"
                "GOOGLE_CLIENT_SECRET in your .env first."
            )

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_local_server(port=0)

        self.stdout.write(self.style.SUCCESS("Success! Add this to your .env:"))
        self.stdout.write(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}")
