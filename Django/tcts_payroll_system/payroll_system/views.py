from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, OuterRef, Subquery, Count, Sum, Min, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm
from .face_recognition_attendance import recognize_face
from .models import Employee, Payroll, Attendance, History
from ph_geography.models import Region, Province, Municipality, Barangay

@csrf_protect  # Ensure CSRF protection
def time_in_out(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee-id", "").strip()  # Handle empty input

        if not employee_id:
            messages.error(request, "Employee ID cannot be empty.")
            return redirect("/payroll_system/time_in_out")

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
    
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )

    latest_payroll_subquery = (
        Payroll.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-payment_date')
        .values('rate')[:1]
    )

    # Total Employees
    total_employees = Employee.objects.count()

    # Get current week range (Monday to Sunday)
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of current week
    end_of_week = start_of_week + timedelta(days=6)  # Get Sunday of current week

    # Count unique active employees per day within the week
    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    # Calculate the average number of active employees within the week
    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1  # Avoid division by zero

    avg_active_employees = total_active_counts / days_counted
    
    # Payroll Status: Count employees with "Processed" payroll
    processed_payroll_count = (
        Employee.objects.filter(payrolls__payroll_status='PROCESSED')
        .distinct()
        .count()
    )

    # Payroll Status: Count employees with "Pending" payroll
    pending_payroll_count = (
        Employee.objects.filter(payrolls__payroll_status='PENDING')
        .distinct()
        .count()
    )
    
    # Calculate Total Payroll (Sum of all processed salaries)
    total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']
    
    if total_payroll is None:
        total_payroll = "No total payroll yet"
    
    # Add next payday calculation too
    today = now().date()
    next_payday = Payroll.objects.filter(payment_date__gt=today).aggregate(Min('payment_date'))['payment_date__min']

    # Modified: Get employees ordered by most recent time-in (attendance date)
    recent_employees = (
        Employee.objects
        .annotate(
            latest_attendance_date=Subquery(latest_attendance_subquery),
            latest_payroll=Subquery(latest_payroll_subquery)
        )
        .order_by('-latest_attendance_date', 'last_name')[:5] # Order by most recent attendance date
    )

    # Modified: Limit history to 7 rows instead of 8
    histories = History.objects.order_by('-date_time')[:7]

    for employee in recent_employees:
        employee.total_payment = (employee.latest_payroll or 0) * employee.attendances.count()
     
    context = { 
        'histories': histories,
        'employees': recent_employees,
        'total_employees': total_employees,
        'avg_active_employees': round(avg_active_employees),
        'processed_payroll_count': processed_payroll_count,
        'pending_payroll_count': pending_payroll_count,
        'total_payroll': total_payroll,
        'next_payday': next_payday,
    }
    return render(request, 'payroll_system/dashboard.html', context)

