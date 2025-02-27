from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Admin(models.Model):
    admin_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=100, null=False)
    password = models.CharField(max_length=100, null=False)

class Employee(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHERS = 'O', _('Others')

    class HighestEducation(models.TextChoices):
        GRADESCHOOL = 'GS', _('Grade School')
        HIGHSCHOOL = 'HS', _('High School')
        BACHELORS_DEGREE = 'B.', _('Bachelor\'s Degree')
        VOCATIONAL_EDUCATION = 'Voc. Ed.', _('Vocational Education')
        MASTERS_DEGREE = 'M.', _('Master\'s Degree')

    class EmployeeStatus(models.TextChoices):
        FULLTIME = 'FT', _('Full Time')
        PARTTIME = 'PT', _('Part Time')

    class PayrollStatus(models.TextChoices):
        PENDING = 'PEND', _('Pending')
        PROCESSED = 'PROC', _('Processed')
    
    employee_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    last_name = models.CharField(max_length=100, null=False)
    gender = models.CharField(max_length=1, choices=Gender.choices, null=False)
    date_of_birth = models.DateField(null=True)
    contact_number = models.CharField(max_length=15, null=True)
    emergency_contact = models.CharField(max_length=15, null=True)
    barangay = models.CharField(max_length=100, null=True)
    postal_address = models.IntegerField(null=True)
    highest_education = models.CharField(max_length=8, choices=HighestEducation.choices, null=True)
    work_experience = models.CharField(max_length=2083, null=True)
    date_of_employment = models.DateField(default=timezone.now)
    employee_status = models.CharField(max_length=2, choices=EmployeeStatus.choices, null=True)
    payroll_status = models.CharField(max_length=4, choices=PayrollStatus.choices, null=True, blank=True)
    absences = models.IntegerField(default=0, null=False)
    employee_image = models.ImageField(null=True, blank=True, upload_to='images/')
    admin_id_fk = models.ForeignKey(Admin, on_delete=models.CASCADE, null=True, blank=True)

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    time_in = models.TimeField(null=True, blank=True)  
    time_out = models.TimeField(null=True, blank=True)  
    date = models.DateField(default=timezone.now,null=False)
    hours_worked = models.FloatField(default=0, null=False)  
    remarks = models.CharField(max_length=255, null=True, blank=True)  
    employee_id_fk = models.ForeignKey(Employee, on_delete=models.CASCADE)

class Payroll(models.Model):
    payroll_id = models.AutoField(primary_key=True)
    incentives = models.FloatField(default=0, null=False) 
    payroll_status = models.CharField(max_length=15, null=False)
    salary = models.FloatField(default=0, null=False)  
    cash_advance = models.FloatField(default=0, null=False)  
    under_time = models.FloatField(default=0, null=False)  
    payment_date = models.DateField(null=False)
    employee_id_fk = models.ForeignKey(Employee, on_delete=models.CASCADE)
    attendance_id_fk = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    admin_id_fk = models.ForeignKey(Admin, on_delete=models.CASCADE)

class History(models.Model):
    history_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=False)
    date_time = models.DateTimeField(default=timezone.now, null=False)
    admin_id_fk = models.ForeignKey(Admin, on_delete=models.CASCADE)