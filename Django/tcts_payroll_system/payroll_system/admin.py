from django.contrib import admin
from .models import Admin, Employee, Payroll, Attendance, History


class AdminAdmin(admin.ModelAdmin):
    list_display = ('username', 'password')

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'middle_name', 'last_name', 'email', 'employee_status', 'absences')

admin.site.register(Admin, AdminAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Payroll)
admin.site.register(Attendance)
admin.site.register(History)