def get_location_data(request):
    """Single view to handle all location-related AJAX requests"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        location_type = request.GET.get('type')
        parent_id = request.GET.get('parent_id')
        
        logger.info(f"Request received: type={location_type}, parent_id={parent_id}")
        
        if location_type == 'provinces':
            data = list(Province.objects.filter(region_id=parent_id).values('id', 'name'))
        elif location_type == 'municipalities':
            data = list(Municipality.objects.filter(province_id=parent_id).values('id', 'name'))
        elif location_type == 'barangays':
            data = list(Barangay.objects.filter(municipality_id=parent_id).values('id', 'name'))
        else:
            data = []
        
        logger.info(f"Returning {len(data)} items")
        return JsonResponse(data, safe=False)
    
    except Exception as e:
        logger.error(f"Error in get_location_data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def employee_registration(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()

            History.objects.create(description=f"Employee {employee.first_name} {employee.last_name} ({employee.employee_id}) was added.")

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
        .order_by('-payment_date')
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
    # Get all employees with prefetched payroll data for efficiency
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()

    # Total Employees
    total_employees = employees.count()

    # Get current week range (Monday to Sunday)
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of current week
    end_of_week = start_of_week + timedelta(days=6)  # Get Sunday of current week
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    # Count unique active employees per day within the week
    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    # Calculate the average number of active employees within the week
    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1  # Avoid division by zero
    avg_active_employees = total_active_counts / days_counted

    # Payroll Status: Count employees with "Processed" payroll
    processed_payroll_count = (
        employees.filter(payrolls__payroll_status='PROCESSED')
        .distinct()
        .count()
    )

    # Payroll Status: Count employees with "Pending" payroll
    pending_payroll_count = (
        employees.filter(payrolls__payroll_status='PENDING')
        .distinct()
        .count()
    )

    # Calculate Total Payroll (Sum of all processed salaries)
    total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']

    if total_payroll is None:
        total_payroll = "No total payroll yet"

    # Get Next Payday (earliest upcoming payment date)
    next_payday = Payroll.objects.filter(payment_date__gt=today).aggregate(Min('payment_date'))['payment_date__min']

    # Calculate Average Rate of Employees
    avg_rate = Payroll.objects.filter(rate__gt=0).aggregate(Avg('rate'))['rate__avg']

    if avg_rate is None:
        avg_rate = "No rate data"
        
    # Calculate Total Payroll for current and previous month
    current_total_payroll = Payroll.objects.filter(
        payroll_status='PROCESSED',
        payment_date__gte=current_month_start,
        payment_date__lte=today
    ).aggregate(Sum('salary'))['salary__sum'] or 0

    previous_total_payroll = Payroll.objects.filter(
        payroll_status='PROCESSED',
        payment_date__gte=previous_month_start,
        payment_date__lte=previous_month_end
    ).aggregate(Sum('salary'))['salary__sum'] or 0

    # Calculate percentage change for total payroll
    payroll_percentage = 0
    if previous_total_payroll > 0:
        payroll_percentage = ((current_total_payroll - previous_total_payroll) / previous_total_payroll) * 100

    # Calculate Average Rate for current and previous month
    current_avg_rate = Payroll.objects.filter(
        rate__gt=0,
        payment_date__gte=current_month_start,
        payment_date__lte=today
    ).aggregate(Avg('rate'))['rate__avg'] or 0

    previous_avg_rate = Payroll.objects.filter(
        rate__gt=0,
        payment_date__gte=previous_month_start,
        payment_date__lte=previous_month_end
    ).aggregate(Avg('rate'))['rate__avg'] or 0

    # Calculate percentage change for average rate
    rate_percentage = 0
    if previous_avg_rate > 0:
        rate_percentage = ((current_avg_rate - previous_avg_rate) / previous_avg_rate) * 100

    # Create a list with employees and their latest payroll
    employee_data = []
    for employee in employees:
        latest_payroll = employee.payrolls.order_by('-payment_date').first()
        
        # Calculate salary based on attendance count
        if latest_payroll:
            attendance_count = employee.attendances.count()
            latest_payroll.salary = latest_payroll.rate * attendance_count
        
        employee_data.append({
            'employee': employee,
            'latest_payroll': latest_payroll
        })

    # Pass all data to the template
    context = {
        'employee_data': employee_data,  # List of employees with their latest payroll
        'total_employees': total_employees,
        'avg_active_employees': round(avg_active_employees),
        'processed_payroll_count': processed_payroll_count,
        'pending_payroll_count': pending_payroll_count,
        'total_payroll': total_payroll,  # Total payroll amount
        'previous_total_payroll': previous_total_payroll,
        'payroll_percentage': payroll_percentage,
        'next_payday': next_payday,  # Next payday date
        'previous_avg_rate': previous_avg_rate,
        'rate_percentage': rate_percentage,
        'avg_rate': current_avg_rate,
    }

    return render(request, 'payroll_system/payroll.html', context)

@login_required
def payroll_individual(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)

    current_payroll = employee.payrolls.order_by('-payment_date').first()

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

    # current_payroll.salary = current_payroll.rate * attendance_count

    return render(request, 'payroll_system/payroll_individual.html', {
        'employee': employee,
        'current_payroll': current_payroll,
        'attendance_count': attendance_count
    })


@login_required
def payroll_edit(request, employee_id):
    employee = Employee.objects.get(employee_id=employee_id)
    today = timezone.now().date()
    
    # Get an active payroll, or create a new one
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
            payroll.payroll_status = prev_payroll.payroll_status
        except Payroll.DoesNotExist:
            # First payroll for this employee, use defaults
            pass
    
    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()

            History.objects.create(description=f"Payroll for {employee.first_name} {employee.last_name} ({employee.employee_id}) was updated.")

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
