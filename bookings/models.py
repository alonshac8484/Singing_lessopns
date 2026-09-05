from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LessonSlot(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending approval"
        BOOKED = "booked", "Booked"

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.date} {self.start_time:%H:%M}-{self.end_time:%H:%M} ({self.status})"


class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE, related_name="requests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()
    student_phone = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    google_event_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.student_name} - {self.slot} ({self.status})"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.user}"
