from datetime import datetime
from django.contrib.auth import  authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import OuterRef, Subquery, Count, Sum, Min, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollForm, ServiceForm, CustomerForm, VehicleForm, AdminEditProfileForm, PasswordChangingForm
from .models import Employee, Payroll, Attendance, History, Region, Province, City, Barangay, Service, Customer, Vehicle, Task 

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
        form = EmployeeForm(request.POST, request.FILES)
        
        if form.is_valid():
            employee = form.save()
            
            # Create history entry
            History.objects.create(
                description=f"Employee {employee.first_name} {employee.last_name} ({employee.employee_id}) was added."
            )
            return redirect('payroll_system:payroll_individual', employee_id=employee.employee_id)
    else:
        form = EmployeeForm()
    
    regions = list(Region.objects.all().values('regDesc', 'regCode'))
    
    context = {
        'form': form,
        'regions': regions,
    }

    return render(request, 'payroll_system/employee_registration.html', context)

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

    context = {
        'customer_form': customer_form,
        'vehicle_form': vehicle_form
    }
    
    return render(request, 'payroll_system/services_client.html', context)

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
                # Create the task
                service = Service.objects.get(pk=service_id)
                customer = Customer.objects.get(pk=customer_id)
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                
                task = Task(
                    task_name=f"{service.title} for {customer.first_name} {customer.last_name}",
                    service=service,
                    customer=customer,
                    vehicle=vehicle,
                    # Assuming you have an Employee model with employee_id as primary key
                    employee=Employee.objects.get(pk=employee_id)
                )
                task.save()
                
                # Clear session data
                for key in ['selected_service_id', 'customer_id', 'vehicle_id']:
                    if key in request.session:
                        del request.session[key]
                
                return redirect('payroll_system:status')
                
        else:
            # This is the customer and vehicle form submission from services_client
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
                return render(request, 'payroll_system/services_assign.html', {
                    'employees': employees
                })
            else:
                # If form validation fails, go back to the customer form with errors
                return render(request, 'payroll_system/services_client.html', {
                    'customer_form': customer_form,
                    'vehicle_form': vehicle_form
                })
    
    # If this is a GET request, get employees to display
    employees = Employee.objects.all()
    return render(request, 'payroll_system/services_assign.html', {
        'employees': employees
    })

@login_required
def status(request):
    # Get all tasks for display
    tasks = Task.objects.all().order_by('-created_at')
    context = {
        'tasks': tasks
    }
    return render(request, 'payroll_system/status.html')

@login_required
def customers(request):
    return render(request, 'payroll_system/customers.html')

@login_required
def customer_page(request):
    return render(request, 'payroll_system/customer_page.html')

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
def logout_user(request):
    logout(request)
    message.success(request, ("You Were Logout!"))
    return redirect('users')