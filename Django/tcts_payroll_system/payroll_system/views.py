import re
import base64
from datetime import datetime
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import OuterRef, Subquery, Count, Sum, Min, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm, ServiceForm, CustomerForm, VehicleForm, AdminEditProfileForm, PasswordChangingForm
from .models import Employee, Payroll, Attendance, History, Region, Province, City, Barangay, Service, Customer, Vehicle, Task 
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_protect  # Ensure CSRF protection

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
    
    latest_payroll_subquery = (
    Payroll.objects.filter(employee_id_fk=OuterRef('pk'))
    .order_by('-payment_date')
    .values('payroll_status')[:1]
    )
    
    employees_with_latest_payroll = Employee.objects.annotate(
    latest_payroll_status=Subquery(latest_payroll_subquery)
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

def employee_registration(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        
        if form.is_valid():
            # Save form data to session instead of database
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

def employee_picture(request):
    # Ensure we have form data in session
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
            
            # Get employee data from session
            employee_data = request.session['employee_form_data']
            
            # Convert date strings back to date objects
            for date_field in ['date_of_birth', 'date_of_employment']:
                if date_field in employee_data and employee_data[date_field]:
                    employee_data[date_field] = parse_date(employee_data[date_field])
            
            # Create and save the employee with all data
            form = EmployeeForm(employee_data)
            
            if form.is_valid():
                employee = form.save(commit=False)
                employee.employee_image = image_file
                employee.save()
                
                # Create history entry
                History.objects.create(
                    description=f"Employee {employee.first_name} {employee.last_name} ({employee.employee_id}) was added."
                )
                
                # Clear session data
                del request.session['employee_form_data']
                
                messages.success(request, "Employee registered successfully!")
                return redirect('payroll_system:payroll_individual', employee_id=employee.employee_id)
            else:
                messages.error(request, "Error in form data. Please try again.")
                return redirect('payroll_system:employee_registration')
        else:
            messages.error(request, "No image was captured. Please take a picture.")
    
    return render(request, 'payroll_system/employee_picture.html')

# Helper function to parse date strings
def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()

@login_required
def employees(request):
    #new
    query = request.GET.get('q', '')

    # Get latest attendance for each employee using a subquery
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )

    # Get latest payroll status for each employee using a subquery
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
        'query': query #new
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    
    # Handle add attendance form submission
    if request.method == 'POST' and 'add_attendance' in request.POST:
        date = request.POST.get('date')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out') or None  # Handle empty time_out
        
        try:
            attendance = Attendance(
                employee_id_fk=employee,
                date=date,
                time_in=time_in,
                time_out=time_out
            )
            attendance.save()
            
            if time_out:  # Calculate hours if time_out is provided
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance added successfully!')
            return redirect('payroll_system:employee_profile', employee_id=employee_id)
        except Exception as e:
            messages.error(request, f'Error adding attendance: {str(e)}')
    
    # Handle edit attendance form submission
    if request.method == 'POST' and 'edit_attendance' in request.POST:
        attendance_id = request.POST.get('attendance_id')
        
        try:
            # Convert to integer to avoid issues 
            attendance_id = int(attendance_id)
            date = request.POST.get('date')
            time_in = request.POST.get('time_in')
            time_out = request.POST.get('time_out') or None

            attendance = get_object_or_404(Attendance, attendance_id=attendance_id, employee_id_fk=employee)
            attendance.date = date
            attendance.time_in = time_in
            attendance.time_out = time_out
            attendance.save()
            
            if time_out:
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')
        
        return redirect('payroll_system:employee_profile', employee_id=employee_id)
    
    employee.update_attendance_stats()
    employee.refresh_from_db()
    
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
    
    #new
    query = request.GET.get('q', '')
    
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee_id_fk=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )
    
    # Get the latest payroll for each employee using a subquery (new)
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
    
    # Total Employees
    total_employees = employees.count()
    
    # Count employees with different payroll statuses
    processed_payroll_count = employees.filter(latest_payroll_status='PROCESSED').count()
    pending_payroll_count = employees.filter(latest_payroll_status='PENDING').count()
    
    # Get payroll data for each employee
    employee_data = []
    try: 
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
    except:
        pass
    
    #new (end)

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

    # Count employees by their latest payroll status
    employees_with_latest_payroll = Employee.objects.annotate(latest_payroll_status=Subquery(latest_payroll_subquery))

    processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()

    pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
    #(new end)

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
    try:
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
            'employee': employee,
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
            'query': query,
        }
    except:
        context = {
            'processed_payroll_count': processed_payroll_count,
            'pending_payroll_count': pending_payroll_count,
            'total_payroll': total_payroll,  # Total payroll amount
            'previous_total_payroll': previous_total_payroll,
            'payroll_percentage': payroll_percentage,
            'next_payday': next_payday,  # Next payday date
            'previous_avg_rate': previous_avg_rate,
            'rate_percentage': rate_percentage,
            'avg_rate': current_avg_rate,
            'query': query,
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
    employee.active_status = Employee.ActiveStatus.INACTIVE
    if latest_time_log and latest_time_log.time_in and not latest_time_log.time_out:
        employee.active_status = Employee.ActiveStatus.ACTIVE

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
    # Store selected service in session
    service_id = request.GET.get('service_id')
    if service_id:
        request.session['selected_service_id'] = service_id
    
    # Forms for customer and vehicle
    customer_form = CustomerForm()
    vehicle_form = VehicleForm()

    # Get all necessary data for the template
    regions = list(Region.objects.all().values('regDesc', 'regCode'))
    customers = Customer.objects.all()
    
    context = {
        'customer_form': customer_form,
        'vehicle_form': vehicle_form,
        'regions': regions,
        'customers': customers,
    }
    
    return render(request, 'payroll_system/services_client.html', context)

# API endpoint to get customer details and vehicles
@login_required
def get_customer_details(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
        vehicles = Vehicle.objects.filter(customer=customer)

        # Prepare response data - simplify this to match the expected format
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

        return JsonResponse({
            'success': True,
            'customer': customer_data,
            'vehicles': vehicles_data
        })

    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Customer not found'
        })

    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Customer not found'
        })

