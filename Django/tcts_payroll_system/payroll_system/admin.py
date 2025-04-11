from django.contrib import admin
from .models import Employee, Payroll, Attendance, History

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'emergency_contact',
                     'region', 'province', 'municipality', 'barangay', 'highest_education', 'work_experience', 'date_of_employment', 'days_worked', 'employee_status', 'absences', 
                     'employee_image')

class PayrollAdmin(admin.ModelAdmin):
    list_display = ('payroll_id', 'rate', 'incentives', 'payroll_status', 'deductions', 'salary', 'cash_advance', 'under_time',
                     'payment_date')
    
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendance_id', 'time_in', 'time_out', 'date', 'hours_worked', 'attendance_status','remarks')

admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Payroll, PayrollAdmin)
admin.site.register(Attendance, AttendanceAdmin)
admin.site.register(History)