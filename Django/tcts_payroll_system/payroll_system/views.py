import re
import base64
from datetime import datetime
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, Count, Sum, Min, Avg
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm, ServiceForm, CustomerForm, CustomerEditForm, VehicleForm
from .models import Employee, Payroll, Attendance, History, Region, Province, City, Barangay, Service, Customer, Vehicle, Task 
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_POST

@csrf_protect  # Ensure CSRF protection

@login_required
def dashboard(request):
    
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )

    latest_payroll_status_subquery = (
        Payroll.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-payment_date')
        .values('payroll_status')[:1]
    )
    
    latest_payroll_rate_subquery = (
        Payroll.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-payment_date')
        .values('salary')[:1]
    )

    total_employees = Employee.objects.count()

    # Get current week range (Monday to Sunday)
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of current week
    end_of_week = start_of_week + timedelta(days=6)  # Get Sunday of current week

    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    # Calculate the average number of active employees within the week
    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1  # Avoid division by zero

    avg_active_employees = total_active_counts / days_counted
    
    employees_with_latest_payroll = Employee.objects.annotate(
        latest_payroll_status=Subquery(latest_payroll_status_subquery)
    )
    
    processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()
    
    pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
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
            latest_payroll_status=Subquery(latest_payroll_status_subquery),
            latest_payroll_rate=Subquery(latest_payroll_rate_subquery)
        )
        .order_by('-latest_attendance_date', 'last_name')[:5] # Order by most recent attendance date
    )

    histories = History.objects.order_by('-date_time')

    # Calculate the total payment correctly using the rate/salary
    for employee in recent_employees:
        if employee.latest_payroll_rate:
            employee.total_payment = f"₱{employee.latest_payroll_rate:.2f}"
        else:
            employee.total_payment = "₱0.00"
     
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

def get_provinces(request):
    region_code = request.GET.get('region')
    provinces = list(Province.objects.filter(regCode=region_code).values('provDesc', 'provCode'))
    return JsonResponse({'provinces': provinces})

def get_cities(request):
    prov_code = request.GET.get('province')
    cities = list(City.objects.filter(provCode=prov_code).values('citymunDesc', 'citymunCode'))
    return JsonResponse({'cities': cities})

def get_barangays(request):
    city_code = request.GET.get('city')
    barangays = list(Barangay.objects.filter(citymunCode=city_code).values('brgyDesc', 'brgyCode'))
    return JsonResponse({'barangays': barangays})

