from django.contrib import admin
from django.urls import path
from . import views

app_name = 'payroll_system'

urlpatterns = [
    path('time_in_out/', views.time_in_out, name='time_in_out'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('employee_registration/', views.employee_registration, name='employee_registration'),
    path('employees/', views.employees, name='employees'),
    path('employee_profile/<int:employee_id>/', views.employee_profile, name='employee_profile'),
    path('payrolls/', views.payrolls, name='payrolls'),
    path('payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('payroll_edit/<int:employee_id>/', views.payroll_edit , name='payroll_edit'),
    path('settings/', views.settings, name='settings'),
    path('about/', views.about, name='about'),
    path('get-address-options/', views.get_address_options, name='get_address_options'), 
    path('get-regions/', views.get_regions, name='get-regions'),
    path('status/', views.status, name='status'),
]