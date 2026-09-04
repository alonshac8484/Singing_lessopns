import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import BookingRequestForm
from .models import BookingRequest, LessonSlot


def slot_list(request):
    slots = LessonSlot.objects.filter(status=LessonSlot.Status.OPEN)
    weeks = {}
    for slot in slots:
        week_start = slot.date - datetime.timedelta(days=slot.date.weekday())
        weeks.setdefault(week_start, []).append(slot)
    return render(request, "bookings/slot_list.html", {"weeks": sorted(weeks.items())})


def book_slot(request, slot_id):
    slot = get_object_or_404(LessonSlot, id=slot_id)

    if request.method == "POST":
        form = BookingRequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                locked_slot = LessonSlot.objects.select_for_update().get(id=slot.id)
                if locked_slot.status != LessonSlot.Status.OPEN:
                    form.add_error(None, _("Sorry, this slot was just taken. Please pick another."))
                else:
                    booking = form.save(commit=False)
                    booking.slot = locked_slot
                    booking.save()
                    locked_slot.status = LessonSlot.Status.PENDING
                    locked_slot.save()
                    return redirect(reverse("bookings:confirmation", args=[booking.id]))
        return render(request, "bookings/book_slot.html", {"slot": slot, "form": form})

    if slot.status != LessonSlot.Status.OPEN:
        return redirect(reverse("bookings:slot_list"))

    form = BookingRequestForm()
    return render(request, "bookings/book_slot.html", {"slot": slot, "form": form})


def confirmation(request, booking_id):
    booking = get_object_or_404(BookingRequest, id=booking_id)
    return render(request, "bookings/confirmation.html", {"booking": booking})
