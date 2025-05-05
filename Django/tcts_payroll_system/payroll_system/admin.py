from django.contrib import admin
from .models import Employee, Deduction, PayrollPeriod, PayrollRecord, Attendance, History, Service, Customer, Vehicle, Task

admin.site.register(Employee)
admin.site.register(Attendance)
admin.site.register(Deduction)
admin.site.register(PayrollPeriod)
admin.site.register(PayrollRecord)
admin.site.register(History)
admin.site.register(Service)
admin.site.register(Customer)
admin.site.register(Vehicle)
admin.site.register(Task)