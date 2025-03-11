import os
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from datetime import timedelta, datetime

# Create your models here.
def rename_employee_image(instance, filename):
    # Get file extension
    ext = filename.split('.')[-1]
    # Create a sanitized name
    sanitized_name = slugify(os.path.splitext(filename)[0])
    # Return the new path
    return f'employee_images/{sanitized_name}.{ext}'

class Admin(models.Model):
    admin_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=100, null=False)
    password = models.CharField(max_length=100, null=False)

class Employee(models.Model):
    class Gender(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
        OTHERS = 'Others', _('Others')

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
    last_name = models.CharField(max_length=100, null=False)
    gender = models.CharField(max_length=6, choices=Gender.choices, null=False)
    date_of_birth = models.DateField(null=True)
    contact_number = models.CharField(max_length=15, null=True)
    emergency_contact = models.CharField(max_length=15, null=True)
    barangay = models.CharField(max_length=100, null=True)
    postal_address = models.IntegerField(null=True)
    highest_education = models.CharField(max_length=20, choices=HighestEducation.choices, null=True)
    work_experience = models.CharField(max_length=2083, null=True)
    date_of_employment = models.DateField(default=timezone.now)
    days_worked = models.IntegerField(default=0, null=False)
    employee_status = models.CharField(max_length=9, choices=EmployeeStatus.choices, null=True)
    active_status = models.CharField(max_length=8, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)
    absences = models.IntegerField(default=0, null=False)
    employee_image = models.ImageField(null=True, blank=True, upload_to='images/')

    def update_attendance_stats(self):
        """Update attendance statistics for the current month"""
        today = timezone.now().date()
        first_day = today.replace(day=1)
        
        # Count days worked
        self.days_worked = self.attendances.filter(
            date__gte=first_day,
            date__lte=today,
            attendance_status=Attendance.AttendanceStatus.PRESENT
        ).count()
        
        # Calculate business days
        workdays_so_far = 0
        day = first_day
        while day <= today:
            if day.weekday() < 5:
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
        """Calculate hours worked for the day"""
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
    admin_id_fk = models.ForeignKey(Admin, on_delete=models.CASCADE)