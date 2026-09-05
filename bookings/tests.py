import datetime
import re
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, TestCase

from .admin import BookingRequestAdmin
from .models import BookingRequest, LessonSlot, Profile


def make_admin_request():
    request = RequestFactory().get("/admin/bookings/bookingrequest/")
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def make_slot():
    return LessonSlot.objects.create(
        date=datetime.date.today() + datetime.timedelta(days=1),
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
    )


def make_user(username="alice"):
    return User.objects.create_user(username=username, password="testpass123", email=f"{username}@example.com")


class BookingFlowTests(TestCase):
    def test_requesting_a_slot_marks_it_pending_and_hides_it(self):
        slot = make_slot()
        self.client.force_login(make_user())
        response = self.client.post(
            f"/slots/{slot.id}/book/",
            {
                "student_name": "Alice",
                "student_email": "alice@example.com",
                "student_phone": "",
                "message": "",
            },
        )
        self.assertEqual(response.status_code, 302)

        slot.refresh_from_db()
        self.assertEqual(slot.status, LessonSlot.Status.PENDING)
        self.assertEqual(BookingRequest.objects.count(), 1)
        self.assertEqual(BookingRequest.objects.get().user.username, "alice")

        list_response = self.client.get("/slots/")
        self.assertNotContains(list_response, f"/slots/{slot.id}/book/")

    def test_double_booking_is_prevented(self):
        slot = make_slot()
        slot.status = LessonSlot.Status.PENDING
        slot.save()
        self.client.force_login(make_user("bob"))

        response = self.client.post(
            f"/slots/{slot.id}/book/",
            {
                "student_name": "Bob",
                "student_email": "bob@example.com",
                "student_phone": "",
                "message": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertEqual(BookingRequest.objects.count(), 0)

    def test_anonymous_booking_redirects_to_login(self):
        slot = make_slot()
        response = self.client.post(
            f"/slots/{slot.id}/book/",
            {
                "student_name": "Eve",
                "student_email": "eve@example.com",
                "student_phone": "",
                "message": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

        slot.refresh_from_db()
        self.assertEqual(slot.status, LessonSlot.Status.OPEN)
        self.assertEqual(BookingRequest.objects.count(), 0)


class AdminApprovalTests(TestCase):
    def setUp(self):
        self.slot = make_slot()
        self.slot.status = LessonSlot.Status.PENDING
        self.slot.save()
        self.booking = BookingRequest.objects.create(
            slot=self.slot,
            student_name="Alice",
            student_email="alice@example.com",
        )
        self.admin = BookingRequestAdmin(BookingRequest, AdminSite())

    @patch("bookings.admin.create_lesson_event", return_value="fake-event-id")
    def test_approve_creates_calendar_event_and_books_slot(self, mock_create_event):
        self.admin.approve_requests(
            request=make_admin_request(),
            queryset=BookingRequest.objects.filter(id=self.booking.id),
        )

        self.booking.refresh_from_db()
        self.slot.refresh_from_db()
        mock_create_event.assert_called_once()
        self.assertEqual(self.booking.status, BookingRequest.Status.APPROVED)
        self.assertEqual(self.booking.google_event_id, "fake-event-id")
        self.assertEqual(self.slot.status, LessonSlot.Status.BOOKED)

    def test_reject_reopens_slot(self):
        self.admin.reject_requests(
            request=make_admin_request(),
            queryset=BookingRequest.objects.filter(id=self.booking.id),
        )

        self.booking.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(self.booking.status, BookingRequest.Status.REJECTED)
        self.assertEqual(self.slot.status, LessonSlot.Status.OPEN)


class AccountPageTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/slots/account/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_updating_details_creates_profile_and_saves_fields(self):
        self.client.force_login(make_user("carol"))
        self.assertFalse(Profile.objects.filter(user__username="carol").exists())

        response = self.client.post(
            "/slots/account/",
            {"phone": "555-1234", "date_of_birth": "1990-05-15"},
        )

        self.assertEqual(response.status_code, 302)
        profile = Profile.objects.get(user__username="carol")
        self.assertEqual(profile.phone, "555-1234")
        self.assertEqual(profile.date_of_birth, datetime.date(1990, 5, 15))

    def test_shows_only_the_logged_in_users_bookings(self):
        mine = make_user("dave")
        someone_else = make_user("erin")
        my_slot = make_slot()
        BookingRequest.objects.create(
            slot=my_slot, user=mine, student_name="Dave", student_email="dave@example.com"
        )
        other_slot = LessonSlot.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=2),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
        )
        BookingRequest.objects.create(
            slot=other_slot, user=someone_else, student_name="Erin", student_email="erin@example.com"
        )

        self.client.force_login(mine)
        response = self.client.get("/slots/account/")

        self.assertContains(response, "10:00")  # my_slot's start time
        self.assertNotContains(response, "09:00")  # other_slot's start time


class CsrfBehindProxyTests(TestCase):
    """
    Render terminates TLS at its own proxy and forwards requests to this app
    over plain HTTP. Without SECURE_PROXY_SSL_HEADER, request.is_secure()
    comes out False, and Django's CSRF middleware then builds the "expected
    origin" for its Origin-header check as http://... while real browsers
    send Origin: https://..., rejecting every submission with a 403 whenever
    the browser includes an Origin header. Client(enforce_csrf_checks=True)
    exercises the real CSRF middleware instead of the test client's default
    bypass, and HTTP_X_FORWARDED_PROTO simulates what Render's proxy sends.
    """

    def test_signup_succeeds_with_https_origin_behind_proxy(self):
        # Deliberately NOT using Client(secure=True): that fakes a secure
        # connection at the WSGI level and would make request.is_secure()
        # True regardless of SECURE_PROXY_SSL_HEADER, defeating the point of
        # this test. The connection here is nominally plain HTTP, exactly
        # like what Render forwards internally, with only the
        # X-Forwarded-Proto header hinting that it was HTTPS externally.
        # A real browser always sends a Host header, which Render's proxy
        # passes through unchanged -- Django's get_host() uses that header
        # directly rather than reconstructing one from SERVER_NAME/PORT, so
        # the port confusion that would otherwise happen here doesn't occur
        # in production. Setting HTTP_HOST explicitly (the test client
        # doesn't by default) reproduces that real condition.
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(
            "/slots/signup/", HTTP_X_FORWARDED_PROTO="https", HTTP_HOST="testserver"
        )
        csrf_token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', get_response.content.decode()
        ).group(1)

        response = client.post(
            "/slots/signup/",
            {
                "username": "proxytest",
                "email": "proxytest@example.com",
                "password1": "correcthorsebattery",
                "password2": "correcthorsebattery",
                "csrfmiddlewaretoken": csrf_token,
            },
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_HOST="testserver",
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="proxytest").exists())
