from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def dashboard(request):
    return render(request, 'payroll_system/dashboard.html')

def time_in_out(request):
    return render(request, 'payroll_system/time_in_out.html')

def register_employee():
    pass

def employees():
    pass

def payrolls():
    pass
