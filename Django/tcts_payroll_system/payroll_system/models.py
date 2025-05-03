import os
import re
from datetime import timedelta, datetime, time
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

def rename_employee_image(instance, filename):
    
    # Get file extension
    ext = filename.split('.')[-1]
    
    sanitized_name = slugify(os.path.splitext(filename)[0])
    
    # Return the new path
    return f'employee_images/{sanitized_name}.{ext}'

def validate_image_size(image):
    max_size = 5 * 1024 * 1024  # 5MB
    if image.size > max_size:
        raise ValidationError(_('Image size cannot exceed 5MB.'))

class Gender(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
        OTHERS = 'Others', _('Others')

# Create your models here.
class Region(models.Model):
    id = models.AutoField(primary_key=True)
    psgcCode = models.CharField(max_length=10)
    regDesc = models.CharField(max_length=255)
    regCode = models.CharField(max_length=10)

    def __str__(self):
        return self.regDesc

    class Meta:
        db_table = 'refregion'
        managed = False

class Province(models.Model):
    id = models.AutoField(primary_key=True)
    psgcCode = models.CharField(max_length=10)
    provDesc = models.CharField(max_length=255)
    regCode = models.CharField(max_length=10)
    provCode = models.CharField(max_length=10)

    def __str__(self):
        return self.provDesc

    class Meta:
        db_table = 'refprovince'
        managed = False

class City(models.Model):
    id = models.AutoField(primary_key=True)
    psgcCode = models.CharField(max_length=10)
    citymunDesc = models.CharField(max_length=255)
    regDesc = models.CharField(max_length=10)
    provCode = models.CharField(max_length=10)
    citymunCode = models.CharField(max_length=10)

    def __str__(self):
        return self.citymunDesc
    
    class Meta:
        db_table = 'refcitymun'
        managed = False

class Barangay(models.Model):
    id = models.AutoField(primary_key=True)
    brgyDesc = models.CharField(max_length=255)
    regCode = models.CharField(max_length=10)
    provCode = models.CharField(max_length=10)
    citymunCode = models.CharField(max_length=10)
    brgyCode = models.CharField(max_length=10)

    def __str__(self):
        return self.brgyDesc

    class Meta:
        db_table = 'refbrgy'
        managed = False

class Employee(models.Model):
    class HighestEducation(models.TextChoices):
        GRADESCHOOL = 'Grade School', _('Grade School')
        HIGHSCHOOL = 'High School', _('High School')
        BACHELORS_DEGREE = 'Bachelor\'s Degree', _('Bachelor\'s Degree')
        VOCATIONAL_EDUCATION = 'Vocational Education', _('Vocational Education')
        MASTERS_DEGREE = 'Master\'s Degree', _('Master\'s Degree')

    class EmployeeStatus(models.TextChoices):
        FULLTIME = 'Full Time', _('Full Time')
        PARTTIME = 'Part Time', _('Part Time')

    employee_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=False)
    gender = models.CharField(max_length=6, choices=Gender.choices, null=False)
    date_of_birth = models.DateField(null=True)
    contact_number = models.CharField(max_length=15, null=True)
    emergency_contact = models.CharField(max_length=15, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, to_field='id')
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, to_field='id')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, to_field='id')
    barangay = models.ForeignKey(Barangay, on_delete=models.SET_NULL, null=True, to_field='id')
    highest_education = models.CharField(max_length=20, choices=HighestEducation.choices, null=True)
    work_experience = models.CharField(max_length=2083, null=True, blank=True)
    daily_rate = models.FloatField(default=0, null=False)
    date_of_employment = models.DateField(default=timezone.now)
    employee_status = models.CharField(max_length=9, choices=EmployeeStatus.choices, null=True)
    is_active = models.BooleanField(default=True)
    absences = models.IntegerField(default=0, null=False)
    employee_image = models.ImageField(null=False, upload_to='images/', validators=[validate_image_size])

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        # Call parent's clean method
        super().clean()
        
        # Name validation
        if self.first_name and self.first_name.strip() == '':
            raise ValidationError({'first_name': _('First name cannot be empty.')})
            
        if self.last_name and self.last_name.strip() == '':
            raise ValidationError({'last_name': _('Last name cannot be empty.')})
        
        # Location validation - ensure proper relationship between region, province, city
        if self.city and not self.province:
            raise ValidationError(_('Province must be specified if city is provided.'))
            
        if self.province and not self.region:
            raise ValidationError(_('Region must be specified if province is provided.'))
            
        if self.barangay and not self.city:
            raise ValidationError(_('City must be specified if barangay is provided.'))
        
        # Check for duplicate employees based on name and birth date
        if self.first_name and self.last_name and self.date_of_birth:
            existing_employees = Employee.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth
            )
            
            # Exclude self when updating an existing employee
            if self.employee_id:
                existing_employees = existing_employees.exclude(employee_id=self.employee_id)
            
            # If any match is found, raise a validation error
            if existing_employees.exists():
                raise ValidationError({
                    'first_name': "An employee with this name and birth date already exists.",
                    'last_name': "Please verify this is not a duplicate entry or add a middle name to distinguish."
                })
        
        # Validate contact number format
        if self.contact_number:
            phone_regex = re.compile(r'^\+?[0-9]{10,15}$')
            if not phone_regex.match(self.contact_number):
                raise ValidationError({
                    'contact_number': _('Phone number must be entered in the format: "+999999999". 10-15 digits allowed.')
                })
        
        # Validate emergency contact format
        if self.emergency_contact:
            phone_regex = re.compile(r'^\+?[0-9]{10,15}$')
            if not phone_regex.match(self.emergency_contact):
                raise ValidationError({
                    'emergency_contact': _('Emergency contact must be entered in the format: "+999999999". 10-15 digits allowed.')
                })
        
        # Validate emergency contact is different from contact number
        if self.contact_number and self.emergency_contact and self.contact_number == self.emergency_contact:
            raise ValidationError({'emergency_contact': "Emergency contact cannot be the same as personal contact."})
        
        # Validate age is at least 18
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year
            
            # Adjust age if birthday hasn't occurred yet this year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age -= 1
            
            if age < 18:
                raise ValidationError({'date_of_birth': "Employee must be at least 18 years old."})
        
        # Validate date of employment
        if self.date_of_employment and self.date_of_birth:
            # Check if employment date is after birth date
            if self.date_of_employment < self.date_of_birth:
                raise ValidationError({'date_of_employment': "Employment date cannot be before birth date."})
            
            # Check if employee is at least 18 at employment date
            age_at_employment = self.date_of_employment.year - self.date_of_birth.year
            if (self.date_of_employment.month, self.date_of_employment.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age_at_employment -= 1
                
            if age_at_employment < 18:
                raise ValidationError({'date_of_employment': "Employee must be at least 18 years old at date of employment."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Attendance(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'Present', _('Present')
        ABSENT = 'Absent', _('Absent')
    
    attendance_id = models.AutoField(primary_key=True)
    time_in = models.TimeField(null=True, blank=True)  
    time_out = models.TimeField(null=True, blank=True)  
    date = models.DateField(default=timezone.now, null=False)
    hours_worked = models.FloatField(default=0, null=False)  
    attendance_status = models.CharField(max_length=8, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='attendances')
    
    # Define work hour boundaries
    WORK_START_TIME = time(8, 0)  # 8:00 AM
    WORK_END_TIME = time(17, 0)   # 5:00 PM
    
    class Meta:
        ordering = ['date', 'time_in']
    
    def __str__(self):
        status = f"[{self.attendance_status}]"
        employee = self.employee.first_name if hasattr(self.employee, 'first_name') else f"Employee #{self.employee_id_fk_id}"
        date_str = self.date.strftime('%Y-%m-%d')
        hours = f"{self.hours_worked}hrs" if self.hours_worked else "No hours recorded"
        
        return f"{employee} - {date_str} {status} - {hours}"
    
    def clean(self):
        # Validate time_in is before time_out
        if self.time_in and self.time_out and self.time_in >= self.time_out:
            raise ValidationError(_('Time in must be before time out.'))
        
        # Validate attendance_status is consistent with times
        if self.attendance_status == self.AttendanceStatus.PRESENT and not self.time_in:
            raise ValidationError(_('Present status requires time in to be set.'))
        
        # Validate work hours: time_in must not be earlier than 8:00 AM
        if self.time_in and self.time_in < self.WORK_START_TIME:
            raise ValidationError(_('Cannot time in before 8:00 AM. Work hours start at 8:00 AM.'))
        
        # Validate work hours: time_out must not be later than 5:00 PM
        if self.time_out and self.time_out > self.WORK_END_TIME:
            raise ValidationError(_('Cannot time out after 5:00 PM. Work hours end at 5:00 PM.'))
            
    def calculate_hours_worked(self):
        # Calculate hours worked for the day
        if self.time_in and self.time_out:
            time_in_dt = datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.combine(self.date, self.time_out)
            worked_seconds = (time_out_dt - time_in_dt).total_seconds()
            self.hours_worked = round(worked_seconds / 3600, 2)

    def save(self, *args, **kwargs):
        self.full_clean()  
        
        if self.time_in and self.time_out:
            if not kwargs.pop('skip_hours_calculation', False):
                time_in_dt = datetime.combine(self.date, self.time_in)
                time_out_dt = datetime.combine(self.date, self.time_out)
                worked_seconds = (time_out_dt - time_in_dt).total_seconds()
                self.hours_worked = round(worked_seconds / 3600, 2)
        
        super().save(*args, **kwargs)
            
    def get_formatted_hours_worked(self):
        # Returns time worked as hh:mm:ss if time_out exists
        if self.time_in and self.time_out:
            time_in_dt = datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.combine(self.date, self.time_out)
            duration = time_out_dt - time_in_dt
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None
    
class PayrollPeriod(models.Model):
    class PayrollStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSED = 'PROCESSED', _('Processed')

    class Type(models.TextChoices):
        WEEKLY = 'WEEKLY', _('Weekly')
        BIWEEKLY = 'BY-WEEKLY', _('By-weekly')
        MONTHLY = 'MONTHLY', _('Monthly')

    payroll_period_id = models.AutoField(primary_key=True)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    payment_date = models.DateField(null=False)
    payroll_status = models.CharField(max_length=9, choices=PayrollStatus.choices, default=PayrollStatus.PENDING)
    type = models.CharField(max_length=9, choices=Type.choices)

    def save(self, *args, **kwargs):
        if self.end_date:
            self.payment_date = self.end_date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.start_date} to {self.end_date} ({self.get_payroll_status_display()})"

class Deduction(models.Model):
    class DeductionType(models.TextChoices):
        SSS = 'SSS', _('SSS')
        PHILHEALTH = 'PHILHEALTH', _('PhilHealth')
        PAGIBIG = 'PAGIBIG', _('Pag-IBIG')

    deduction_id = models.AutoField(primary_key=True)
    payroll_record = models.ForeignKey('PayrollRecord', on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DeductionType.choices)
    amount = models.FloatField(default=0)

    def __str__(self):
        return f"{self.type}: {self.amount:.2f}"

class PayrollRecord(models.Model):
    payroll_record_id = models.AutoField(primary_key=True)
    days_worked = models.IntegerField(default=0)
    gross_pay = models.FloatField(default=0)
    incentives = models.FloatField(default=0)
    cash_advance = models.FloatField(default=0)
    net_pay = models.FloatField(default=0)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='payrollrecords')
    payroll_period = models.ForeignKey('PayrollPeriod', on_delete=models.CASCADE, related_name='payrollrecords')

    def calculate_gross_pay(self):
        return self.days_worked * self.employee.daily_rate + self.incentives

    def calculate_total_deductions(self):
        return sum(d.amount for d in self.deductions.all())

    def calculate_net_pay(self):
        total_deductions = self.calculate_total_deductions()
        return self.gross_pay - total_deductions - self.cash_advance

    def save(self, *args, **kwargs):
        self.gross_pay = self.calculate_gross_pay()
        super().save(*args, **kwargs)  # Save first so deductions have a related PayrollRecord
        self.net_pay = self.calculate_net_pay()
        super().save(update_fields=['net_pay'])  # Update net pay only

    def __str__(self):
        return f"{self.employee} | {self.payroll_period.start_date} - {self.net_pay:.2f} net pay"
    
class History(models.Model):
    history_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=False)
    date_time = models.DateTimeField(default=timezone.now, null=False)

    def __str__(self):
        return f"{self.description} - {self.date_time}"

    def clean(self):
        # Validate that description is not just whitespace
        if self.description and self.description.strip() == '':
            raise ValidationError(_('Description cannot be empty or whitespace only.'))
            
        # Future date validation
        if self.date_time and self.date_time > timezone.now():
            raise ValidationError(_('History date cannot be in the future.'))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=False)
    contact_number = models.CharField(max_length=15, null=False)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, to_field='id')
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, to_field='id')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, to_field='id')
    barangay = models.ForeignKey(Barangay, on_delete=models.SET_NULL, null=True, to_field='id')

    def clean(self):
        # Name validation
        if self.first_name and self.first_name.strip() == '':
            raise ValidationError({'first_name': _('First name cannot be empty.')})
            
        if self.last_name and self.last_name.strip() == '':
            raise ValidationError({'last_name': _('Last name cannot be empty.')})
        
        # Validate contact number format
        if self.contact_number:
            phone_regex = re.compile(r'^\+?[0-9]{10,15}$')
            if not phone_regex.match(self.contact_number):
                raise ValidationError({
                    'contact_number': _('Phone number must be entered in the format: "+999999999". 10-15 digits allowed.')
                })
        
        # Location validation - ensure proper relationship between region, province, city
        if self.city and not self.province:
            raise ValidationError(_('Province must be specified if city is provided.'))
            
        if self.province and not self.region:
            raise ValidationError(_('Region must be specified if province is provided.'))
            
        if self.barangay and not self.city:
            raise ValidationError(_('City must be specified if barangay is provided.'))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Vehicle(models.Model):
    vehicle_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_name = models.CharField(max_length=100, null=False)
    vehicle_color = models.CharField(max_length=100, null=False)
    plate_number = models.CharField(max_length=100, null=False)

    def __str__(self):
        return f"{self.vehicle_name} ({self.plate_number})"
    
    def clean(self):
        # Basic validation for vehicle details
        if self.vehicle_name and self.vehicle_name.strip() == '':
            raise ValidationError({'vehicle_name': _('Vehicle name cannot be empty.')})
            
        if self.vehicle_color and self.vehicle_color.strip() == '':
            raise ValidationError({'vehicle_color': _('Vehicle color cannot be empty.')})
            
        # Plate number validation - simple format check (can be adjusted based on your country's format)
        if self.plate_number:
            if self.plate_number.strip() == '':
                raise ValidationError({'plate_number': _('Plate number cannot be empty.')})
            
        # Check if plate number is unique, but only for new vehicles or when the plate number changes
        if not self.pk or Vehicle.objects.filter(plate_number=self.plate_number).exclude(pk=self.pk).exists():
            # Only check uniqueness for new vehicles (no pk) or if the plate number was changed
            existing_vehicle = Vehicle.objects.filter(plate_number=self.plate_number).exclude(pk=self.pk)
            if existing_vehicle.exists():
                raise ValidationError({'plate_number': _('This plate number is already registered.')})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, null=False)
    service_image = models.ImageField(null=False, upload_to='images/', validators=[validate_image_size])

    def __str__(self):
        return self.title
    
    def clean(self):
        if self.title and self.title.strip() == '':
            raise ValidationError({'title': _('Service title cannot be empty.')})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Task(models.Model):
    class TaskStatus(models.TextChoices):
        IN_PROGRESS = 'In Progress', _('In Progress')
        COMPLETED = 'Completed', _('Completed')
    
    task_id = models.AutoField(primary_key=True)
    task_name = models.CharField(max_length=100, null=False)
    task_status = models.CharField(max_length=11, choices=TaskStatus.choices, default=TaskStatus.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='tasks')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tasks')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='tasks')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks')

    def __str__(self):
        return f"{self.task_name} - {self.customer} - {self.task_status}" 
    
    def clean(self):
        if self.task_name and self.task_name.strip() == '':
            raise ValidationError({'task_name': _('Task name cannot be empty.')})
            
        # Validate relationships
        if self.vehicle and self.vehicle.customer != self.customer:
            raise ValidationError(_('The vehicle must belong to the selected customer.'))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)