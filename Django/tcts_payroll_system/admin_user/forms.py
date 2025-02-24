from django import forms

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class AdminLogin(forms.Form):
    admin_name = forms.CharField(label="Admin Name", max_length=100)