@login_required
def employee_registration(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        
        if form.is_valid():
            request.session['employee_form_data'] = form.cleaned_data
            
            # Convert date objects to strings for session storage
            for key, value in request.session['employee_form_data'].items():
                if hasattr(value, 'isoformat'):  # For date objects
                    request.session['employee_form_data'][key] = value.isoformat()
            
            return redirect('payroll_system:employee_picture')
    else:
        form = EmployeeForm()
    
    regions = list(Region.objects.all().values('regDesc', 'regCode'))
    
    context = {
        'form': form,
        'regions': regions,
    }

    return render(request, 'payroll_system/employee_registration.html', context)

def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()

@login_required
def employee_picture(request):
    if 'employee_form_data' not in request.session:
        messages.error(request, "Please fill out employee details first")
        return redirect('payroll_system:employee_registration')
    
    if request.method == "POST":
        image_data = request.POST.get('image_data')
        
        if image_data:
            # Extract the base64 encoded image data
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Create a ContentFile from the base64 data
            image_file = ContentFile(base64.b64decode(imgstr), name=f'employee_image.{ext}')
            
            employee_data = request.session['employee_form_data']
            
            for date_field in ['date_of_birth', 'date_of_employment']:
                if date_field in employee_data and employee_data[date_field]:
                    employee_data[date_field] = parse_date(employee_data[date_field])
            
            form = EmployeeForm(employee_data)
            
            if form.is_valid():
                employee = form.save(commit=False)
                employee.employee_image = image_file
                employee.save()
                
                History.objects.create(
                    description=f"Employee {employee.first_name} {employee.last_name} ({employee.employee_id}) was added."
                )
                
                del request.session['employee_form_data']
                
                messages.success(request, "Employee registered successfully!")
                return redirect('payroll_system:payroll_individual', employee_id=employee.employee_id)
            else:
                messages.error(request, "Error in form data. Please try again.")
                return redirect('payroll_system:employee_registration')
        else:
            messages.error(request, "No image was captured. Please take a picture.")
    
    return render(request, 'payroll_system/employee_picture.html')

@login_required
def employees(request):
    #new
    query = request.GET.get('q', '')

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
        .values('payroll_status')[:1]
    )

    # Base QuerySet with annotations
    employees = Employee.objects.annotate(
        latest_attendance_date=Subquery(latest_attendance_subquery),
        latest_payroll_status=Subquery(latest_payroll_subquery)
    )

    # Apply search filter if query exists
    if query:
        employees = employees.filter(
            first_name__icontains=query
        ) | employees.filter(
            last_name__icontains=query
        ) | employees.filter(
            employee_id__icontains=query
        )

    # Handle AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  
        data = list(employees.values('first_name', 'last_name', 'employee_id', 'contact_number', 'employee_status', 'latest_payroll_status', 'latest_attendance_date'))
        return JsonResponse({'employees': data})
    
    context = {
        'employees': employees,
        'query': query
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    
    if request.method == 'POST' and 'add_attendance' in request.POST:
        date = request.POST.get('date')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out') or None  
        
        try:
            # Create attendance object but don't save yet
            attendance = Attendance(employee_id_fk=employee, date=date, time_in=time_in, time_out=time_out)
            
            # This will run the clean method and validate work hours
            attendance.save()
            
            if time_out:  
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance added successfully!')
            return redirect('payroll_system:employee_profile', employee_id=employee_id)
        except ValidationError as e:
            # Handle validation errors explicitly
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error adding attendance: {str(e)}')
    
    if request.method == 'POST' and 'edit_attendance' in request.POST:
        attendance_id = request.POST.get('attendance_id')
        
        try:
            attendance_id = int(attendance_id)
            date = request.POST.get('date')
            time_in = request.POST.get('time_in')
            time_out = request.POST.get('time_out') or None

            attendance = get_object_or_404(Attendance, attendance_id=attendance_id, employee_id_fk=employee)
            attendance.date = date
            attendance.time_in = time_in
            attendance.time_out = time_out
            
            # This will run validation through clean() method
            attendance.save()
            
            if time_out:
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance updated successfully!')
        except ValidationError as e:
            # Handle validation errors explicitly
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')
        
        return redirect('payroll_system:employee_profile', employee_id=employee_id)
    
    employee.update_attendance_stats()
    employee.refresh_from_db()
    
    # Get latest attendance and calculate hours worked
    latest_attendance = employee.attendances.order_by('-date').first()
    if latest_attendance:
        latest_attendance.calculate_hours_worked()  

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
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    
    query = request.GET.get('q', '')
    
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
        .values('payroll_status')[:1]
    )
    
    employees = Employee.objects.annotate(
        latest_attendance_date=Subquery(latest_attendance_subquery),
        latest_payroll_status=Subquery(latest_payroll_subquery)
    )
    
    if query:
        employees = employees.filter(
            first_name__icontains=query
        ) | employees.filter(
            last_name__icontains=query
        ) | employees.filter(
            employee_id__icontains=query
        )
    
    total_employees = employees.count()
    
    # Count employees with different payroll statuses
    processed_payroll_count = employees.filter(latest_payroll_status='PROCESSED').count()
    pending_payroll_count = employees.filter(latest_payroll_status='PENDING').count()
    
    # Calculate the next Saturday for the payday
    today = now().date()
    days_until_saturday = (5 - today.weekday()) % 7  # 5 is Saturday
    next_saturday = today + timedelta(days=days_until_saturday)
    
    # Get the start and end of the current week (Monday to Sunday)
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
    # Get payroll data for each employee with calculated salary
    employee_data = []
    try:
        for employee in employees:
            latest_payroll = employee.payrolls.order_by('-payment_date').first()
            
            if latest_payroll:
                # Count attendance for the current week
                weekly_attendance_count = Attendance.objects.filter(
                    employee_id_fk=employee,
                    date__range=[start_of_week, end_of_week],
                    attendance_status='Present'
                ).count()
                
                # Calculate salary using the model method
                latest_payroll.calculate_salary(weekly_attendance_count)
                latest_payroll.save()  # Save the updated salary
            
            employee_data.append({
                'employee': employee,
                'latest_payroll': latest_payroll
            })
    except Exception as e:
        print(f"Error processing employee data: {e}")
    
    # Calculate statistics for the dashboard
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1  # Avoid division by zero
    avg_active_employees = total_active_counts / days_counted

    employees_with_latest_payroll = Employee.objects.annotate(latest_payroll_status=Subquery(latest_payroll_subquery))

    processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()
    pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
    # Calculate Total Payroll (Sum of all processed salaries)
    total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']

    if total_payroll is None:
        total_payroll = "No total payroll yet"

    # Get the earliest payment_date from PENDING payrolls
    next_payday = Payroll.objects.filter(payroll_status='PENDING').aggregate(Min('payment_date'))['payment_date__min']

    if next_payday:
        formatted_payday = next_payday.strftime('%m/%d/%Y')
        day_of_week = next_payday.strftime('%a').upper()
        current_payday = f"{formatted_payday}, {day_of_week}"
    else:
        current_payday = "XX/XX/XXXX, SAT"


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

    rate_percentage = 0
    if previous_avg_rate > 0:
        rate_percentage = ((current_avg_rate - previous_avg_rate) / previous_avg_rate) * 100

    # Format the next payday for display
    formatted_payday = next_payday.strftime('%m/%d/%Y')
    day_of_week = next_payday.strftime('%a').upper()
    formatted_payday_display = f"{formatted_payday}, {day_of_week}"
    current_payday = formatted_payday_display

    # Pass all data to the template
    try:
        context = {
            'employee_data': employee_data,
            'total_employees': total_employees,
            'avg_active_employees': round(avg_active_employees),
            'processed_payroll_count': processed_payroll_count,
            'pending_payroll_count': pending_payroll_count,
            'total_payroll': total_payroll,  
            'previous_total_payroll': previous_total_payroll,
            'payroll_percentage': payroll_percentage,
            'next_payday': next_payday,  
            'formatted_payday': formatted_payday_display,
            'current_payday': current_payday,
            'previous_avg_rate': previous_avg_rate,
            'rate_percentage': rate_percentage,
            'avg_rate': current_avg_rate,
            'query': query,
        }
    except Exception as e:
        print(f"Error creating context: {e}")
        context = {
            'processed_payroll_count': processed_payroll_count,
            'pending_payroll_count': pending_payroll_count,
            'total_payroll': total_payroll,  
            'previous_total_payroll': previous_total_payroll,
            'payroll_percentage': payroll_percentage,
            'next_payday': next_payday,
            'formatted_payday': formatted_payday_display,
            'previous_avg_rate': previous_avg_rate,
            'rate_percentage': rate_percentage,
            'avg_rate': current_avg_rate,
            'query': query,
        }

    return render(request, 'payroll_system/payroll.html', context)

