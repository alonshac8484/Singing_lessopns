import datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import BookingRequestForm, SignUpForm
from .models import BookingRequest, LessonSlot


def slot_list(request):
    slots = LessonSlot.objects.filter(status=LessonSlot.Status.OPEN)
    weeks = {}
    for slot in slots:
        week_start = slot.date - datetime.timedelta(days=slot.date.weekday())
        weeks.setdefault(week_start, []).append(slot)
    return render(request, "bookings/slot_list.html", {"weeks": sorted(weeks.items())})


@login_required
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
                    booking.user = request.user
                    booking.save()
                    locked_slot.status = LessonSlot.Status.PENDING
                    locked_slot.save()
                    return redirect(reverse("bookings:confirmation", args=[booking.id]))
        return render(request, "bookings/book_slot.html", {"slot": slot, "form": form})

    if slot.status != LessonSlot.Status.OPEN:
        return redirect(reverse("bookings:slot_list"))

    initial = {
        "student_name": request.user.get_full_name() or request.user.username,
        "student_email": request.user.email,
    }
    form = BookingRequestForm(initial=initial)
    return render(request, "bookings/book_slot.html", {"slot": slot, "form": form})


def confirmation(request, booking_id):
    booking = get_object_or_404(BookingRequest, id=booking_id)
    return render(request, "bookings/confirmation.html", {"booking": booking})


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Account created! Welcome, %(name)s.") % {"name": user.username})
            next_url = request.POST.get("next") or request.GET.get("next") or reverse("bookings:slot_list")
            return redirect(next_url)
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})