@login_required
def services_assign(request):
    if request.method == 'POST':
        if 'assigned_employee' in request.POST:
            # This is the employee assignment form submission
            employee_id = request.POST.get('assigned_employee')
            
            # Get stored data from session
            service_id = request.session.get('selected_service_id')
            customer_id = request.session.get('customer_id')
            vehicle_id = request.session.get('vehicle_id')
            
            if service_id and customer_id and vehicle_id and employee_id:
                # Get the objects
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
                    # Duplicate task found - send error message
                    messages.error(request, f"This vehicle already has an active '{service.title}' service in progress.")
                    # Return to the assignment page with the error
                    return render(request, 'payroll_system/services_assign.html', {
                        'employees': Employee.objects.all(),
                        'customer': customer,
                        'vehicle': vehicle,
                        'duplicate_error': True
                    })
                
                # No duplicate - create the task
                task = Task(
                    task_name=f"{service.title} for {customer.first_name} {customer.last_name}",
                    service=service,
                    customer=customer,
                    vehicle=vehicle,
                    employee=employee
                )
                task.save()
                
                # Check if there are additional vehicles to process
                additional_vehicle_ids = request.session.get('additional_vehicle_ids', [])
                for add_vehicle_id in additional_vehicle_ids:
                    add_vehicle = Vehicle.objects.get(pk=add_vehicle_id)
                    
                    # Check for duplicate task on additional vehicle
                    existing_additional_task = Task.objects.filter(
                        service=service,
                        vehicle=add_vehicle,
                        task_status=Task.TaskStatus.IN_PROGRESS
                    ).exists()
                    
                    if not existing_additional_task:  # Only create if no duplicate
                        add_task = Task(
                            task_name=f"{service.title} for {customer.first_name} {customer.last_name} - Additional Vehicle",
                            service=service,
                            customer=customer,
                            vehicle=add_vehicle,
                            employee=employee
                        )
                        add_task.save()
                
                # Clear session data
                for key in ['selected_service_id', 'customer_id', 'vehicle_id', 'additional_vehicle_ids']:
                    if key in request.session:
                        del request.session[key]
                
                return redirect('payroll_system:status')
                
        else:
            # This is the customer and vehicle form submission from services_client
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
                    
                    # Process any additional vehicles - code remains the same
                    additional_vehicle_ids = []
                    i = 1
                    while f'additional_vehicle_name_{i}' in request.POST:
                        vehicle_name = request.POST.get(f'additional_vehicle_name_{i}')
                        vehicle_color = request.POST.get(f'additional_vehicle_color_{i}')
                        plate_number = request.POST.get(f'additional_plate_number_{i}')
                        
                        # Create and save the additional vehicle
                        new_vehicle = Vehicle(
                            customer=customer,
                            vehicle_name=vehicle_name,
                            vehicle_color=vehicle_color,
                            plate_number=plate_number
                        )
                        new_vehicle.save()
                        additional_vehicle_ids.append(new_vehicle.vehicle_id)
                        i += 1
                    
                    # Store additional vehicle IDs in session
                    if additional_vehicle_ids:
                        request.session['additional_vehicle_ids'] = additional_vehicle_ids
                    
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
                        
                        # Process any additional vehicles
                        additional_vehicle_ids = []
                        i = 1
                        while f'additional_vehicle_name_{i}' in request.POST:
                            vehicle_name = request.POST.get(f'additional_vehicle_name_{i}')
                            vehicle_color = request.POST.get(f'additional_vehicle_color_{i}')
                            plate_number = request.POST.get(f'additional_plate_number_{i}')
                            
                            # Create and save the additional vehicle
                            new_vehicle = Vehicle(
                                customer=customer,
                                vehicle_name=vehicle_name,
                                vehicle_color=vehicle_color,
                                plate_number=plate_number
                            )
                            new_vehicle.save()
                            additional_vehicle_ids.append(new_vehicle.vehicle_id)
                            i += 1
                        
                        # Store additional vehicle IDs in session
                        if additional_vehicle_ids:
                            request.session['additional_vehicle_ids'] = additional_vehicle_ids
                        
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
                        'regions': regions,  # Add regions data back
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
    # Get all tasks for display
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
def settings(request):
    return render(request, 'payroll_system/settings.html')