@login_required
def payroll_history(request):
    return render(request, 'payroll_system/payroll_history.html')

@login_required
def update_all_incentives(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        amount = request.POST.get('amount')
        
        try:
            amount = float(amount)
            
            # Get all employees
            employees = Employee.objects.all()
            
            # For each employee, get their most recent payroll
            for employee in employees:
                latest_payroll = employee.payrolls.order_by('-payment_date').first()
                
                if latest_payroll:
                    current_incentives = latest_payroll.incentives or 0  # Handle None values
                    
                    if action == 'add':
                        # Add to incentives
                        latest_payroll.incentives = current_incentives + amount
                    elif action == 'subtract':
                        # Subtract from incentives (ensure it doesn't go below zero)
                        latest_payroll.incentives = max(0, current_incentives - amount)
                    
                    latest_payroll.save()
            
            messages.success(request, f'Successfully updated incentives for all employees!')
        except ValueError:
            messages.error(request, 'Please enter a valid number for amount')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('payroll_system:payrolls')

@login_required
def update_employee_incentives(request, employee_id):
    """Update incentives for a specific employee."""
    if request.method == 'POST':
        action = request.POST.get('action')
        amount_str = request.POST.get('amount')
        
        try:
            # Get the employee
            employee = Employee.objects.get(employee_id=employee_id)
            
            # Get the most recent payroll for this employee
            current_payroll = employee.payrolls.order_by('-payment_date').first()
            
            if not current_payroll:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'No payroll record exists for this employee.'
                    })
                else:
                    messages.error(request, 'No payroll record exists for this employee.')
                    return redirect('payroll_system:payroll_individual', employee_id=employee_id)
            
            # Convert amount to float
            amount = float(amount_str)
            
            # Update incentives based on action
            current_incentives = current_payroll.incentives or 0  # Handle None values
            
            if action == 'add':
                current_payroll.incentives = current_incentives + amount
            elif action == 'subtract':
                # Ensure we don't go below zero
                current_payroll.incentives = max(0, current_incentives - amount)
            
            # Recalculate salary with updated incentives
            # Get the attendance count
            today = now().date()
            start_of_week = today - timedelta(days=today.weekday())  # Monday
            end_of_week = start_of_week + timedelta(days=6)  # Sunday
            
            weekly_attendance_count = Attendance.objects.filter(
                employee_id_fk=employee,
                date__range=[start_of_week, end_of_week],
                attendance_status='Present'
            ).count()
            
            current_payroll.calculate_salary(weekly_attendance_count)
            current_payroll.save()
            
            # Format the values for display
            formatted_incentives = "{:.2f}".format(current_payroll.incentives)
            formatted_salary = "{:.2f}".format(current_payroll.salary)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return JSON response for AJAX request
                return JsonResponse({
                    'success': True,
                    'new_incentives': formatted_incentives,
                    'new_salary': formatted_salary
                })
            else:
                # Regular form submission
                messages.success(
                    request, 
                    f'Successfully {"added to" if action == "add" else "subtracted from"} incentives for {employee.first_name} {employee.last_name}.'
                )
                return redirect('payroll_system:payroll_individual', employee_id=employee_id)
                
        except Employee.DoesNotExist:
            error_msg = 'Employee not found.'
        except ValueError:
            error_msg = 'Please enter a valid number for amount.'
        except Exception as e:
            error_msg = f'An error occurred: {str(e)}'
        
        # Handle errors
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        else:
            messages.error(request, error_msg)
            return redirect('payroll_system:payroll_individual', employee_id=employee_id)
    
    # If not POST, redirect back to the payroll page
    return redirect('payroll_system:payroll_individual', employee_id=employee_id)

