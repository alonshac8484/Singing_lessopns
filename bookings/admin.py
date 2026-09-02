from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings

from .models import BookingRequest, LessonSlot
from .services.google_calendar import create_lesson_event, delete_lesson_event


@admin.register(LessonSlot)
class LessonSlotAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "end_time", "status")
    list_filter = ("status", "date")
    ordering = ("date", "start_time")


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ("student_name", "slot", "status", "requested_at")
    list_filter = ("status",)
    actions = ["approve_requests", "reject_requests"]

    def approve_requests(self, request, queryset):
        approved = 0
        for booking in queryset.select_related("slot"):
            if booking.status != BookingRequest.Status.PENDING:
                continue
            event_id = create_lesson_event(booking.slot, booking)
            booking.status = BookingRequest.Status.APPROVED
            booking.google_event_id = event_id or ""
            booking.save()
            booking.slot.status = LessonSlot.Status.BOOKED
            booking.slot.save()
            send_mail(
                subject="Your voice lesson is confirmed",
                message=(
                    f"Hi {booking.student_name},\n\n"
                    f"Your lesson on {booking.slot.date} at {booking.slot.start_time:%H:%M} "
                    "has been approved. See you then!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.student_email],
                fail_silently=True,
            )
            approved += 1
        self.message_user(request, f"Approved {approved} booking(s).")

    approve_requests.short_description = "Approve selected requests (adds to calendar)"

    def reject_requests(self, request, queryset):
        rejected = 0
        for booking in queryset.select_related("slot"):
            if booking.status != BookingRequest.Status.PENDING:
                continue
            if booking.google_event_id:
                delete_lesson_event(booking.google_event_id)
            booking.status = BookingRequest.Status.REJECTED
            booking.save()
            booking.slot.status = LessonSlot.Status.OPEN
            booking.slot.save()
            rejected += 1
        self.message_user(request, f"Rejected {rejected} booking(s).")

    reject_requests.short_description = "Reject selected requests (reopens the slot)"
