from django import forms
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.utils import timezone
from datetime import datetime
from .models import Employee, Payroll

class EmployeeForm(ModelForm):
    region = forms.CharField(label='region', widget=forms.TextInput(attrs={ 'id': 'region-dropdown', 'list': 'region-list', 'autocomplete': 'off'}))
    province = forms.CharField(label='province', widget=forms.TextInput(attrs={ 'id': 'province-dropdown', 'list': 'province-list', 'autocomplete': 'off'}))
    city = forms.CharField(label='city', widget=forms.TextInput(attrs={ 'id': 'city-dropdown', 'list': 'city-list', 'autocomplete': 'off'}))
    barangay = forms.CharField(label='barangay', widget=forms.TextInput(attrs={ 'id': 'barangay-dropdown', 'list': 'barangay-list', 'autocomplete': 'off'}))
    
    class Meta:
        model = Employee
        fields = ('first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
                   'highest_education', 'work_experience', 'date_of_employment',
                   'employee_status', 'employee_image')
        widgets = {
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'middle_name': forms.TextInput(),
            'gender': forms.Select(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'contact_number': forms.TextInput(),
            'emergency_contact': forms.TextInput(),
            'highest_education': forms.Select(),
            'work_experience': forms.Textarea(),
            'date_of_employment': forms.DateInput(attrs={'type': 'date'}),
            'employee_status': forms.Select(),
            'employee_image': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_image_field()
        
        # Set custom attributes for the date picker
        self.fields['date_of_birth'].widget = forms.DateInput(
            attrs={
                'type': 'date',
                'max': timezone.now().date().isoformat(),  # Set max date to today
                'value': '',  # No default value when form loads
            }
        )

    def _setup_image_field(self):
        """Make image required only for new employees."""
        if not self.instance.pk:
            self.fields['employee_image'].required = True

    def validate_date_format(self, date_str):
        """Helper function to validate 'YYYY-MM-DD' format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")
        
    def clean_date_of_birth(self):
        """Validate that employee is at least 18 years old"""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            # Calculate age without using dateutil
            today = timezone.now().date()
            age = today.year - date_of_birth.year
            
            # Adjust age if birthday hasn't occurred yet this year
            if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                age -= 1
            
            if age < 18:
                raise forms.ValidationError("Employee must be at least 18 years old.")
        
        return date_of_birth

    def clean_date_of_employment(self):
        date_of_employment = self.cleaned_data.get('date_of_employment')
        if date_of_employment:
            self.validate_date_format(str(date_of_employment))
        return date_of_employment

    def validate_contact_number(self, contact_number):
        """Helper function to validate 11-digit numbers."""
        if not contact_number.isdigit() or len(contact_number) != 11:
            raise forms.ValidationError("Invalid contact number. Must be exactly 11 digits.")
        return contact_number

    def clean_contact_number(self):
        return self.validate_contact_number(self.cleaned_data.get('contact_number', ''))

    def clean_emergency_contact(self):
        return self.validate_contact_number(self.cleaned_data.get('emergency_contact', ''))
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Basic location validation if needed
        # This is simplified since we're just saving strings now
        return cleaned_data
    
class PayrollForm(ModelForm):
    rate = forms.FloatField(widget=forms.NumberInput())
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = Payroll
        fields = ('rate', 'payment_date', 'payroll_status')
        widget = {
            'payroll_status': forms.Select(),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['rate', 'payment_date', 'payroll_status']

        # Check if all required fields are filled
        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
        
    def validate_date_format(self, date_str):
        """Helper function to validate 'YYYY-MM-DD' format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        if payment_date:
            self.validate_date_format(str(payment_date))
        return payment_date    
    
class AdminEditProfileForm(UserChangeForm):
    username = forms.CharField(max_length=100, widget=forms.TextInput())
    first_name = forms.CharField(max_length=100, widget=forms.TextInput())
    last_name = forms.CharField(max_length=100, widget=forms.TextInput())
    email = forms.EmailField(widget=forms.EmailInput())
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password')

class PasswordChangingForm(PasswordChangeForm):
    old_password = forms.CharField(max_length=100, widget=forms.PasswordInput())
    new_password1 = forms.CharField(max_length=100, widget=forms.PasswordInput())
    new_password2 = forms.CharField(max_length=100, widget=forms.PasswordInput())
    
    class Meta:
        model = User
        fields = ('old_password', 'new_password1', 'new_password2', )