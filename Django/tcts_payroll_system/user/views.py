from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from payroll_system.models import Admin
from payroll_system.forms import AdminForm

# Create your views here.

def time_in_out(request): 
    admin = Admin.objects.first()
    if request.method == 'POST':
        id = request.POST.get('employee-id')

        if id == str(admin.admin_id): 
            return redirect('/user/admin_login/?next=/payroll_system/dashboard')
        else:
            return redirect('/user/time_in_out')

    return render(request, 'user/time_in_out.html')