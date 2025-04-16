from .views import AdminEditView, PasswordsChangeView
from django.contrib import admin
from django.urls import path
from . import views

app_name = 'payroll_system'

urlpatterns = [
    path('time_in_out/', views.time_in_out, name='time_in_out'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('employees/employee_registration/', views.employee_registration, name='employee_registration'),
    path('employees/', views.employees, name='employees'),
    path('employees/employee_profile/<int:employee_id>/', views.employee_profile, name='employee_profile'),
    path('payrolls/', views.payrolls, name='payrolls'),
    path('payrolls/payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('payrolls/payroll_edit/<int:employee_id>/', views.payroll_edit , name='payroll_edit'),
    path('services/', views.services, name='services'),
    path('services/services_add/', views.services_add, name='services_add'),
    path('services/services_client/', views.services_client, name='services_client'),
    path('services/services_vehicle/', views.services_vehicle, name='services_vehicle'),
    path('status/', views.status, name='status'),
    path('settings/', views.settings, name='settings'),
    path('admin_edit_profile/', AdminEditView.as_view(), name='admin_edit_profile'),
    path('password/', PasswordsChangeView.as_view(template_name='payroll_system/change_password.html')),
    path('about/', views.about, name='about'),
    path('get-address-options/', views.get_address_options, name='get_address_options'), 
    path('get-regions/', views.get_regions, name='get-regions'),
    path('customers/', views.customers, name='customers'),
]