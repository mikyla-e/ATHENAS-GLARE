from django.contrib import admin
from .models import Admin
from .models import Employee
from .models import Attendance
from .models import Payroll
from .models import History

# Register your models here.

admin.site.register(Admin)
admin.site.register(Employee)
admin.site.register(Attendance)
admin.site.register(Payroll)
admin.site.register(History)