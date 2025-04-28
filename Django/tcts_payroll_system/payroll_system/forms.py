import re
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from .models import Employee, Payroll, Region, Province, City, Barangay, Service, Customer, Vehicle

class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput())
    middle_name = forms.CharField(widget=forms.TextInput(), required=False)
    last_name = forms.CharField(widget=forms.TextInput())
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    contact_number = forms.CharField(widget=forms.TextInput(attrs={'type': 'tel'}))
    emergency_contact = forms.CharField(widget=forms.TextInput(attrs={'type': 'tel'}))
    region = forms.CharField(label='region', widget=forms.TextInput(attrs={'id': 'region-dropdown', 'list': 'region-list', 
                             'autocomplete': 'off'}))
    province = forms.CharField(label='province', widget=forms.TextInput(attrs={'id': 'province-dropdown', 'list': 'province-list',
                               'autocomplete': 'off'}))
    city = forms.CharField(label='city', widget=forms.TextInput(attrs={'id': 'city-dropdown', 'list': 'city-list', 
                           'autocomplete': 'off'}))
    barangay = forms.CharField(label='barangay', widget=forms.TextInput(attrs={'id': 'barangay-dropdown', 'list': 'barangay-list', 
                               'autocomplete': 'off'}))
    work_experience = forms.CharField(widget=forms.Textarea(), required=False)
    date_of_employment = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=timezone.now)
    
    class Meta:
        model = Employee
        fields = ('first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
                  'highest_education', 'work_experience', 'date_of_employment', 'employee_status')
        widgets = {
            'gender': forms.Select(),
            'highest_education': forms.Select(),
            'employee_status': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set custom attributes for the date picker
        self.fields['date_of_birth'].widget = forms.DateInput(
            attrs={
                'type': 'date',
                'max': timezone.now().date().isoformat(),  # Set max date to today
                'value': '',  # No default value when form loads
            }
        )

    #Helper function to validate 11-digit numbers.
    def validate_contact_number(self, contact_number):
        
        if not contact_number.isdigit() or len(contact_number) != 11:
            raise forms.ValidationError("Contact number must be exactly 11 digits.")
        return contact_number

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in first_name):
            raise forms.ValidationError("First name should contain only letters, spaces, or hyphens.")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in last_name):
            raise forms.ValidationError("Last name should contain only letters, spaces, or hyphens.")
        return last_name.strip()

    def clean_middle_name(self):
        middle_name = self.cleaned_data.get('middle_name', '')
        if middle_name and not all(char.isalpha() or char.isspace() or char == '-' for char in middle_name):
            raise forms.ValidationError("Middle name should contain only letters, spaces, or hyphens.")
        return middle_name.strip() if middle_name else middle_name

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            # Validate that employee is at least 18 years old
            today = timezone.now().date()
            age = today.year - date_of_birth.year
            
            # Adjust age if birthday hasn't occurred yet this year
            if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                age -= 1
            
            if age < 18:
                raise forms.ValidationError("Employee must be at least 18 years old.")
            
            # Additional validation: date can't be in the future
            if date_of_birth > today:
                raise forms.ValidationError("Date of birth cannot be in the future.")
        
        return date_of_birth

    def clean_date_of_employment(self):
        date_of_employment = self.cleaned_data.get('date_of_employment')
        date_of_birth = self.cleaned_data.get('date_of_birth')
        
        # Date of employment shouldn't be in the future
        if date_of_employment and date_of_employment > timezone.now().date():
            raise forms.ValidationError("Date of employment cannot be in the future.")
            
        # Date of employment shouldn't be before date of birth
        if date_of_employment and date_of_birth and date_of_employment < date_of_birth:
            raise forms.ValidationError("Date of employment cannot be before date of birth.")
            
        # Employee should be at least 18 years old at date of employment
        if date_of_employment and date_of_birth:
            age_at_employment = date_of_employment.year - date_of_birth.year
            if (date_of_employment.month, date_of_employment.day) < (date_of_birth.month, date_of_birth.day):
                age_at_employment -= 1
                
            if age_at_employment < 18:
                raise forms.ValidationError("Employee must be at least 18 years old at date of employment.")
                
        return date_of_employment

    def clean_contact_number(self):
        return self.validate_contact_number(self.cleaned_data.get('contact_number', ''))

    def clean_emergency_contact(self):
        emergency_contact = self.cleaned_data.get('emergency_contact', '')
        contact_number = self.cleaned_data.get('contact_number', '')
        
        # Validate format
        emergency_contact = self.validate_contact_number(emergency_contact)
        
        # Emergency contact shouldn't be the same as contact number
        if emergency_contact == contact_number:
            raise forms.ValidationError("Emergency contact cannot be the same as personal contact number.")
            
        return emergency_contact
    
    def clean_region(self):
        region_name = self.cleaned_data.get('region')
        if not region_name:
            raise forms.ValidationError("Region is required.")
            
        region = Region.objects.filter(regDesc=region_name).first()
        if not region:
            raise forms.ValidationError("Please select a valid region.")
            
        return region_name
    
    def clean_province(self):
        province_name = self.cleaned_data.get('province')
        region_name = self.cleaned_data.get('region')
        
        if not province_name:
            raise forms.ValidationError("Province is required.")
            
        if region_name:
            region = Region.objects.filter(regDesc=region_name).first()
            if region:
                province = Province.objects.filter(
                    provDesc=province_name,
                    regCode=region.regCode
                ).first()
                
                if not province:
                    raise forms.ValidationError("Province must belong to the selected region.")
        
        return province_name
    
    def clean_city(self):
        city_name = self.cleaned_data.get('city')
        province_name = self.cleaned_data.get('province')
        
        if not city_name:
            raise forms.ValidationError("City is required.")
            
        if province_name:
            province = Province.objects.filter(provDesc=province_name).first()
            if province:
                city = City.objects.filter(
                    citymunDesc=city_name,
                    provCode=province.provCode
                ).first()
                
                if not city:
                    raise forms.ValidationError("City must belong to the selected province.")
        
        return city_name
    
    def clean_barangay(self):
        barangay_name = self.cleaned_data.get('barangay')
        city_name = self.cleaned_data.get('city')
        
        if not barangay_name:
            raise forms.ValidationError("Barangay is required.")
            
        if city_name:
            city = City.objects.filter(citymunDesc=city_name).first()
            if city:
                barangay = Barangay.objects.filter(
                    brgyDesc=barangay_name,
                    citymunCode=city.citymunCode
                ).first()
                
                if not barangay:
                    raise forms.ValidationError("Barangay must belong to the selected city.")
        
        return barangay_name
    
    def clean_work_experience(self):
        work_experience = self.cleaned_data.get('work_experience', '')
        if work_experience and len(work_experience) > 1000:
            raise forms.ValidationError("Work experience description is too long (max 1000 characters).")
        return work_experience
    
    def clean(self):
        cleaned_data = super().clean()

        required_fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
            'highest_education', 'date_of_employment', 'employee_status', 'region', 'province', 'city', 'barangay'
        ]
        
        # Check for duplicate employees based on name and birth date
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        date_of_birth = cleaned_data.get('date_of_birth')

        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
        
        if first_name and last_name and date_of_birth:
            # Define the query to find potential duplicates
            existing_query = Employee.objects.filter(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth
            )
            
            # Exclude the current instance when updating
            if self.instance.pk:
                existing_query = existing_query.exclude(employee_id=self.instance.pk)
            
            # Check if any potential duplicates exist
            if existing_query.exists():
                raise forms.ValidationError(
                    "An employee with this name and birth date already exists. "
                    "If this is a different person, please add a middle name or "
                    "contact HR to resolve this conflict."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        
        # Set location fields based on validated data
        region_name = self.cleaned_data.get('region')
        province_name = self.cleaned_data.get('province')
        city_name = self.cleaned_data.get('city')
        barangay_name = self.cleaned_data.get('barangay')
        
        region = Region.objects.filter(regDesc=region_name).first()
        province = Province.objects.filter(provDesc=province_name, regCode=region.regCode).first()
        city = City.objects.filter(citymunDesc=city_name, provCode=province.provCode).first()
        barangay = Barangay.objects.filter(brgyDesc=barangay_name, citymunCode=city.citymunCode).first()
        
        employee.region = region
        employee.province = province
        employee.city = city
        employee.barangay = barangay
        
        if commit:
            employee.save()
        
        return employee
    
class PayrollForm(ModelForm):
    rate = forms.FloatField(widget=forms.NumberInput())
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = Payroll
        fields = ('rate', 'payment_date', 'payroll_status')
        widget = {
            'payroll_status': forms.Select(),
        }
            
    # Helper function to validate 'YYYY-MM-DD' format.
    def validate_date_format(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise forms.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        if payment_date:
            self.validate_date_format(str(payment_date))
            
            # Check if date is not in the past
            today = datetime.now().date()
            if payment_date < today:
                raise forms.ValidationError("Payment date cannot be in the past.")
                
            # Check if date is not in the too distant future
            if payment_date > today + timedelta(days=365):
                raise forms.ValidationError("Payment date cannot be more than a year in the future.")
                    
        return payment_date 

    def clean(self):
        cleaned_data = super().clean()

        # Get values with defaults
        rate = cleaned_data.get('rate', 0) or 0
        deductions = cleaned_data.get('deductions', 0) or 0
        cash_advance = cleaned_data.get('cash_advance', 0) or 0
        under_time = cleaned_data.get('under_time', 0) or 0
        incentives = cleaned_data.get('incentives', 0) or 0
        
        # Calculate salary
        calculated_salary = rate - deductions - cash_advance - under_time + incentives
        
        # Either validate or auto-set
        if 'salary' in cleaned_data:
            salary = cleaned_data.get('salary', 0) or 0
            if abs(calculated_salary - salary) > 0.01:
                raise ValidationError(_('Salary does not match the calculated amount based on rates and deductions.'))
        else:
            # Auto-set the salary field
            cleaned_data['salary'] = round(calculated_salary, 2)
        
        # Validate non-negative values
        for field_name, value in [
            ('rate', rate), ('deductions', deductions), 
            ('cash_advance', cash_advance), ('under_time', under_time),
            ('incentives', incentives)
        ]:
            if value < 0:
                self.add_error(field_name, _('This value cannot be negative.'))

        required_fields = ['rate', 'payment_date', 'payroll_status']

        # Check if all required fields are filled
        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
        
        return cleaned_data
        
class ServiceForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'w-full outline-none text-lg', 'placeholder': 'Enter Title'}))
    service_image = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'hidden', 'accept': 'image/*', 'onchange': 'loadImage(event)'}))
    
    class Meta:
        model = Service
        fields = ('title', 'service_image')

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            # Check if title contains only valid characters (including spaces)
            if not re.match(r'^[A-Za-z0-9\s\-_.,&()]+$', title):
                raise forms.ValidationError("Title contains invalid characters")
        return title

    def clean_service_image(self):
        image = self.cleaned_data.get('service_image')
        if image:
            # Check file size
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("Image file is too large. Max size is 5MB.")
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif']
            ext = image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file extension. Use jpg, jpeg, png, or gif.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['title', 'service_image']

        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
        
        return cleaned_data

class CustomerForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}))
    middle_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}), required=False)
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}))
    contact_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]', 'type': 'tel'}))
    region = forms.CharField(label='region', widget=forms.TextInput(attrs={'class': 'h-[50px]', 'id': 'region-dropdown', 'list': 'region-list', 
                             'autocomplete': 'off'}))
    province = forms.CharField(label='province', widget=forms.TextInput(attrs={'class': 'h-[50px]', 'id': 'province-dropdown', 'list': 'province-list',
                               'autocomplete': 'off'}))
    city = forms.CharField(label='city', widget=forms.TextInput(attrs={'class': 'h-[50px]', 'id': 'city-dropdown', 'list': 'city-list', 
                           'autocomplete': 'off'}))
    barangay = forms.CharField(label='barangay', widget=forms.TextInput(attrs={'class': 'h-[50px]', 'id': 'barangay-dropdown', 'list': 'barangay-list', 
                               'autocomplete': 'off'}))
    
    class Meta:
        model = Customer
        fields = ('first_name', 'middle_name', 'last_name', 'contact_number')
        
    #Helper function to validate 11-digit numbers.
    def validate_contact_number(self, contact_number):
        if not contact_number.isdigit() or len(contact_number) != 11:
            raise forms.ValidationError("Contact number must be exactly 11 digits.")
        return contact_number

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in first_name):
            raise forms.ValidationError("First name should contain only letters, spaces, or hyphens.")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in last_name):
            raise forms.ValidationError("Last name should contain only letters, spaces, or hyphens.")
        return last_name.strip()

    def clean_middle_name(self):
        middle_name = self.cleaned_data.get('middle_name', '')
        if middle_name and not all(char.isalpha() or char.isspace() or char == '-' for char in middle_name):
            raise forms.ValidationError("Middle name should contain only letters, spaces, or hyphens.")
        return middle_name.strip() if middle_name else middle_name
    
    def clean_contact_number(self):
        return self.validate_contact_number(self.cleaned_data.get('contact_number', ''))
    
    def clean_region(self):
        region_name = self.cleaned_data.get('region')
        if not region_name:
            raise forms.ValidationError("Region is required.")
            
        region = Region.objects.filter(regDesc=region_name).first()
        if not region:
            raise forms.ValidationError("Please select a valid region.")
            
        return region_name
    
    def clean_province(self):
        province_name = self.cleaned_data.get('province')
        region_name = self.cleaned_data.get('region')
        
        if not province_name:
            raise forms.ValidationError("Province is required.")
            
        if region_name:
            region = Region.objects.filter(regDesc=region_name).first()
            if region:
                province = Province.objects.filter(
                    provDesc=province_name,
                    regCode=region.regCode
                ).first()
                
                if not province:
                    raise forms.ValidationError("Province must belong to the selected region.")
        
        return province_name
    
    def clean_city(self):
        city_name = self.cleaned_data.get('city')
        province_name = self.cleaned_data.get('province')
        
        if not city_name:
            raise forms.ValidationError("City is required.")
            
        if province_name:
            province = Province.objects.filter(provDesc=province_name).first()
            if province:
                city = City.objects.filter(
                    citymunDesc=city_name,
                    provCode=province.provCode
                ).first()
                
                if not city:
                    raise forms.ValidationError("City must belong to the selected province.")
        
        return city_name
    
    def clean_barangay(self):
        barangay_name = self.cleaned_data.get('barangay')
        city_name = self.cleaned_data.get('city')
        
        if not barangay_name:
            raise forms.ValidationError("Barangay is required.")
            
        if city_name:
            city = City.objects.filter(citymunDesc=city_name).first()
            if city:
                barangay = Barangay.objects.filter(
                    brgyDesc=barangay_name,
                    citymunCode=city.citymunCode
                ).first()
                
                if not barangay:
                    raise forms.ValidationError("Barangay must belong to the selected city.")
        
        return barangay_name
    
    def clean(self):
        cleaned_data = super().clean()

        required_fields = [
            'first_name', 'last_name', 'contact_number', 'region', 'province', 'city', 'barangay'
        ]
        
        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
        
        return cleaned_data

    def save(self, commit=True):
        customer = super().save(commit=False)
        
        # Set location fields based on validated data
        region_name = self.cleaned_data.get('region')
        province_name = self.cleaned_data.get('province')
        city_name = self.cleaned_data.get('city')
        barangay_name = self.cleaned_data.get('barangay')
        
        region = Region.objects.filter(regDesc=region_name).first()
        province = Province.objects.filter(provDesc=province_name, regCode=region.regCode).first()
        city = City.objects.filter(citymunDesc=city_name, provCode=province.provCode).first()
        barangay = Barangay.objects.filter(brgyDesc=barangay_name, citymunCode=city.citymunCode).first()
        
        customer.region = region
        customer.province = province
        customer.city = city
        customer.barangay = barangay
        
        if commit:
            customer.save()
        
        return customer

class CustomerEditForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-12'}))
    middle_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-12'}), required=False)
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-12'}))
    contact_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-12', 'type': 'tel'}))
    region = forms.CharField(
        label='region', 
        widget=forms.TextInput(attrs={'class': 'h-12', 'id': 'region-dropdown', 'list': 'region-list', 'autocomplete': 'off'})
    )
    province = forms.CharField(
        label='province', 
        widget=forms.TextInput(attrs={'class': 'h-12', 'id': 'province-dropdown', 'list': 'province-list', 'autocomplete': 'off'})
    )
    city = forms.CharField(
        label='city', 
        widget=forms.TextInput(attrs={'class': 'h-12', 'id': 'city-dropdown', 'list': 'city-list', 'autocomplete': 'off'})
    )
    barangay = forms.CharField(
        label='barangay', 
        widget=forms.TextInput(attrs={'class': 'h-12', 'id': 'barangay-dropdown', 'list': 'barangay-list', 'autocomplete': 'off'})
    )
    
    class Meta:
        model = Customer
        fields = ('first_name', 'middle_name', 'last_name', 'contact_number')
    
    # Copy validation methods from CustomerForm...
    def validate_contact_number(self, contact_number):
        if not contact_number.isdigit() or len(contact_number) != 11:
            raise forms.ValidationError("Contact number must be exactly 11 digits.")
        return contact_number

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in first_name):
            raise forms.ValidationError("First name should contain only letters, spaces, or hyphens.")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in last_name):
            raise forms.ValidationError("Last name should contain only letters, spaces, or hyphens.")
        return last_name.strip()

    def clean_middle_name(self):
        middle_name = self.cleaned_data.get('middle_name', '')
        if middle_name and not all(char.isalpha() or char.isspace() or char == '-' for char in middle_name):
            raise forms.ValidationError("Middle name should contain only letters, spaces, or hyphens.")
        return middle_name.strip() if middle_name else middle_name
    
    def clean_contact_number(self):
        return self.validate_contact_number(self.cleaned_data.get('contact_number', ''))
    
    def clean_region(self):
        region_name = self.cleaned_data.get('region')
        if not region_name:
            raise forms.ValidationError("Region is required.")
            
        region = Region.objects.filter(regDesc=region_name).first()
        if not region:
            raise forms.ValidationError("Please select a valid region.")
            
        return region_name
    
    def clean_province(self):
        province_name = self.cleaned_data.get('province')
        region_name = self.cleaned_data.get('region')
        
        if not province_name:
            raise forms.ValidationError("Province is required.")
            
        if region_name:
            region = Region.objects.filter(regDesc=region_name).first()
            if region:
                province = Province.objects.filter(
                    provDesc=province_name,
                    regCode=region.regCode
                ).first()
                
                if not province:
                    raise forms.ValidationError("Province must belong to the selected region.")
        
        return province_name
    
    def clean_city(self):
        city_name = self.cleaned_data.get('city')
        province_name = self.cleaned_data.get('province')
        
        if not city_name:
            raise forms.ValidationError("City is required.")
            
        if province_name:
            province = Province.objects.filter(provDesc=province_name).first()
            if province:
                city = City.objects.filter(
                    citymunDesc=city_name,
                    provCode=province.provCode
                ).first()
                
                if not city:
                    raise forms.ValidationError("City must belong to the selected province.")
        
        return city_name
    
    def clean_barangay(self):
        barangay_name = self.cleaned_data.get('barangay')
        city_name = self.cleaned_data.get('city')
        
        if not barangay_name:
            raise forms.ValidationError("Barangay is required.")
            
        if city_name:
            city = City.objects.filter(citymunDesc=city_name).first()
            if city:
                barangay = Barangay.objects.filter(
                    brgyDesc=barangay_name,
                    citymunCode=city.citymunCode
                ).first()
                
                if not barangay:
                    raise forms.ValidationError("Barangay must belong to the selected city.")
        
        return barangay_name
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for location fields using descriptive names
        instance = kwargs.get('instance')
        if instance:
            if instance.region:
                self.initial['region'] = instance.region.regDesc
            if instance.province:
                self.initial['province'] = instance.province.provDesc
            if instance.city:
                self.initial['city'] = instance.city.citymunDesc
            if instance.barangay:
                self.initial['barangay'] = instance.barangay.brgyDesc
    
    def save(self, commit=True):
        customer = super().save(commit=False)
        
        # Set location fields based on validated data
        region_name = self.cleaned_data.get('region')
        province_name = self.cleaned_data.get('province')
        city_name = self.cleaned_data.get('city')
        barangay_name = self.cleaned_data.get('barangay')
        
        # Get region object
        region = Region.objects.filter(regDesc=region_name).first()
        if region:
            customer.region = region
            
            # Get province object
            province = Province.objects.filter(
                provDesc=province_name,
                regCode=region.regCode
            ).first()
            if province:
                customer.province = province
                
                # Get city object
                city = City.objects.filter(
                    citymunDesc=city_name,
                    provCode=province.provCode
                ).first()
                if city:
                    customer.city = city
                    
                    # Get barangay object
                    barangay = Barangay.objects.filter(
                        brgyDesc=barangay_name,
                        citymunCode=city.citymunCode
                    ).first()
                    if barangay:
                        customer.barangay = barangay
        
        if commit:
            customer.save()
        
        return customer

