from django.shortcuts import render, redirect
from django.db.models import Max, OuterRef, Subquery
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm
from .models import Employee, Payroll, Attendance
from .face_recognition_attendance import recognize_face
from django.utils import timezone

@csrf_protect  # Ensure CSRF protection
def time_in_out(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee-id", "").strip()  # Handle empty input

        if not employee_id:
            messages.error(request, "Employee ID cannot be empty.")
            return redirect("/payroll_system/time_in_out")  # Redirect to avoid resubmission issues

        try:
            employee = Employee.objects.get(employee_id=employee_id)
        except Employee.DoesNotExist:
            messages.error(request, "Employee ID not found.")
            return redirect("/payroll_system/time_in_out")

        # Start face recognition process
        message = recognize_face(employee_id)

        if "recorded" in message:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect("/payroll_system/time_in_out")  # Redirect after processing

    return render(request, "payroll_system/time_in_out.html")


@login_required
def dashboard(request):
    return render(request, 'payroll_system/dashboard.html')

@login_required
def employee_registration(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()  # This will save the file automatically
            return redirect('/payroll_system/employee_registration')
    else:
        form = EmployeeForm()

    return render(request, 'payroll_system/employee_registration.html', {'form': form})

@login_required

def employees(request):
    # Get the latest attendance for each employee using a subquery
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')  # The minus sign sorts by date descending (newest first)
        .values('date')[:1]  # Limit to 1 result
    )
    
    # Add the latest attendance date to each employee
    employees = (
        Employee.objects
        .prefetch_related('payrolls')
        .annotate(latest_attendance_date=Subquery(latest_attendance_subquery))
        .all()
    )
    
    context = {
        'employees': employees
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    
    # Update the attendance stats
    employee.update_attendance_stats()
    
     # Get latest attendance and calculate hours worked
    latest_attendance = employee.attendances.order_by('-date').first()
    if latest_attendance:
        latest_attendance.calculate_hours_worked()  # Ensure hours are updated
        
    latest_payroll = employee.payrolls.order_by('-payment_date').first()
    payroll_status = latest_payroll.payroll_status if latest_payroll else "No Payroll Data"
    
    context = {
        'employee': employee,
        'latest_attendance': latest_attendance,
        'payroll_status': payroll_status
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
def payroll_edit(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls').get(employee_id = employee_id)
    payroll = Payroll.objects.get(employee_id_fk=employee)
    if request.method == "POST":
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()
            return redirect('/payroll_system/payrolls')
    else:
        form = PayrollForm(instance=payroll)
    context = { 'employee': employee, 'form': form}
    return render(request, 'payroll_system/payroll_edit.html', context)

@login_required
def settings(request):
    return render(request, 'payroll_system/settings.html')
