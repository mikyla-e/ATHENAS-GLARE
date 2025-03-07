from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from payroll_system.models import Admin
from django.contrib.auth.forms import AuthenticationForm

# Create your views here.