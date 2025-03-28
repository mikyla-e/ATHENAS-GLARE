import datetime
from django import forms
from django.forms import ModelForm
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
    region = forms.CharField(
        label='Region', 
        widget=forms.TextInput(attrs={'list': 'region-list', 'autocomplete': 'off'}),
        required=True
    )
    province = forms.CharField(
        label='Province', 
        widget=forms.TextInput(attrs={'list': 'province-list', 'autocomplete': 'off'}),
        required=True
    )
    municipality = forms.CharField(
        label='Municipality', 
        widget=forms.TextInput(attrs={'list': 'municipality-list', 'autocomplete': 'off'}),
        required=True
    )
    barangay = forms.CharField(
        label='Barangay', 
        widget=forms.TextInput(attrs={'list': 'barangay-list', 'autocomplete': 'off'}),
        required=True
    )
    class Meta:
        model = Employee
        fields = ('first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
                   'region', 'province', 'municipality', 'barangay', 'highest_education', 'work_experience', 'date_of_employment',
                   'employee_status', 'employee_image')
        widgets = {
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'middle_name': forms.TextInput(),
            'gender': forms.Select(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'contact_number': forms.TextInput(),
            'emergency_contact': forms.TextInput(),
            'region': forms.TextInput(),
            'province': forms.TextInput(),
            'municipality': forms.TextInput(),
            'barangay': forms.TextInput(),
            'highest_education': forms.Select(),
            'work_experience': forms.Textarea(),
            'date_of_employment': forms.DateInput(attrs={'type': 'date'}),
            'employee_status': forms.Select(),
            'employee_image': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make image required only for new employees (not for updates)
        if not self.instance.pk:
            self.fields['employee_image'].required = True
        
        # Populate datalist options dynamically
        self.fields['region'].initial = self.instance.region.name if self.instance.region else ''
        
        # Prepare choices
        self.region_choices = list(Region.objects.values_list('name', flat=True))
        self.province_choices = []
        self.municipality_choices = []
        self.barangay_choices = []

        # If editing an existing employee, populate cascading choices
        if self.instance.pk:
            if self.instance.region:
                self.province_choices = list(Province.objects.filter(
                    region=self.instance.region
                ).values_list('name', flat=True))
                
                # Set initial province input
                self.fields['province'].initial = self.instance.province.name if self.instance.province else ''
            
            if self.instance.province:
                self.municipality_choices = list(Municipality.objects.filter(
                    province=self.instance.province
                ).values_list('name', flat=True))
                
                # Set initial municipality input
                self.fields['municipality'].initial = self.instance.municipality.name if self.instance.municipality else ''
            
            if self.instance.municipality:
                self.barangay_choices = list(Barangay.objects.filter(
                    municipality=self.instance.municipality
                ).values_list('name', flat=True))
                
                # Set initial barangay input
                self.fields['barangay'].initial = self.instance.barangay.name if self.instance.barangay else ''

    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 
                           'emergency_contact', 'region', 'province', 'municipality', 'barangay',
                           'highest_education', 'work_experience', 'date_of_employment', 
                           'employee_status']

        # Check if all required fields are filled
        missing_fields = [field for field in required_fields if not cleaned_data.get(field)]
        if missing_fields:
            raise forms.ValidationError(f"The following fields must be filled: {', '.join(missing_fields)}")

        return cleaned_data

    def validate_date_format(self, date_str):
        """Helper function to validate 'YYYY-MM-DD' format."""
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            self.validate_date_format(str(date_of_birth))
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
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        if payment_date:
            self.validate_date_format(str(payment_date))
        return payment_date    