from django.contrib import admin
from .models import Admin
from .models import Attendance
from .models import Employee
from .models import History


# Register your models here.

admin.site.register(Admin)
admin.site.register(Attendance)
admin.site.register(Employee)
admin.site.register(History)