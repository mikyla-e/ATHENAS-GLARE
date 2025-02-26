from django import forms
from django.forms import ModelForm
from .models import Admin, Employee

class AdminForm(ModelForm):
    class Meta:
        model = Admin
        fields = ('username', 'password')
        widgets = {
            'username': forms.TextInput(),
            'password': forms.PasswordInput()
        }

class EmployeeForm(ModelForm):
    class Meta:
        model = Employee
        fields = ('first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact', 'barangay', 'postal_address', 'highest_education', 'work_experience', 'date_of_employment', 'employee_status')
        widgets = {
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'gender': forms.Select(),
            'date_of_birth': forms.TextInput(),
            'contact_number': forms.TextInput(),
            'emergency_contact': forms.TextInput(),
            'barangay': forms.TextInput(),
            'postal_address': forms.TextInput(),
            'highest_education': forms.Select(),
            'work_experience': forms.Textarea(),
            'date_of_employment': forms.DateInput(),
            'employee_status': forms.Select(),
        }
