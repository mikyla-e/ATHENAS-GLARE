from django import forms
from django.forms import ModelForm
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import Admin, Employee, Payroll
from ph_geography.models import Region, Province, Municipality, Barangay

class AdminForm(ModelForm):
    class Meta:
        model = Admin
        fields = ('username', 'password')
        widgets = {
            'username': forms.TextInput(),
            'password': forms.PasswordInput()
        }
        
class EmployeeForm(ModelForm):
    region_name = forms.CharField(
        label='Region',
        widget=forms.TextInput(attrs={
            'list': 'region-list',
            'autocomplete': 'off',
            'class': 'location-field'
        }),
        required=True
    )
    province_name = forms.CharField(
        label='Province',
        widget=forms.TextInput(attrs={
            'list': 'province-list', 
            'autocomplete': 'off',
            'class': 'location-field'
        }),
        required=True
    )
    municipality_name = forms.CharField(
        label='Municipality',
        widget=forms.TextInput(attrs={
            'list': 'municipality-list',
            'autocomplete': 'off',
            'class': 'location-field'
        }),
        required=True
    )
    barangay_name = forms.CharField(
        label='Barangay',
        widget=forms.TextInput(attrs={
            'list': 'barangay-list',
            'autocomplete': 'off',
            'class': 'location-field'
        }),
        required=True
    )
    
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
        self._setup_location_fields()
        self._setup_image_field()
        
        # Set custom attributes for the date picker
        self.fields['date_of_birth'].widget = forms.DateInput(
            attrs={
                'type': 'date',
                'max': timezone.now().date().isoformat(),  # Set max date to today
                'value': '',  # No default value when form loads
            }
        )

    def _setup_location_fields(self):
        """Initialize location fields and their initial values."""
        if self.instance.pk:
            # Set initial values from model instance
            self.fields['region_name'].initial = self.instance.region
            self.fields['province_name'].initial = self.instance.province
            self.fields['municipality_name'].initial = self.instance.municipality
            self.fields['barangay_name'].initial = self.instance.barangay

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

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Copy the location name values to the model instance
        instance.region = self.cleaned_data.get('region_name', '')
        instance.province = self.cleaned_data.get('province_name', '')
        instance.municipality = self.cleaned_data.get('municipality_name', '')
        instance.barangay = self.cleaned_data.get('barangay_name', '')
        
        if commit:
            instance.save()
        return instance
    
class PayrollForm(ModelForm):
    class Meta:
        model = Payroll
        fields = ('rate', 'payment_date', 'payroll_status')
        widgets = {
            'rate': forms.NumberInput(),
            'payment_date': forms.DateInput(),
            'payroll_status': forms.Select()
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