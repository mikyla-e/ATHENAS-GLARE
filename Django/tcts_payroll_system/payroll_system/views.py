from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Max, OuterRef, Subquery
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm
from .models import Employee, Payroll, Attendance
from .face_recognition_attendance import recognize_face
from django.utils import timezone
from django.utils.timezone import now

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
            return redirect('payroll_system:payroll_individual', employee_id = employee.employee_id)
    else:
        form = EmployeeForm()

    return render(request, 'payroll_system/employee_registration.html', {'form': form})

@login_required
def employees(request):
    # Get the latest attendance for each employee using a subquery
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )
    
    # Get the latest payroll for each employee using a subquery
    latest_payroll_subquery = (
        Payroll.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-payment_date')  # Assuming there's a created_at or similar timestamp field
        .values('payroll_status')[:1]
    )
    
    # Add the latest attendance date and latest payroll status to each employee
    employees = (
        Employee.objects
        .annotate(
            latest_attendance_date=Subquery(latest_attendance_subquery),
            latest_payroll_status=Subquery(latest_payroll_subquery)
        )
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
    employee.refresh_from_db()

    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    
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
    employees = Employee.objects.all()
    
    # Create a list with employees and their latest payroll
    employee_data = []
    for employee in employees:
        latest_payroll = employee.payrolls.order_by('-payment_date').first()
        employee_data.append({
            'employee': employee,
            'latest_payroll': latest_payroll
        })
    
    context = {
        'employee_data': employee_data
    }
    return render(request, 'payroll_system/payroll.html', context)

@login_required
def payroll_individual(request, employee_id):
    employee = get_object_or_404(Employee.objects.prefetch_related('payrolls', 'attendances'), employee_id=employee_id)

    # Get latest payroll
    current_payroll = employee.payrolls.order_by('-payment_date').first()

    # Count attendance records
    attendance_count = employee.attendances.count()

    # Check attendance records for today's active status
    today = now().date()
    latest_time_log = Attendance.objects.filter(employee_id_fk=employee, date=today).order_by('-time_in').first()

    # Determine active status
    employee.active_status = False
    if latest_time_log and latest_time_log.time_in and not latest_time_log.time_out:
        employee.active_status = True

    # Save updated active_status in database
    employee.save(update_fields=['active_status'])

    return render(request, 'payroll_system/payroll_individual.html', {
        'employee': employee,
        'current_payroll': current_payroll,
        'attendance_count': attendance_count
    })


@login_required
def payroll_edit(request, employee_id):
    employee = Employee.objects.get(employee_id=employee_id)
    today = timezone.now().date()
    
    # Try to get an active payroll, or create a new one
    try:
        payroll = Payroll.objects.get(
            employee_id_fk=employee,
            payment_date__gte=today
        )
    except Payroll.DoesNotExist:
        # No active payroll - create a new one
        payroll = Payroll(employee_id_fk=employee)
        
        # Set payment date to one week from today
        payroll.payment_date = today + timezone.timedelta(days=7)
        
        # Copy data from the most recent payroll if it exists
        try:
            prev_payroll = Payroll.objects.filter(
                employee_id_fk=employee
            ).latest('payment_date')
            
            # Copy relevant fields
            payroll.rate = prev_payroll.rate
            payroll.incentives = prev_payroll.incentives
            # Add any other fields you need to copy
        except Payroll.DoesNotExist:
            # First payroll for this employee, use defaults
            pass
    
    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()
            return redirect('payroll_system:payroll_individual', employee_id=employee_id)
    else:
        form = PayrollForm(instance=payroll)

     # Get the latest payroll for display purposes
    latest_payroll = employee.payrolls.order_by('-payment_date').first()
    
    context = {
        'form': form,
        'employee': employee,
        'latest_payroll': latest_payroll
    }
    return render(request, 'payroll_system/payroll_edit.html', context)

@login_required
def settings(request):
    return render(request, 'payroll_system/settings.html')

@login_required
def about(request):
    return render(request, 'payroll_system/about.html')
