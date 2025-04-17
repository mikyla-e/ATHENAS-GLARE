import os
from django.db import models
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
    id = models.AutoField(primary_key=True)  # Add this line
    psgcCode = models.CharField(max_length=10)
    regDesc = models.CharField(max_length=255)
    regCode = models.CharField(max_length=10)

    def __str__(self):
        return self.regDesc

    class Meta:
        db_table = 'refregion'
        managed = False

class Province(models.Model):
    id = models.AutoField(primary_key=True)  # Add this line
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
    id = models.AutoField(primary_key=True)  # Add this line
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
    id = models.AutoField(primary_key=True)  # Add this line
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
    employee_image = models.ImageField(null=True, blank=True, upload_to='images/')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def update_attendance_stats(self):
        # Update attendance statistics for the current month
        today = timezone.now().date()
        first_day = today.replace(day=1)
        
        self.days_worked = self.attendances.filter(
            date__gte=first_day,
            date__lte=today,
            attendance_status='Present'  # Assuming this is the correct status value
        ).count()
        
        # Calculate business days
        workdays_so_far = 0
        day = first_day
        while day <= today:
            if day.weekday() < 5:  # Monday to Friday
                workdays_so_far += 1
            day += timedelta(days=1)

        self.absences = workdays_so_far - self.days_worked
        self.save(update_fields=['days_worked', 'absences'])

class Attendance(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'Present', _('Present')
        ABSENT = 'Absent', _('Absent')
    
    attendance_id = models.AutoField(primary_key=True)
    time_in = models.TimeField(null=True, blank=True)  
    time_out = models.TimeField(null=True, blank=True)  
    date = models.DateField(default=timezone.now,null=False)
    hours_worked = models.FloatField(default=0, null=False)  
    attendance_status = models.CharField(max_length=8, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = models.CharField(max_length=255, null=True, blank=True)  
    employee_id_fk = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')

    def calculate_hours_worked(self):
        
        # Calculate hours worked for the day
        if self.time_in and self.time_out:
            time_in_dt = datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.combine(self.date, self.time_out)
            worked_hours = (time_out_dt - time_in_dt).total_seconds() / 3600  # Convert seconds to hours
            self.hours_worked = round(worked_hours, 2)
            self.save()
        
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
    employee_id_fk = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    attendance_id_fk = models.ForeignKey(Attendance, null=True, blank=True, on_delete=models.CASCADE)

class History(models.Model):
    history_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=False)
    date_time = models.DateTimeField(default=timezone.now, null=False)

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=False)
    gender = models.CharField(max_length=6, choices=Gender.choices, null=False)
    contact_number = models.CharField(max_length=15, null=True)
    region = models.CharField(max_length=255, null=False, default='')
    province = models.CharField(max_length=255, null=False, default='')
    municipality = models.CharField(max_length=255, null=False, default='')
    barangay = models.CharField(max_length=255, null=False, default='')

class Vehicle(models.Model):
    vehicle_id = models.AutoField(primary_key=True)
    vehicle_name = models.CharField(max_length=100, null=False)
    vehicle_color = models.CharField(max_length=100, null=False)
    plate_number = models.CharField(max_length=100, null=False)

class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, null=False)
    service_image = models.ImageField(null=True, blank=True, upload_to='images/')

# Create your task model here.