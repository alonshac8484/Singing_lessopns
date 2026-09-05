import datetime
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from .admin import BookingRequestAdmin
from .models import BookingRequest, LessonSlot


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
        self.assertNotContains(list_response, "Request this slot")

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
        self.assertContains(response, "just taken")
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