class VehicleForm(forms.ModelForm):
    vehicle_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}))
    vehicle_color = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}))
    plate_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'h-[50px]'}))
    class Meta:
        model = Vehicle
        fields = ('vehicle_name', 'vehicle_color', 'plate_number')

    def clean_vehicle_name(self):
        vehicle_name = self.cleaned_data.get('vehicle_name')
        if vehicle_name:
            # Check if name contains only valid characters (including spaces)
            if not re.match(r'^[A-Za-z0-9\s\-_.,&()]+$', vehicle_name):
                raise forms.ValidationError("Vehicle name contains invalid characters")
        return vehicle_name

    def clean_vehicle_color(self):
        color = self.cleaned_data.get('vehicle_color')
        if color:
            # Check if color contains only alphabets and spaces
            if not re.match(r'^[A-Za-z\s]+$', color):
                raise forms.ValidationError("Color should only contain letters")
        return color
    
    def clean_plate_number(self):
        plate_number = self.cleaned_data.get('plate_number')
        
        # If this field is empty, it means we're using an existing vehicle
        # So we should skip validation
        if not plate_number:
            return plate_number
            
        # Remove spaces for validation
        cleaned_plate_number = plate_number.replace(" ", "")
        
        # Check if plate number follows typical pattern (alphanumeric and dash)
        if not re.match(r'^[A-Za-z0-9\-]+$', cleaned_plate_number):
            raise forms.ValidationError("Plate number contains invalid characters.")

        # Check for duplicate plate number but handle both new and existing vehicles
        query = Vehicle.objects.filter(plate_number__iexact=plate_number)
        
        # If we're editing an existing vehicle, exclude it from the check
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise forms.ValidationError("This plate number is already registered.")
            
        return plate_number
    
    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['vehicle_name', 'vehicle_color', 'plate_number']

        if any(cleaned_data.get(field) in [None, ''] for field in required_fields):
            raise forms.ValidationError("All fields must be filled.")
            
        return cleaned_data