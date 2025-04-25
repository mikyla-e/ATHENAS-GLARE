import os
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from datetime import timedelta, datetime

def rename_employee_image(instance, filename):
    
    # Get file extension
    ext = filename.split('.')[-1]
    
    sanitized_name = slugify(os.path.splitext(filename)[0])
    
    # Return the new path
    return f'employee_images/{sanitized_name}.{ext}'

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
    employee_image = models.ImageField(null=False, upload_to='images/')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        #Validate model data before saving
        # Call parent's clean method
        super().clean()
        
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
        if self.contact_number and (not self.contact_number.isdigit() or len(self.contact_number) != 11):
            raise ValidationError({'contact_number': "Contact number must be exactly 11 digits."})
        
        # Validate emergency contact format
        if self.emergency_contact and (not self.emergency_contact.isdigit() or len(self.emergency_contact) != 11):
            raise ValidationError({'emergency_contact': "Emergency contact must be exactly 11 digits."})
        
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
                raise ValidationError({
                    'date_of_employment': "Employee must be at least 18 years old at date of employment."
                })

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
    
    class Meta:
        ordering = ['date', 'time_in']
    
    def __str__(self):
        status = f"[{self.attendance_status}]"
        employee = self.employee_id_fk.first_name if hasattr(self.employee_id_fk, 'first_name') else f"Employee #{self.employee_id_fk_id}"
        date_str = self.date.strftime('%Y-%m-%d')
        hours = f"{self.hours_worked}hrs" if self.hours_worked else "No hours recorded"
        
        return f"{employee} - {date_str} {status} - {hours}"
    
    def calculate_hours_worked(self):
        
        # Calculate hours worked for the day
        if self.time_in and self.time_out:
            time_in_dt = datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.combine(self.date, self.time_out)
            worked_seconds = (time_out_dt - time_in_dt).total_seconds()
            self.hours_worked = round(worked_seconds / 3600, 2)
            self.save()
    #New        
    def get_formatted_hours_worked(self):
        """Returns time worked as hh:mm:ss if time_out exists"""
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
    under_time = models.FloatField(default=0, null=False)  
    payment_date = models.DateField(null=False)
    employee_id_fk = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='payrolls')
    attendance_id_fk = models.ForeignKey(Attendance, null=True, blank=True, on_delete=models.CASCADE)
    
    def __str__(self):
        employee = self.employee_id_fk.first_name if hasattr(self.employee_id_fk, 'first_name') else f"Employee #{self.employee_id_fk_id}"
        date_str = self.payment_date.strftime('%Y-%m-%d')
        amount = f"₱{self.salary:,.2f}" if self.salary else "₱0.00"
        status = f"[{self.payroll_status}]"
        
        return f"Payroll #{self.payroll_id} - {employee} - {date_str} - {amount} {status}"

class History(models.Model):
    history_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=False)
    date_time = models.DateTimeField(default=timezone.now, null=False)

    def __str__(self):
        return self.description

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=False)
    gender = models.CharField(max_length=6, choices=Gender.choices, null=False)
    contact_number = models.CharField(max_length=15, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, to_field='id')
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, to_field='id')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, to_field='id')
    barangay = models.ForeignKey(Barangay, on_delete=models.SET_NULL, null=True, to_field='id')

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

class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, null=False)
    service_image = models.ImageField(null=False, upload_to='images/')

    def __str__(self):
        return self.title

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