from django import forms
from django.forms import ModelForm
from .models import Admin

class AdminForm(ModelForm):
    class Meta:
        model = Admin
        fields = ('username', 'password')
        labels = {
            'username': '',
            'password': ''
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder':'Enter your Username'}),
            'password': forms.PasswordInput(attrs={'placeholder':'Enter your Password'})
        }
