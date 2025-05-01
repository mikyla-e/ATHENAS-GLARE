import os
import re
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from datetime import timedelta, datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, time


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

    class ActiveStatus(models.TextChoices):
        ACTIVE = 'Active', _('Active')
        INACTIVE = 'Inactive', _('Inactive')

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
    date_of_employment = models.DateField(default=timezone.now)
    days_worked = models.IntegerField(default=0, null=False)
    employee_status = models.CharField(max_length=9, choices=EmployeeStatus.choices, null=True)
    active_status = models.CharField(max_length=8, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)
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
        # Run full validation before saving (ensures model-level validation runs)
        self.full_clean()
        super().save(*args, **kwargs)

    def update_attendance_stats(self):
        today = timezone.now().date()
        start_date = self.date_of_employment

        if start_date > today:
            return

        # Count working days (exclude Sundays)
        total_working_days = 0
        day = start_date
        while day <= today:
            if day.weekday() != 6:  # 6 = Sunday
                total_working_days += 1
            day += timedelta(days=1)

        # Count present days based on actual time_in
        present_days = self.attendances.filter(
            date__lte=today,
            time_in__isnull=False
        ).values('date').distinct().count()

        # Calculate absences
        absences = max(total_working_days - present_days, 0)

        # Update DB and instance
        Employee.objects.filter(employee_id=self.employee_id).update(
            days_worked=present_days,
            absences=absences
        )
        self.days_worked = present_days
        self.absences = absences

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
    remarks = models.CharField(max_length=255, null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    employee_id_fk = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='attendances')
    
    # Define work hour boundaries
    WORK_START_TIME = time(8, 0)  # 8:00 AM
    WORK_END_TIME = time(17, 0)   # 5:00 PM
    
    class Meta:
        ordering = ['date', 'time_in']
    
    def __str__(self):
        status = f"[{self.attendance_status}]"
        employee = self.employee_id_fk.first_name if hasattr(self.employee_id_fk, 'first_name') else f"Employee #{self.employee_id_fk_id}"
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
        self.full_clean()  # Run validation before saving
        
        # Calculate hours before saving if needed
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

class Payroll(models.Model):
    class PayrollStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSED = 'PROCESSED', _('Processed')
    
    payroll_id = models.AutoField(primary_key=True)
    rate = models.FloatField(default=0, null=False)
    incentives = models.FloatField(default=0, null=False)
    payroll_status = models.CharField(max_length=9, choices=PayrollStatus.choices, default=PayrollStatus.PENDING, null=True, blank=True)
    deductions = models.FloatField(default=0, null=False)
    salary = models.FloatField(default=0, null=False)  
    cash_advance = models.FloatField(default=0, null=False)  
    payment_date = models.DateField(null=False)
    employee_id_fk = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='payrolls')
    attendance_id_fk = models.ForeignKey(Attendance, null=True, blank=True, on_delete=models.CASCADE)
    
    def __str__(self):
        employee = self.employee_id_fk.first_name if hasattr(self.employee_id_fk, 'first_name') else f"Employee #{self.employee_id_fk_id}"
        date_str = self.payment_date.strftime('%Y-%m-%d')
        amount = f"₱{self.salary:,.2f}" if self.salary else "₱0.00"
        status = f"[{self.payroll_status}]"
        
        return f"Payroll #{self.payroll_id} - {employee} - {date_str} - {amount} {status}"
    
    def calculate_salary(self, attendance_count=None):
        """
        Calculate the salary based on rate, incentives, and deductions.
        If attendance_count is provided, it will be used for the calculation,
        otherwise the method will fetch the attendance count from the database.
        """
        if attendance_count is None:
            if self.payment_date:
                # Get current week's Monday and Sunday
                # This ensures we only count attendance in the current week
                # regardless of payment date
                payment_date = self.payment_date
                current_weekday = payment_date.weekday()  # 0=Monday, 6=Sunday
                
                # Calculate the Monday of the current week
                start_date = payment_date - timedelta(days=current_weekday)
                
                # End date is either the payment date or Sunday of current week, whichever is earlier
                sunday_of_week = start_date + timedelta(days=6)
                end_date = min(payment_date, sunday_of_week)
                
                unique_days = Attendance.objects.filter(
                    employee_id_fk=self.employee_id_fk,
                    date__range=[start_date, end_date],
                    attendance_status='Present'
                ).values_list('date', flat=True).distinct().count()
                
                attendance_count = unique_days
            else:
                attendance_count = 0
        
        base_salary = self.rate * attendance_count
        
        # Calculate salary without including cash_advance in calculations
        # Cash advance is only considered when creating a new payroll
        self.salary = base_salary + self.incentives - self.deductions
        
        if self.salary < 0:
            self.salary = 0
            
        return self.salary
    
    def process_payroll(self):
        """
        Process the payroll - just return the cash advance amount for the next payroll
        Without resetting the cash advance on the current payroll
        """
        # Just return the cash advance amount so it can be transferred to next payroll
        cash_advance_amount = self.cash_advance
        
        # Set status to PROCESSED
        self.payroll_status = self.PayrollStatus.PROCESSED
        
        # Recalculate salary
        self.calculate_salary()
        
        return cash_advance_amount
    
    def get_next_payment_date(self, from_date=None, target_weekday=5):
        """
        Calculate the next payment date.
        
        Args:
            from_date: The reference date (defaults to today)
            target_weekday: The target day of week (0=Monday, 5=Saturday [default], 6=Sunday)
        
        Returns:
            The next date corresponding to the target weekday
        """
        if from_date is None:
            from_date = timezone.now().date()
        
        # Calculate days until target weekday (e.g., Saturday=5)
        days_until_target = (target_weekday - from_date.weekday()) % 7
        
        # If today is the target day, return next week's target day
        if days_until_target == 0:
            days_until_target = 7
            
        return from_date + timedelta(days=days_until_target)
        
    def get_next_saturday(self, from_date=None):
        """
        Maintained for backward compatibility.
        Returns the next Saturday from the given date.
        """
        return self.get_next_payment_date(from_date, target_weekday=5)
            
    def save(self, *args, **kwargs):
        # If this is a new payroll record (no ID yet)
        if not self.payroll_id:
            # If payment_date is not set, set it to the next Saturday by default
            if not self.payment_date:
                self.payment_date = self.get_next_saturday()
        
        # Check if payroll is being processed (status changing from PENDING to PROCESSED)
        is_processing = False
        
        if self.payroll_id:
            try:
                old_payroll = Payroll.objects.get(payroll_id=self.payroll_id)
                if (old_payroll.payroll_status == self.PayrollStatus.PENDING and 
                    self.payroll_status == self.PayrollStatus.PROCESSED):
                    is_processing = True
            except Payroll.DoesNotExist:
                pass
        
        # Calculate salary before saving
        self.calculate_salary()
        
        # Process payroll if needed (but don't reset cash advance)
        if is_processing:
            self.process_payroll()
        
        self.full_clean()
        super().save(*args, **kwargs)

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
    contact_number = models.CharField(max_length=15, null=True)
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
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='tasks')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tasks')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='tasks')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks', null=True)
    task_status = models.CharField(max_length=11, choices=TaskStatus.choices, default=TaskStatus.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        
class PayrollSettings(models.Model):
    global_payday = models.DateField()