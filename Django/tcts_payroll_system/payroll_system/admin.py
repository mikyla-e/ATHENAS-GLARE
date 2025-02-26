from django.contrib import admin
from .models import Admin, Employee, Payroll, Attendance, History


class AdminAdmin(admin.ModelAdmin):
    list_display = ('username', 'password')

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
                     'barangay', 'postal_address', 'highest_education', 'work_experience', 'date_of_employment',
                     'employee_status', 'absences')

admin.site.register(Admin, AdminAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Payroll)
admin.site.register(Attendance)
admin.site.register(History)