from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import EmployeeForm
from .models import Employee

@login_required
def dashboard(request):
    return render(request, 'payroll_system/dashboard.html')

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

def employees(request):
    employees = Employee.objects.all()
    context = {
        'employees': employees
    }
    return render(request, 'payroll_system/employees.html', context)

def employee_profile(request, employee_id):
    employee = Employee.objects.get(employee_id=employee_id)
    context = {
        'employee' : employee,
    }
    return render(request, 'payroll_system/employee_profile.html', context)

def payrolls(request):
    return render(request, 'payroll_system/payroll.html')

def payroll_individual(request):
    return render(request, 'payroll_system/payroll_individual.html')

def settings(request):
    return render(request, 'payroll_system/settings.html')
