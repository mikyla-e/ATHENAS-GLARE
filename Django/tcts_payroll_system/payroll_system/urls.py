from django.contrib import admin
from django.urls import path
from . import views

app_name = 'payroll_system'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('time_in_out/', views.time_in_out, name='time_in_out'),
    path('employee_registration/', views.employee_registration, name='employee_registration'),
    path('payroll/', views.payroll, name='payroll')
    
]