@login_required
def confirm_payroll(request):
    if request.method == 'POST':
        try:
            # Find all pending payrolls
            pending_payrolls = Payroll.objects.filter(payroll_status='PENDING')
            
            # Calculate the next payment date for the new payroll
            today = now().date()
            temp_payroll = Payroll()  # Temporary instance to use the method
            
            # Default to Saturday (5), but this could be configurable via settings or form
            payment_weekday = 5  # 0=Monday, 5=Saturday, 6=Sunday
            next_payment_date = temp_payroll.get_next_payment_date(today, payment_weekday)
            
            # Process all the pending payrolls first
            processed_payrolls = []
            for payroll in pending_payrolls:
                # Store the cash advance amount for later use
                cash_advance_amount = payroll.cash_advance
                employee = payroll.employee_id_fk
                
                # Update the payroll status to PROCESSED but keep the cash_advance value
                payroll.payroll_status = 'PROCESSED'
                payroll.save()
                
                # Store information needed for creating new payrolls
                processed_payrolls.append({
                    'employee': employee,
                    'rate': payroll.rate,
                    'cash_advance': cash_advance_amount
                })
            
            # Now create new payrolls with cash advance transferred to deductions
            for payroll_info in processed_payrolls:
                # Create a new payroll with the cash advance as deductions
                new_payroll = Payroll(
                    rate=payroll_info['rate'],  # Keep the same rate
                    incentives=0,  # Reset incentives
                    payroll_status='PENDING',  # Set status to PENDING
                    deductions=payroll_info['cash_advance'],  # Transfer cash advance to deductions
                    salary=0,  # Reset salary
                    cash_advance=0,  # Start with zero cash advance
                    payment_date=next_payment_date,  # Set payment date to next payment day
                    employee_id_fk=payroll_info['employee']  # Keep the same employee
                )
                new_payroll.save()
            
            # Log history
            History.objects.create(description=f"Payroll confirmed. Cash advances transferred to next payroll's deductions.")
            
            return redirect('payroll_system:payrolls')
        except Exception as e:
            messages.error(request, f'Error confirming payroll: {e}')
            # Return to payroll page with error message
            return redirect('payroll_system:payrolls')
    
    return redirect('payroll_system:payrolls')

