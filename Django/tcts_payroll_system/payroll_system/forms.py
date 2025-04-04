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
        """Initialize location fields and their choices."""
        if self.instance.pk:
            self._set_initial_location_values()
        
        # Populate region choices from the library model
        self.region_choices = Region.objects.filter(is_active=True).values_list('name', flat=True)
        self.province_choices = []
        self.municipality_choices = []
        self.barangay_choices = []

        if self.instance.pk and self.instance.region:
            self._populate_cascading_choices()

    def _set_initial_location_values(self):
        """Set initial values for location fields when editing."""
        if self.instance.region:
            self.fields['region_name'].initial = self.instance.region.name
        if self.instance.province:
            self.fields['province_name'].initial = self.instance.province.name
        if self.instance.municipality:
            self.fields['municipality_name'].initial = self.instance.municipality.name
        if self.instance.barangay:
            self.fields['barangay_name'].initial = self.instance.barangay.name

    # def _setup_date_fields(self):
    #     """Set up date fields with appropriate defaults and constraints."""
    #     # Calculate date 18 years ago for date_of_birth field
    #     eighteen_years_ago = datetime.datetime.now().date() - datetime.timedelta(days=365*18)
        
    #     # Set max attribute to today (can't be born in the future)
    #     today = datetime.datetime.now().date().isoformat()
        
    #     # Update the date_of_birth widget attributes
    #     self.fields['date_of_birth'].widget.attrs.update({
    #         'max': today,
    #         'value': eighteen_years_ago.isoformat()  # Default to 18 years ago
    #     })

    def _populate_cascading_choices(self):
        """Populate cascading choices for existing instances."""
        if self.instance.region:
            self.province_choices = Province.objects.filter(
                region=self.instance.region, 
                is_active=True
            ).values_list('name', flat=True)
            
        if self.instance.province:
            self.municipality_choices = Municipality.objects.filter(
                province=self.instance.province, 
                is_active=True
            ).values_list('name', flat=True)
            
        if self.instance.municipality:
            self.barangay_choices = Barangay.objects.filter(
                municipality=self.instance.municipality, 
                is_active=True
            ).values_list('name', flat=True)

    def _setup_image_field(self):
        """Make image required only for new employees."""
        if not self.instance.pk:
            self.fields['employee_image'].required = True

    def validate_date_format(self, date_str):
        """Helper function to validate 'YYYY-MM-DD' format."""
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
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
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get location names from form fields
        region_name = cleaned_data.get('region_name')
        province_name = cleaned_data.get('province_name')
        municipality_name = cleaned_data.get('municipality_name')
        barangay_name = cleaned_data.get('barangay_name')
        
        # Validate locations exist but don't store references
        if region_name:
            region = Region.objects.filter(name__iexact=region_name, is_active=True).first()
            if not region:
                self.add_error('region_name', f'Region "{region_name}" not found')
        
        if province_name and region_name:
            region = Region.objects.filter(name__iexact=region_name, is_active=True).first()
            if region:
                province = Province.objects.filter(
                    name__iexact=province_name, 
                    region=region,
                    is_active=True
                ).first()
                if not province:
                    self.add_error('province_name', f'Province "{province_name}" not found in {region_name}')
            
        if municipality_name and province_name and region_name:
            region = Region.objects.filter(name__iexact=region_name, is_active=True).first()
            if region:
                province = Province.objects.filter(
                    name__iexact=province_name, 
                    region=region,
                    is_active=True
                ).first()
                if province:
                    municipality = Municipality.objects.filter(
                        name__iexact=municipality_name,
                        province=province,
                        is_active=True
                    ).first()
                    if not municipality:
                        self.add_error('municipality_name', f'Municipality "{municipality_name}" not found in {province_name}')
            
        if barangay_name and municipality_name and province_name and region_name:
            region = Region.objects.filter(name__iexact=region_name, is_active=True).first()
            if region:
                province = Province.objects.filter(
                    name__iexact=province_name, 
                    region=region,
                    is_active=True
                ).first()
                if province:
                    municipality = Municipality.objects.filter(
                        name__iexact=municipality_name,
                        province=province,
                        is_active=True
                    ).first()
                    if municipality:
                        barangay = Barangay.objects.filter(
                            name__iexact=barangay_name,
                            municipality=municipality,
                            is_active=True
                        ).first()
                        if not barangay:
                            self.add_error('barangay_name', f'Barangay "{barangay_name}" not found in {municipality_name}')
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # No need to set foreign key references
        # Just let the form's normal save mechanism handle the CharFields
        
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
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        if payment_date:
            self.validate_date_format(str(payment_date))
        return payment_date    