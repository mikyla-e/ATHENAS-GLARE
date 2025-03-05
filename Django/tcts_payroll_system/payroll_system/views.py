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

@login_required
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

@login_required
def employees(request):
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    context = {
        'employees': employees
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    context = {
        'employee' : employee,
    }
    return render(request, 'payroll_system/employee_profile.html', context)

@login_required
def payrolls(request):
    employees = Employee.objects.prefetch_related('payrolls').all()
    context = {
        'employees': employees
    }
    return render(request, 'payroll_system/payroll.html', context)

@login_required
def payroll_individual(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    context = {
        'employee' : employee,
    }
    return render(request, 'payroll_system/payroll_individual.html', context)

@login_required
def payroll_edit(request):
    return render(request, 'payroll_system/payroll_edit.html')

@login_required
def settings(request):
    return render(request, 'payroll_system/settings.html')
