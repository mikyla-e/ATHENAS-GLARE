from .views import AdminEditView, PasswordsChangeView
from django.contrib import admin
from django.urls import path
from . import views

app_name = 'payroll_system'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('employees/employee_registration/', views.employee_registration, name='employee_registration'),
    path('employees/employee_picture/', views.employee_picture, name='employee_picture'),
    path('employees/', views.employees, name='employees'),
    path('employees/employee_profile/<int:employee_id>/', views.employee_profile, name='employee_profile'),
    path('payrolls/', views.payrolls, name='payrolls'),
    path('payrolls/payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('payrolls/payroll_edit/<int:employee_id>/', views.payroll_edit , name='payroll_edit'),
    path('services/', views.services, name='services'),
    path('services/services_add/', views.services_add, name='services_add'),
    path('services/services_client/', views.services_client, name='services_client'),
    path('services/services_assign/', views.services_assign, name='services_assign'),
    path('status/', views.status, name='status'),
    path('settings/', views.settings, name='settings'),
    path('settings/admin_edit_profile/', AdminEditView.as_view(), name='admin_edit_profile'),
    path('settings/password/', PasswordsChangeView.as_view(template_name='payroll_system/change_password.html')),
    path('about/', views.about, name='about'),
    path('customers/', views.customers, name='customers'),
    path('customer_page/<int:customer_id>/', views.customer_page, name='customer_page'),
    path('ajax/get-provinces/', views.get_provinces, name='get_provinces'),
    path('ajax/get-cities/', views.get_cities, name='get_cities'),
    path('ajax/get-barangays/', views.get_barangays, name='get_barangays'),
    path('update-incentives/', views.update_incentives, name='update_incentives'),
    path('print/', views.print, name='print'),
]