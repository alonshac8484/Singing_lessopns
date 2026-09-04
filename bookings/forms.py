from django import forms
from django.utils.translation import gettext_lazy as _

from .models import BookingRequest


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ["student_name", "student_email", "student_phone", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "student_name": _("Student name"),
            "student_email": _("Student email"),
            "student_phone": _("Student phone"),
            "message": _("Message"),
        }
