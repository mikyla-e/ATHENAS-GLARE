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
    # path('payrolls/confirm/', views.confirm_payroll, name='confirm_payroll'),
    path('payrolls/payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('payrolls/payroll_history/', views.payroll_history, name='payroll_history'),
    # path('payrolls/payroll_history/<int:employee_id>/', views.payroll_history, name='payroll_history'),
    # path('payrolls/payroll_edit/<int:employee_id>/', views.payroll_edit , name='payroll_edit'),
    path('services/', views.services, name='services'),
    path('services/services_add/', views.services_add, name='services_add'),
    path('services/services_client/', views.services_client, name='services_client'),
    path('services/services_assign/', views.services_assign, name='services_assign'),
    path('status/', views.status, name='status'),
    path('customers/', views.customers, name='customers'),
    path('customer_page/<int:customer_id>/', views.customer_page, name='customer_page'),
    path('customer_edit/<int:customer_id>/', views.customer_edit, name='customer_edit'),
    path('update-all-incentives/', views.update_all_incentives, name='update_all_incentives'),
    path('payroll/<str:employee_id>/update-incentives/', views.update_employee_incentives, name='update_employee_incentives'),
    # path('print/', views.print, name='print'),
    path('ajax/get-provinces/', views.get_provinces, name='get_provinces'),
    path('ajax/get-cities/', views.get_cities, name='get_cities'),
    path('ajax/get-barangays/', views.get_barangays, name='get_barangays'),
    path('ajax/customer/<int:customer_id>/', views.get_customer_details, name='get_customer_details'),
    # path('payroll/update-payday/', views.update_payday, name='update_payday'),
    path('api/attendance-stats/', views.get_attendance_stats, name='attendance_stats'),
]