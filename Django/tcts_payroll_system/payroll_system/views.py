from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import EmployeeForm
# Create your views here.

@login_required
def dashboard(request):
    return render(request, 'payroll_system/dashboard.html')

def payroll(request):
    return render(request, '/payroll_system/payroll.html')

def time_in_out(request):
    return render(request, 'payroll_system/time_in_out.html')

def employee_registration(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        form.save()
        return redirect('/payroll_system/employee_registration')
    form = EmployeeForm()
    context = {
        'form': form,
    }
    return render(request, 'payroll_system/employee_registration.html', context)

def employees():
    pass

def payrolls():
    pass