@login_required
def payroll_individual(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    
    # Get current payroll (most recent)
    current_payroll = employee.payrolls.order_by('-payment_date').first()
    
    # Get payroll history (excluding current)
    payroll_history = employee.payrolls.order_by('-payment_date')[1:] if employee.payrolls.count() > 1 else []
    
    # Get the start and end of the current week (Monday to Saturday)
    today = now().date()
    # Find Monday of current week
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    # End of payroll week is Saturday (5 days after Monday)
    end_of_week = start_of_week + timedelta(days=5)  # Saturday
    
    # Get weekly attendance count for current payroll display
    weekly_attendance = Attendance.objects.filter(
        employee_id_fk=employee,
        date__range=[start_of_week, end_of_week],
        attendance_status='Present'
    ).values_list('date', flat=True).distinct().count()
    
    # Re-calculate the current payroll using the attendance count
    if current_payroll:
        current_payroll.calculate_salary(weekly_attendance)
        current_payroll.save()
    
    # Calculate attendance counts for each historical payroll
    for payroll in payroll_history:
        # Determine the payment period for this payroll
        payment_date = payroll.payment_date
        
        # Payment date is typically a Saturday, so subtract 5 days to get Monday
        start_date = payment_date - timedelta(days=5)  # Monday
        
        # Count attendance records within this payroll period
        payroll.attendance_count = Attendance.objects.filter(
            employee_id_fk=employee,
            date__range=[start_date, payment_date],
            attendance_status='Present'
        ).values_list('date', flat=True).distinct().count()
    
    # Check attendance records for today's active status
    latest_time_log = Attendance.objects.filter(employee_id_fk=employee, date=today).order_by('-time_in').first()
    
    # Determine active status
    employee.active_status = Employee.ActiveStatus.INACTIVE
    if latest_time_log and latest_time_log.time_in and not latest_time_log.time_out:
        employee.active_status = Employee.ActiveStatus.ACTIVE
    
    # Save updated active_status in database
    employee.save(update_fields=['active_status'])
    
    return render(request, 'payroll_system/payroll_individual.html', {
        'employee': employee,
        'current_payroll': current_payroll,
        'payroll_history': payroll_history,
        'attendance_count': weekly_attendance
    })

@login_required
def payroll_edit(request, employee_id):
    employee = Employee.objects.get(employee_id=employee_id)
    today = timezone.now().date()
    
    # Get an active pending payroll, or create a new one
    try:
        payroll = Payroll.objects.get(
            employee_id_fk=employee,
            payment_date__gte=today,
            payroll_status=Payroll.PayrollStatus.PENDING  # Only get PENDING payrolls
        )
    except Payroll.DoesNotExist:
        # If no pending payroll exists, try to get the most recent one as a starting point
        payroll = Payroll(employee_id_fk=employee)
        
        # Payment date will be set to next Saturday automatically in the save method
        
        # Copy data from the most recent payroll if it exists
        try:
            prev_payroll = Payroll.objects.filter(
                employee_id_fk=employee
            ).latest('payment_date')
            
            # Copy relevant fields
            payroll.rate = prev_payroll.rate
            payroll.incentives = prev_payroll.incentives
            payroll.payroll_status = Payroll.PayrollStatus.PENDING  
        except Payroll.DoesNotExist:
            # First payroll for this employee, use defaults
            pass
    except Payroll.MultipleObjectsReturned:
        # If multiple pending payrolls exist, get the most recent one
        payroll = Payroll.objects.filter(
            employee_id_fk=employee,
            payment_date__gte=today,
            payroll_status=Payroll.PayrollStatus.PENDING
        ).order_by('-payment_date').first()
    
    if request.method == 'POST':
        # Check if this is a cash advance submission
        if 'cash_advance' in request.POST and request.POST.get('number'):
            try:
                cash_amount = float(request.POST.get('number', 0))
                if cash_amount > 0:
                    payroll.cash_advance += cash_amount
                    payroll.save()
                    messages.success(request, f"Cash advance of ₱{cash_amount:,.2f} added successfully.")
                else:
                    messages.error(request, "Cash advance amount must be greater than zero.")
            except ValueError:
                messages.error(request, "Invalid cash advance amount.")
            
            return redirect('payroll_system:payroll_edit', employee_id=employee_id)
        # Check if this is a payment date change
        elif 'payment_date' in request.POST and request.POST.get('payment_date'):
            try:
                new_date = datetime.strptime(request.POST.get('payment_date'), '%Y-%m-%d').date()
                if new_date >= today:
                    payroll.payment_date = new_date
                    payroll.save()
                    messages.success(request, f"Payment date updated to {new_date.strftime('%Y-%m-%d')}.")
                else:
                    messages.error(request, "Payment date cannot be in the past.")
            except ValueError:
                messages.error(request, "Invalid date format.")
                
            return redirect('payroll_system:payroll_edit', employee_id=employee_id)
        else:
            # Regular payroll form submission
            form = PayrollForm(request.POST, instance=payroll)
            if form.is_valid():
                form.save()  # This will trigger the salary calculation in the model's save method
                
                # Log the history
                History.objects.create(description=f"Payroll for {employee.first_name} {employee.last_name} ({employee.employee_id}) was updated.")
                
                return redirect('payroll_system:payroll_individual', employee_id=employee_id)
    else:
        form = PayrollForm(instance=payroll)

    # Get the latest payroll for display purposes
    latest_payroll = employee.payrolls.order_by('-payment_date').first()
    
    # Get current week's Monday for context display
    current_weekday = payroll.payment_date.weekday()
    monday_of_week = payroll.payment_date - timedelta(days=current_weekday)
    sunday_of_week = monday_of_week + timedelta(days=6)
    
    context = {
        'form': form,
        'employee': employee,
        'latest_payroll': latest_payroll,
        'week_start': monday_of_week,
        'week_end': sunday_of_week,
        'today': today
    }
    return render(request, 'payroll_system/payroll_edit.html', context)

@login_required
def services(request):
    services = Service.objects.all()
    context = {
        'services': services
    }
    return render(request, 'payroll_system/services.html', context)

@login_required
def services_add(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('payroll_system:services')
    else:
        form = ServiceForm()
    
    context = {
        'form': form
    }
    return render(request, 'payroll_system/services_add.html', context)

@login_required
def services_client(request):
    response = None
    
    service_id = request.GET.get('service_id')
    if service_id:
        request.session['selected_service_id'] = service_id
    
    customer_form = CustomerForm()
    vehicle_form = VehicleForm()

    regions = list(Region.objects.all().values('regDesc', 'regCode'))
    customers = Customer.objects.all()
    
    context = {
        'customer_form': customer_form,
        'vehicle_form': vehicle_form,
        'regions': regions,
        'customers': customers,
        'should_clear_storage': True,
    }
    
    return render(request, 'payroll_system/services_client.html', context)

@login_required
def get_customer_details(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
        vehicles = Vehicle.objects.filter(customer=customer)

        customer_data = {
            'first_name': customer.first_name,
            'middle_name': customer.middle_name,
            'last_name': customer.last_name,
            'contact_number': customer.contact_number,
            'region': customer.region.regDesc if customer.region else '',
            'province': customer.province.provDesc if customer.province else '',
            'city': customer.city.citymunDesc if customer.city else '',
            'barangay': customer.barangay.brgyDesc if customer.barangay else '',
        }

        vehicles_data = [
            {
                'id': vehicle.vehicle_id,
                'vehicle_name': vehicle.vehicle_name,
                'vehicle_color': vehicle.vehicle_color,
                'plate_number': vehicle.plate_number,
            }
            for vehicle in vehicles
        ]

        return JsonResponse({'success': True, 'customer': customer_data, 'vehicles': vehicles_data})

    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer not found'})

    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer not found'})

@login_required
def services_assign(request):
    if request.method == 'POST':
        if 'assigned_employee' in request.POST:
            employee_id = request.POST.get('assigned_employee')
            
            # Get stored data from session
            service_id = request.session.get('selected_service_id')
            customer_id = request.session.get('customer_id')
            vehicle_id = request.session.get('vehicle_id')
            
            if service_id and customer_id and vehicle_id and employee_id:
                service = Service.objects.get(pk=service_id)
                customer = Customer.objects.get(pk=customer_id)
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                employee = Employee.objects.get(pk=employee_id)
                
                # Check for duplicate task (same service for same vehicle that's still in progress)
                existing_task = Task.objects.filter(
                    service=service, 
                    vehicle=vehicle,
                    task_status=Task.TaskStatus.IN_PROGRESS
                ).exists()
                
                if existing_task:
                    messages.error(request, f"This vehicle already has an active '{service.title}' service in progress.")
                    return render(request, 'payroll_system/services_assign.html', {
                        'employees': Employee.objects.all(),
                        'customer': customer,
                        'vehicle': vehicle,
                        'duplicate_error': True
                    })
                
                task = Task(
                    task_name=f"{service.title} for {customer.first_name} {customer.last_name}",
                    service=service,
                    customer=customer,
                    vehicle=vehicle,
                    employee=employee
                )
                task.save()
                
                # Clear ALL session data related to the form
                keys_to_clear = ['selected_service_id', 'customer_id', 'vehicle_id']
                for key in keys_to_clear:
                    if key in request.session:
                        del request.session[key]
                
                # Add response header to clear sessionStorage JavaScript values
                response = redirect('payroll_system:status')
                response.headers['X-Clear-Form-Storage'] = 'true'
                return response
                
        else:
            customer_id = request.POST.get('customer_id')
            
            if customer_id:
                # Existing customer flow
                customer = Customer.objects.get(pk=customer_id)
                
                # Check if user is selecting an existing vehicle
                existing_vehicle_id = request.POST.get('existing_vehicle_id')
                
                if existing_vehicle_id:
                    # Using an existing vehicle - bypass vehicle form validation completely
                    vehicle = Vehicle.objects.get(pk=existing_vehicle_id)
                    
                    # Store primary vehicle in session
                    request.session['customer_id'] = customer.customer_id
                    request.session['vehicle_id'] = vehicle.vehicle_id
                    
                    # Get employees to display for assignment
                    employees = Employee.objects.all()
                    
                    # Render the assign page with the primary vehicle
                    return render(request, 'payroll_system/services_assign.html', {
                        'employees': employees, 
                        'customer': customer, 
                        'vehicle': vehicle
                    })
                else:
                    # Process primary vehicle form for new vehicle
                    vehicle_form = VehicleForm(request.POST)
                    if vehicle_form.is_valid():
                        # Creating a new vehicle for existing customer
                        vehicle = vehicle_form.save(commit=False)
                        vehicle.customer = customer
                        vehicle.save()
                        
                        # Store primary vehicle in session
                        request.session['customer_id'] = customer.customer_id
                        request.session['vehicle_id'] = vehicle.vehicle_id
                        
                        # Get employees to display for assignment
                        employees = Employee.objects.all()
                        
                        # Render the assign page with the primary vehicle
                        return render(request, 'payroll_system/services_assign.html', {
                            'employees': employees, 
                            'customer': customer, 
                            'vehicle': vehicle
                        })
                    else:
                        # If form validation fails, go back with errors
                        customer_form = CustomerForm(instance=customer)
                        
                        # Get all necessary data for the template again
                        regions = list(Region.objects.all().values('regDesc', 'regCode'))
                        
                        return render(request, 'payroll_system/services_client.html', {
                            'customer_form': customer_form, 
                            'vehicle_form': vehicle_form,
                            'customers': Customer.objects.all(),
                            'regions': regions, 
                        })
            else:
                # New customer flow
                customer_form = CustomerForm(request.POST)
                vehicle_form = VehicleForm(request.POST)
                
                if customer_form.is_valid() and vehicle_form.is_valid():
                    # Save customer first
                    customer = customer_form.save()
                    
                    # Then save vehicle with customer reference
                    vehicle = vehicle_form.save(commit=False)
                    vehicle.customer = customer
                    vehicle.save()
                    
                    # Store data in session for next step
                    request.session['customer_id'] = customer.customer_id
                    request.session['vehicle_id'] = vehicle.vehicle_id
                    
                    # Get employees to display for assignment
                    employees = Employee.objects.all()
                    
                    # Add the customer and vehicle data to pass to the template
                    return render(request, 'payroll_system/services_assign.html', {
                        'employees': employees, 
                        'customer': customer, 
                        'vehicle': vehicle
                    })
                else:
                    # If form validation fails, go back to the customer form with errors
                    regions = list(Region.objects.all().values('regDesc', 'regCode'))
                    
                    return render(request, 'payroll_system/services_client.html', {
                        'customer_form': customer_form, 
                        'vehicle_form': vehicle_form,
                        'customers': Customer.objects.all(),
                        'regions': regions,
                    })
    
    # If this is a GET request, check if we have customer and vehicle in session
    employees = Employee.objects.all()
    context = {
        'employees': employees
    }
    
    # If this is a GET request or coming back to this page, try to get the customer and vehicle data
    customer_id = request.session.get('customer_id')
    vehicle_id = request.session.get('vehicle_id')
    
    if customer_id and vehicle_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
            vehicle = Vehicle.objects.get(pk=vehicle_id)
            context.update({
                'customer': customer,
                'vehicle': vehicle
            })
        except (Customer.DoesNotExist, Vehicle.DoesNotExist):
            # If the objects don't exist, simply don't add them to context
            pass
    
    return render(request, 'payroll_system/services_assign.html', context)

@login_required
def status(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        
        if task_id and task_id != 'undefined':
            task = get_object_or_404(Task, task_id=task_id)
            
            if 'incentives' in request.POST:
                amount = request.POST.get('number')
                if amount and float(amount) > 0:
                    payroll = Payroll.objects.filter(employee_id_fk=task.employee).latest('payment_date')
                    
                    payroll.incentives = payroll.incentives + float(amount)
                    payroll.save()
                    
                task.task_status = 'Completed'
                task.save()
                
                return redirect('payroll_system:status')
    
    tasks = Task.objects.all().order_by('-created_at')
    context = {
        'tasks': tasks
    }
    return render(request, 'payroll_system/status.html', context)

@login_required
def customers(request):
    customers = Customer.objects.all()
    context = {
        'customers': customers
    }
    return render(request, 'payroll_system/customers.html', context)

@login_required
def customer_page(request, customer_id):
    customer = Customer.objects.prefetch_related('vehicles').get(customer_id=customer_id)
    context = {
        'customer': customer
    }
    return render(request, 'payroll_system/customer_page.html', context)

@login_required
def customer_edit(request, customer_id):
    customer = get_object_or_404(Customer, customer_id=customer_id)
    
    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            # messages.success(request, "Customer information updated successfully.")
            return redirect('payroll_system:customer_page', customer_id=customer.customer_id)
    else:
        form = CustomerEditForm(instance=customer)
    
    # Get location data for dropdowns
    regions = Region.objects.all().values('regDesc', 'regCode')
    
    # Get related provinces, cities, and barangays based on selected values
    provinces = []
    cities = []
    barangays = []
    
    if customer.region:
        provinces = Province.objects.filter(regCode=customer.region.regCode).order_by('provDesc')
        
        if customer.province:
            cities = City.objects.filter(provCode=customer.province.provCode).order_by('citymunDesc')
            
            if customer.city:
                barangays = Barangay.objects.filter(citymunCode=customer.city.citymunCode).order_by('brgyDesc')
    
    context = {
        'form': form,
        'customer': customer,
        'regions': regions,
        'provinces': provinces,
        'cities': cities,
        'barangays': barangays,
    }
    
    return render(request, 'payroll_system/customer_edit.html', context)

@login_required
def print(request):
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    
    query = request.GET.get('q', '')
    
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
        .values('payroll_status')[:1]
    )
    
    employees = Employee.objects.annotate(
        latest_attendance_date=Subquery(latest_attendance_subquery),
        latest_payroll_status=Subquery(latest_payroll_subquery)
    )
    
    if query:
        employees = employees.filter(
            first_name__icontains=query
        ) | employees.filter(
            last_name__icontains=query
        ) | employees.filter(
            employee_id__icontains=query
        )
    
    total_employees = employees.count()
    
    # Count employees with different payroll statuses
    processed_payroll_count = employees.filter(latest_payroll_status='PROCESSED').count()
    pending_payroll_count = employees.filter(latest_payroll_status='PENDING').count()
    
    # Calculate the next Saturday for the payday
    today = now().date()
    days_until_saturday = (5 - today.weekday()) % 7  # 5 is Saturday
    next_saturday = today + timedelta(days=days_until_saturday)
    
    # Get the start and end of the current week (Monday to Sunday)
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
    # Get payroll data for each employee with calculated salary
    employee_data = []
    try:
        for employee in employees:
            latest_payroll = employee.payrolls.order_by('-payment_date').first()
            
            if latest_payroll:
                # Count attendance for the current week
                weekly_attendance_count = Attendance.objects.filter(
                    employee_id_fk=employee,
                    date__range=[start_of_week, end_of_week],
                    attendance_status='Present'
                ).count()
                
                # Calculate salary using the model method
                latest_payroll.calculate_salary(weekly_attendance_count)
                latest_payroll.save()  # Save the updated salary
            
            employee_data.append({
                'employee': employee,
                'latest_payroll': latest_payroll
            })
    except Exception as e:
        print(f"Error processing employee data: {e}")
    
    # Calculate statistics for the dashboard
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1  # Avoid division by zero
    avg_active_employees = total_active_counts / days_counted

    employees_with_latest_payroll = Employee.objects.annotate(latest_payroll_status=Subquery(latest_payroll_subquery))

    processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()
    pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
    # Calculate Total Payroll (Sum of all processed salaries)
    total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']

    if total_payroll is None:
        total_payroll = "No total payroll yet"

    # Get the earliest payment_date from PENDING payrolls
    next_payday = Payroll.objects.filter(payroll_status='PENDING').aggregate(Min('payment_date'))['payment_date__min']

    if next_payday:
        formatted_payday = next_payday.strftime('%m/%d/%Y')
        day_of_week = next_payday.strftime('%a').upper()
        current_payday = f"{formatted_payday}, {day_of_week}"
    else:
        current_payday = "XX/XX/XXXX, SAT"


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

    rate_percentage = 0
    if previous_avg_rate > 0:
        rate_percentage = ((current_avg_rate - previous_avg_rate) / previous_avg_rate) * 100

    # Format the next payday for display
    formatted_payday = next_payday.strftime('%m/%d/%Y')
    day_of_week = next_payday.strftime('%a').upper()
    formatted_payday_display = f"{formatted_payday}, {day_of_week}"
    current_payday = formatted_payday_display

    # Pass all data to the template
    try:
        context = {
            'employee_data': employee_data,
            'total_employees': total_employees,
            'avg_active_employees': round(avg_active_employees),
            'processed_payroll_count': processed_payroll_count,
            'pending_payroll_count': pending_payroll_count,
            'total_payroll': total_payroll,  
            'previous_total_payroll': previous_total_payroll,
            'payroll_percentage': payroll_percentage,
            'next_payday': next_payday,  
            'formatted_payday': formatted_payday_display,
            'current_payday': current_payday,
            'previous_avg_rate': previous_avg_rate,
            'rate_percentage': rate_percentage,
            'avg_rate': current_avg_rate,
            'query': query,
        }
    except Exception as e:
        print(f"Error creating context: {e}")
        context = {
            'processed_payroll_count': processed_payroll_count,
            'pending_payroll_count': pending_payroll_count,
            'total_payroll': total_payroll,  
            'previous_total_payroll': previous_total_payroll,
            'payroll_percentage': payroll_percentage,
            'next_payday': next_payday,
            'formatted_payday': formatted_payday_display,
            'previous_avg_rate': previous_avg_rate,
            'rate_percentage': rate_percentage,
            'avg_rate': current_avg_rate,
            'query': query,
        }

    return render(request, 'payroll_system/print.html', context)

@login_required
def update_payday(request):
    if request.method == 'POST' and request.POST.get('payday') == 'true':
        new_date = request.POST.get('date')
        if new_date:
            formatted_date = datetime.strptime(new_date, "%Y-%m-%d").date()
            Payroll.objects.filter(payroll_status='PENDING').update(payment_date=formatted_date)

            # Format for frontend display (e.g., "05/03/2025, SAT")
            formatted_display = formatted_date.strftime("%m/%d/%Y") + ", " + formatted_date.strftime("%a").upper()
            return JsonResponse({'success': True, 'updated_payday': formatted_display})
        return JsonResponse({'success': False, 'error': 'Invalid date'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})