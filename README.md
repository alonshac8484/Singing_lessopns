# Singing / Voice Lessons Booking

A small CRM for booking singing/voice lessons. Each week the teacher publishes
lesson slots; students submit a booking request for an open slot; once the
teacher approves it in the admin panel, the lesson is added to the teacher's
Google Calendar and the slot becomes permanently unavailable.

## Stack

Django (with its built-in admin as the teacher's slot/approval dashboard),
SQLite locally / Postgres in production, Google Calendar API for calendar
sync, deployed on Render.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Public site: http://127.0.0.1:8000/slots/
- Admin (add slots, approve/reject requests): http://127.0.0.1:8000/admin/

## Google Calendar setup (optional but needed for calendar sync)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project and enable the **Google Calendar API**.
2. Create OAuth 2.0 credentials of type **Desktop app**; note the client ID
   and secret.
3. Run, locally:
   ```bash
   python manage.py get_google_refresh_token --client-id <id> --client-secret <secret>
   ```
   This opens a browser to authorize your Google account and prints a
   refresh token.
4. Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`
   to your `.env` (locally) or Render environment variables (production).

Without these set, the app still works — approving a booking just skips the
calendar step.

## How booking works

1. Teacher adds `LessonSlot`s for the week via `/admin/`.
2. Students browse open slots at `/slots/` and submit a short request form
   (name/email/phone) — this immediately marks the slot `pending` so no one
   else can request it.
3. Teacher reviews pending `BookingRequest`s in `/admin/` and runs the
   **Approve** or **Reject** bulk action:
   - Approve creates a Google Calendar event, marks the slot `booked`, and
     emails the student.
   - Reject reopens the slot for other students.

## Tests

```bash
python manage.py test
```

## Deploying to Render

1. Push this repo to GitHub (already connected to
   `github.com/alonshac8484/Singing_lessopns`).
2. In Render, create a new **Blueprint** from this repo — it picks up
   `render.yaml`, which provisions a free Postgres database and a web
   service.
3. In the Render dashboard, set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
   and `GOOGLE_REFRESH_TOKEN` (marked `sync: false` in `render.yaml`, so
   Render will prompt for them).
4. Every push to `main` auto-deploys.
