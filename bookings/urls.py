from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.slot_list, name="slot_list"),
    path("<int:slot_id>/book/", views.book_slot, name="book_slot"),
    path("confirmation/<int:booking_id>/", views.confirmation, name="confirmation"),
]
