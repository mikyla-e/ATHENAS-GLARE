from django import forms
from django.forms import ModelForm
from .models import Admin, Employee, Payroll

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
                   'barangay', 'postal_address', 'highest_education', 'work_experience', 'date_of_employment',
                   'employee_status', 'employee_image')
        widgets = {
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'gender': forms.Select(),
            'date_of_birth': forms.DateInput(),
            'contact_number': forms.TextInput(),
            'emergency_contact': forms.TextInput(),
            'barangay': forms.TextInput(),
            'postal_address': forms.TextInput(),
            'highest_education': forms.Select(),
            'work_experience': forms.Textarea(),
            'date_of_employment': forms.DateInput(),
            'employee_status': forms.Select(),
            'employee_image': forms.ClearableFileInput(),
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        print("Running clean_contact_number with:", contact_number)
        if len(contact_number) != 11:
            raise forms.ValidationError('Contact number must be exactly 11 digits')
        return contact_number
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image required only for new employees (not for updates)
        if not self.instance.pk:  # If this is a new employee
            self.fields['employee_image'].required = True
    
class PayrollForm(ModelForm):
    class Meta:
        model = Payroll
        fields = ('rate', 'deductions', 'payment_date', 'payroll_status')
        widgets = {
            'rate': forms.NumberInput(),
            'deductions': forms.NumberInput(),
            'payment_date': forms.DateInput(),
            'payroll_status': forms.Select()
        }
        