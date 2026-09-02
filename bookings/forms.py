from django import forms

from .models import BookingRequest


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ["student_name", "student_email", "student_phone", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }
