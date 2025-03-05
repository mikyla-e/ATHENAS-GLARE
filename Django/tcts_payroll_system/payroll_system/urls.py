from django.contrib import admin
from django.urls import path
from . import views

app_name = 'payroll_system'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('employee_registration/', views.employee_registration, name='employee_registration'),
    path('employees/', views.employees, name='employees'),
    path('employee_profile/<int:employee_id>/', views.employee_profile, name='employee_profile'),
    path('payrolls/', views.payrolls, name='payrolls'),
    path('payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('settings/', views.settings, name='settings'),
]