class AdminEditView(LoginRequiredMixin, generic.UpdateView):
    form_class = AdminEditProfileForm
    template_name = 'payroll_system/admin_edit_profile.html'
    success_url = reverse_lazy('payroll_system:settings')

    def get_object(self):
        return self.request.user
    
class PasswordsChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = PasswordChangingForm
    success_url = reverse_lazy('payroll_system:settings')

@login_required
def about(request):
    return render(request, 'payroll_system/about.html')

@login_required
def print(request):
    # Get all employees with prefetched payroll data for efficiency
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    
    # Handle search query
    query = request.GET.get('q', '')
    
    if query:
        employees = employees.filter(
            first_name__icontains=query
        ) | employees.filter(
            last_name__icontains=query
        ) | employees.filter(
            employee_id__icontains=query
        )
    
    # Total Employees
    total_employees = employees.count()
    
    # Get current date and time periods
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    # Calculate active employees per day
    active_employees_per_day = (
        Attendance.objects.filter(date__range=[start_of_week, end_of_week])
        .values('date')
        .annotate(active_count=Count('employee_id_fk', distinct=True))
    )

    # Calculate average active employees
    total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    days_counted = len(active_employees_per_day) or 1
    avg_active_employees = total_active_counts / days_counted

    # Prepare employee data with latest payroll information
    employee_data = []
    processed_count = 0
    pending_count = 0
    
    for employee in employees:
        latest_payroll = employee.payrolls.order_by('-payment_date').first()
        
        # Calculate salary based on attendance count if payroll exists
        if latest_payroll:
            attendance_count = employee.attendances.count()
            latest_payroll.salary = latest_payroll.rate * attendance_count
            
            # Count processed and pending payrolls
            if latest_payroll.payroll_status == 'PROCESSED':
                processed_count += 1
            elif latest_payroll.payroll_status == 'PENDING':
                pending_count += 1
        
        employee_data.append({
            'employee': employee,
            'latest_payroll': latest_payroll
        })

    # Calculate financial metrics
    total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum'] or 0
    next_payday = Payroll.objects.filter(payment_date__gt=today).aggregate(Min('payment_date'))['payment_date__min']
    avg_rate = Payroll.objects.filter(rate__gt=0).aggregate(Avg('rate'))['rate__avg'] or 0
    
    # Calculate current and previous month metrics
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

    # Calculate percentage changes
    payroll_percentage = 0
    if previous_total_payroll > 0:
        payroll_percentage = ((current_total_payroll - previous_total_payroll) / previous_total_payroll) * 100

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

    # Context for template
    context = {
        'employees': employees,  # All employees for iteration
        'employee_data': employee_data,  # Employee data with latest payroll info
        'total_employees': total_employees,
        'avg_active_employees': round(avg_active_employees),
        'processed_payroll_count': processed_count,
        'pending_payroll_count': pending_count,
        'total_payroll': total_payroll,
        'previous_total_payroll': previous_total_payroll,
        'payroll_percentage': payroll_percentage,
        'next_payday': next_payday,
        'previous_avg_rate': previous_avg_rate,
        'rate_percentage': rate_percentage,
        'avg_rate': current_avg_rate,
        'query': query,
    }

    return render(request, 'payroll_system/print.html', context)

