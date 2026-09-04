"""
Creates the admin (teacher) superuser account from env vars if it doesn't
already exist yet. Safe to run on every deploy/build, unlike Django's
built-in createsuperuser --noinput, which errors if the user already exists.

Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL,
DJANGO_SUPERUSER_PASSWORD. Does nothing if any of those are unset.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates the admin superuser from env vars if it doesn't exist yet."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not (username and email and password):
            self.stdout.write("DJANGO_SUPERUSER_* env vars not set, skipping.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists, skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
