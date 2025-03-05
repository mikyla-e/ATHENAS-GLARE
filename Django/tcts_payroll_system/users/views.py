from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from payroll_system.models import Admin
from django.contrib.auth.forms import AuthenticationForm

# Create your views here.

def time_in_out(request): 
    admin = Admin.objects.first()
    form = AuthenticationForm
    if request.method == 'POST':
        id = request.POST.get('employee-id')

        if id == str(admin.admin_id): 
            return redirect('/users/admin_login/?next=/payroll_system/dashboard')
        else:
            return redirect('/users/time_in_out')
    context = {
        'form': form
    }
    return render(request, 'users/time_in_out.html', context)