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
    path('employees/employee_edit/<int:employee_id>/', views.employee_edit, name='employee_edit'),    
    path('create_payroll', views.create_payroll, name='create_payroll'),
    path('payrolls/payroll_record/', views.payroll_record, name='payroll_record'),
    path('payrolls/', views.payrolls, name='payrolls'),
    path('payrolls/payroll_individual/<int:employee_id>/', views.payroll_individual, name='payroll_individual'),
    path('payrolls/payroll_history/', views.payroll_history, name='payroll_history'),
    path('payroll/record/<int:payroll_record_id>/add-deduction/', views.add_individual_deduction, name='add_individual_deduction'),
    path('edit_deductions', views.edit_deductions, name='edit_deductions'),
    path('generate_payroll/<int:payroll_period_id>/', views.generate_payroll, name='generate_payroll'),
    path('update-all-incentives/', views.update_all_incentives, name='update_all_incentives'),
    path('payroll/<str:employee_id>/update-incentives/', views.update_employee_incentives, name='update_employee_incentives'),
    path('payroll/record/<int:record_id>/cash-advance/', views.add_cash_advance, name='add_cash_advance'),                  
    path('payroll/confirm/<int:payroll_period_id>/', views.confirm_payroll, name='confirm_payroll'),
    # path('payrolls/payroll_edit/<int:employee_id>/', views.payroll_edit , name='payroll_edit'),
    path('services/', views.services, name='services'),
    path('services/services_add/', views.services_add, name='services_add'),
    path('services/services_client/', views.services_client, name='services_client'),
    path('services/services_assign/', views.services_assign, name='services_assign'),
    path('status/', views.status, name='status'),
    path('customers/', views.customers, name='customers'),
    path('customer_page/<int:customer_id>/', views.customer_page, name='customer_page'),
    path('customer_edit/<int:customer_id>/', views.customer_edit, name='customer_edit'),
    # path('print/', views.print, name='print'),
    path('ajax/get-provinces/', views.get_provinces, name='get_provinces'),
    path('ajax/get-cities/', views.get_cities, name='get_cities'),
    path('ajax/get-barangays/', views.get_barangays, name='get_barangays'),
    path('ajax/customer/<int:customer_id>/', views.get_customer_details, name='get_customer_details'),
    # path('payroll/update-payday/', views.update_payday, name='update_payday'),
    path('api/payroll-by-week/', views.payroll_by_week, name='payroll_by_week'),
    path('payslip/', views.payslip, name='payslip'),
    #new - flores
    path('attendance/summary/', views.attendance_summary, name='attendance-summary'),
    path('api/payroll/chart-data/', views.payroll_chart_data, name='payroll_chart_data'),
]