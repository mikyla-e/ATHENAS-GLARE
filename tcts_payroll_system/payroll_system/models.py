from django.db import models

# Create your models here.

class Admin(models.Model):
    admin_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    last_name = models.CharField(max_length=100, null=False)
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=100, null=False)

class Employee(models.Model):
    employee_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, null=False)
    middle_name = models.CharField(max_length=100, null=True, blank=True)  
    last_name = models.CharField(max_length=100, null=False)
    email = models.EmailField(unique=True, null=False)
    employee_status = models.CharField(max_length=15, null=False)
    absences = models.IntegerField(default=0, null=False)  

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    time_in = models.DateTimeField(null=True, blank=True)  
    time_out = models.DateTimeField(null=True, blank=True)  
    date = models.DateField(null=False)
    hours_worked = models.FloatField(default=0, null=False)  
    remarks = models.CharField(max_length=255, null=True, blank=True)  
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

class Payroll(models.Model):
    payroll_id = models.AutoField(primary_key=True)
    incentives = models.FloatField(default=0, null=False) 
    payroll_status = models.CharField(max_length=15, null=False)
    salary = models.FloatField(default=0, null=False)  
    cash_advance = models.FloatField(default=0, null=False)  
    under_time = models.FloatField(default=0, null=False)  
    payment_date = models.DateField(null=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)

class History(models.Model):
    history_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=False)
    date_and_time = models.DateTimeField(null=False)