@login_required
@csrf_exempt 
def update_incentives(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        incentive_value = float(data.get('incentive', 0))
        action = data.get('action')
        employees = Payroll.objects.filter(payroll_status='PENDING')
        
        for emp in employees:
            try:
                # Get attendance count for the employee
                attendance = Attendance.objects.filter(employee_id_fk=emp.employee_id_fk).count()
            except Exception as e:
                print(f"Error fetching attendance for employee {emp.employee_id_fk}: {e}")
                attendance = 0  # Default to 0 if attendance retrieval fails
            
            # Calculate the base payment (rate x attendance)
            base_payment = emp.rate * attendance
            
            if action == 'add':
                # Update the incentives field by adding the new value
                new_incentives = emp.incentives + incentive_value
                
                # For the salary, we only add the new incentive_value to the current salary
                new_salary = emp.salary + incentive_value

                Payroll.objects.filter(pk=emp.payroll_id).update(
                    incentives=new_incentives,
                    salary=new_salary
                )
            elif action == 'subtract':
                # Keep incentives value unchanged when subtracting
                new_incentives = emp.incentives
                
                # For salary, simply subtract the incentive_value from the current salary
                new_salary = emp.salary - incentive_value

                Payroll.objects.filter(pk=emp.payroll_id).update(
                    incentives=new_incentives,
                    salary=new_salary
                )
                
        # Get updated values for the response
        first_emp = Payroll.objects.filter(payroll_status='PENDING').first()
        new_incentive = first_emp.incentives if first_emp else 0.0
        new_salary = first_emp.salary if first_emp else 0.0
        
        return JsonResponse({'success': True, 'new_incentive': str(new_incentive), 'new_salary': str(new_salary)})
    
    return JsonResponse({'success': False})

@login_required
@csrf_exempt
def update_incentives_individual(request, employee_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        incentive_value = float(data.get('incentive', 0))
        action = data.get('action')

        try:
            emp = Payroll.objects.get(employee_id_fk=employee_id, payroll_status='PENDING')
        except Payroll.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee payroll not found.'})

        try:
            attendance = Attendance.objects.filter(employee_id_fk=emp.employee_id_fk).count()
        except Exception as e:
            print(f"Error fetching attendance for employee {emp.employee_id_fk}: {e}")
            attendance = 0

        base_payment = emp.rate * attendance

        if action == 'add':
            new_incentives = emp.incentives + incentive_value
            new_salary = emp.salary + incentive_value
        elif action == 'subtract':
            new_incentives = emp.incentives
            new_salary = emp.salary - incentive_value
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action.'})

        Payroll.objects.filter(pk=emp.payroll_id).update(
            incentives=new_incentives,
            salary=new_salary
        )

        return JsonResponse({'success': True, 'new_incentive': str(new_incentives), 'new_salary': str(new_salary)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
