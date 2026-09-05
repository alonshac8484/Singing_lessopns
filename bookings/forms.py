from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import BookingRequest


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label=_("Email"))

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        labels = {
            "username": _("Username"),
        }


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
