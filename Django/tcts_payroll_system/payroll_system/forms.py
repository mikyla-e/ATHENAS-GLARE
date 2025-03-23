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
            'date_of_birth': forms.DateInput(),
            'contact_number': forms.TextInput(),
            'emergency_contact': forms.TextInput(),
            'region': forms.Select(attrs={'id': 'region'}),
            'province': forms.Select(attrs={'id': 'province'}),
            'municipality': forms.Select(attrs={'id': 'municipality'}),
            'barangay': forms.Select(attrs={'id': 'barangay'}),
            'highest_education': forms.Select(),
            'work_experience': forms.Textarea(),
            'date_of_employment': forms.DateInput(),
            'employee_status': forms.Select(),
            'employee_image': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make image required only for new employees (not for updates)
        if not self.instance.pk:
            self.fields['employee_image'].required = True
        
        # Always load all regions
        self.fields['region'].queryset = Region.objects.all()
        
        # Get form data if it exists
        form_data = kwargs.get('data')
        
        # For initial load or if there's an instance
        if self.instance.pk or not form_data:
            # If we have an instance with saved data
            if self.instance.pk:
                # Set querysets based on current selections
                if self.instance.region:
                    self.fields['province'].queryset = Province.objects.filter(region=self.instance.region)
                
                if self.instance.province:
                    self.fields['municipality'].queryset = Municipality.objects.filter(
                        province=self.instance.province
                    )
                
                if self.instance.municipality:
                    self.fields['barangay'].queryset = Barangay.objects.filter(
                        municipality=self.instance.municipality
                    )
            else:
                # For initial form load with no data
                self.fields['province'].queryset = Province.objects.none()
                self.fields['municipality'].queryset = Municipality.objects.none()
                self.fields['barangay'].queryset = Barangay.objects.none()
        
        # For form submissions (POST) - populate dropdowns based on form data
        elif form_data:
            # If region is selected, filter provinces
            region_id = form_data.get('region')
            if region_id:
                self.fields['province'].queryset = Province.objects.filter(region_id=region_id)
            else:
                self.fields['province'].queryset = Province.objects.none()
            
            # If province is selected, filter municipalities
            province_id = form_data.get('province')
            if province_id:
                self.fields['municipality'].queryset = Municipality.objects.filter(province_id=province_id)
            else:
                self.fields['municipality'].queryset = Municipality.objects.none()
            
            # If municipality is selected, filter barangays
            municipality_id = form_data.get('municipality')
            if municipality_id:
                self.fields['barangay'].queryset = Barangay.objects.filter(municipality_id=municipality_id)
            else:
                self.fields['barangay'].queryset = Barangay.objects.none()

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