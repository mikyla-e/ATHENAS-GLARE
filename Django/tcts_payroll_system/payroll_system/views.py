import base64
import calendar
from datetime import datetime, date as date_class
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, Sum, Min, Avg
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_protect
from .forms import EmployeeForm, PayrollPeriodForm, DeductionForm, ServiceForm, CustomerForm, CustomerEditForm, VehicleForm
from .models import Employee, Attendance, PayrollPeriod, Deduction, PayrollRecord, History, Region, Province, City, Barangay, Service, Customer, Vehicle, Task 

@csrf_protect  # Ensure CSRF protection

@login_required
def dashboard(request):
    
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )

    # latest_payroll_status_subquery = (
    #     Payroll.objects
    #     .filter(employee_id_fk=OuterRef('pk'))
    #     .order_by('-payment_date')
    #     .values('payroll_status')[:1]
    # )
    
    # latest_payroll_rate_subquery = (
    #     Payroll.objects
    #     .filter(employee_id_fk=OuterRef('pk'))
    #     .order_by('-payment_date')
    #     .values('salary')[:1]
    # )

    total_employees = Employee.objects.count()

    # Get current week range (Monday to Sunday)
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of current week
    end_of_week = start_of_week + timedelta(days=6)  # Get Sunday of current week
    
    # Count of unique active employees with at least one 'Present' attendance this week
    avg_active_employees = Attendance.objects.filter(
        date__range=[start_of_week, end_of_week],
        attendance_status=Attendance.AttendanceStatus.PRESENT,
        employee__is_active=True
    ).values('employee').distinct().count()


    # active_employees_per_day = (
    #     Attendance.objects.filter(date__range=[start_of_week, end_of_week])
    #     .values('date')
    #     .annotate(active_count=Count('employee', distinct=True))
    # )

    # # Calculate the average number of active employees within the week
    # total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
    # days_counted = len(active_employees_per_day) or 1  # Avoid division by zero

    # avg_active_employees = total_active_counts / days_counted
    
    # employees_with_latest_payroll = Employee.objects.annotate(
    #     latest_payroll_status=Subquery(latest_payroll_status_subquery)
    # )
    
    # processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()
    
    # pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
    # Calculate Total Payroll (Sum of all processed salaries)
    #total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']
    
    # if total_payroll is None:
    #     total_payroll = "No total payroll yet"
    
    # Add next payday calculation too
    today = now().date()
    # Count payroll periods grouped by status
    processed_payroll_count = PayrollPeriod.objects.filter(
        payroll_status=PayrollPeriod.PayrollStatus.PROCESSED
    ).count()

    pending_payroll_count = PayrollPeriod.objects.filter(
        payroll_status=PayrollPeriod.PayrollStatus.PENDING
    ).count()
    next_payday = PayrollPeriod.objects.filter(payment_date__gt=today).aggregate(Min('payment_date'))['payment_date__min']

    # Modified: Get employees ordered by most recent time-in (attendance date)
    # recent_employees = (
    #     Employee.objects
    #     .annotate(
    #         latest_attendance_date=Subquery(latest_attendance_subquery),
    #         latest_payroll_status=Subquery(latest_payroll_status_subquery),
    #         latest_payroll_rate=Subquery(latest_payroll_rate_subquery)
    #     )
    #     .order_by('-latest_attendance_date', 'last_name')[:5] # Order by most recent attendance date
    # )

    histories = History.objects.order_by('-date_time')

    # Calculate the total payment correctly using the rate/salary
    # for employee in recent_employees:
    #     if employee.latest_payroll_rate:
    #         employee.total_payment = f"₱{employee.latest_payroll_rate:.2f}"
    #     else:
    #         employee.total_payment = "₱0.00"
    
    #new
    payroll_totals = calculate_payroll_totals(request)
     
    context = { 
        'histories': histories,
        # 'employees': recent_employees,
        'total_employees': total_employees,
        'avg_active_employees': round(avg_active_employees),
        'processed_payroll_count': processed_payroll_count,
        'pending_payroll_count': pending_payroll_count,
        # 'total_payroll': total_payroll,
        'next_payday': next_payday,
        'total_payroll': payroll_totals.get('monthly_payroll', 0),  # Keep existing behavior for compatibility
        'weekly_payroll': payroll_totals.get('weekly_payroll', 0),
        'monthly_payroll': payroll_totals.get('monthly_payroll', 0),
        'yearly_payroll': payroll_totals.get('yearly_payroll', 0),
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
                return redirect('payroll_system:employee_profile', employee_id=employee.employee_id)
            else:
                messages.error(request, "Error in form data. Please try again.")
                return redirect('payroll_system:employee_registration')
        else:
            messages.error(request, "No image was captured. Please take a picture.")
    
    return render(request, 'payroll_system/employee_picture.html')
    

@login_required
def employees(request):
    
    latest_attendance_subquery = (
        Attendance.objects
        .filter(employee=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )

    # Base QuerySet with annotations
    employees = Employee.objects.annotate(
        latest_attendance_date=Subquery(latest_attendance_subquery)
    )
    
    context = {
        'employees': employees,
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('attendances').get(employee_id=employee_id)
    
    if request.method == 'POST' and 'add_attendance' in request.POST:
        date = request.POST.get('date')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out') or None  
        
        try:
            # Create attendance object but don't save yet
            attendance = Attendance(employee=employee, date=date, time_in=time_in, time_out=time_out)
            
            # This will run the clean method and validate work hours
            attendance.save()
            
            if time_out:  
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance added successfully!')
            return redirect('payroll_system:employee_profile', employee_id=employee_id)
        except ValidationError as e:
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

            attendance = get_object_or_404(Attendance, attendance_id=attendance_id, employee=employee)
            attendance.date = date
            attendance.time_in = time_in
            attendance.time_out = time_out
            
            attendance.save()
            
            if time_out:
                attendance.calculate_hours_worked()
                
            messages.success(request, 'Attendance updated successfully!')
        except ValidationError as e:
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')
        
        return redirect('payroll_system:employee_profile', employee_id=employee_id)
    
    # employee.update_attendance_stats()
    employee.refresh_from_db()
    
    # Get latest attendance and calculate hours worked
    latest_attendance = employee.attendances.order_by('-date').first()
    if latest_attendance:
        latest_attendance.calculate_hours_worked()  
    
    context = {
        'employee': employee,
        'latest_attendance': latest_attendance,
    }
    
    return render(request, 'payroll_system/employee_profile.html', context)

@login_required
def employee_edit(request):
    return render(request, 'payroll_system/employee_edit.html')

@login_required
def create_payroll(request):
    if request.method == 'POST':
        payroll_period_form = PayrollPeriodForm(request.POST)
        if payroll_period_form.is_valid():
            payroll_period_form.save()
            return redirect('payroll_system:payrolls')
        else:
            payroll_periods = PayrollPeriod.objects.all()

            context = {
                'payroll_period_form': payroll_period_form,
                'payroll_periods': payroll_periods,
            }

            return render(request, 'payroll_system/payrolls.html', context)

    return redirect('payroll_system:payrolls')

@login_required
def payrolls(request):
    # Get the current in-progress payroll period (if any)
    current_payroll = PayrollPeriod.objects.filter(
        payroll_status=PayrollPeriod.PayrollStatus.INPROGRESS
    ).first()
    
    # Get pending payroll periods (for the bottom list)
    pending_payrolls = PayrollPeriod.objects.filter(
        payroll_status=PayrollPeriod.PayrollStatus.PENDING
    ).order_by('start_date')

    payroll_period_form = PayrollPeriodForm()
    deduction_form = DeductionForm()   

    context = {
        'current_payroll': current_payroll,
        'pending_payrolls': pending_payrolls,
        'payroll_period_form': payroll_period_form,  
        'deduction_form': deduction_form,
    }

    return render(request, 'payroll_system/payrolls.html', context)

@login_required
def payroll_record(request):
    payroll_id = request.GET.get('payroll_id')
    
    if payroll_id:
        payroll = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_id)
        
        # Get all PayrollRecords for the selected period, with employee data
        records = PayrollRecord.objects.filter(payroll_period=payroll).select_related('employee')
        
        # If payroll is in progress, dynamically update all records
        if payroll.payroll_status == PayrollPeriod.PayrollStatus.INPROGRESS:
            for record in records:
                # Check if attendance data has changed
                current_days = record.days_worked
                actual_days = record.calculate_days_worked()
                
                if current_days != actual_days:
                    # Update the record
                    record.days_worked = actual_days
                    record.gross_pay = record.calculate_gross_pay()
                    record.net_pay = record.calculate_net_pay()
                    record.save(update_fields=['days_worked', 'gross_pay', 'net_pay'])
        
        # Refresh the queryset to get updated data
        records = PayrollRecord.objects.filter(payroll_period=payroll).select_related('employee')
        
        # Calculate total payroll amount for this period
        total_payroll = records.aggregate(total=Sum('net_pay'))['total'] or 0
        
        # Calculate percentage change compared to previous period
        previous_payroll = PayrollPeriod.objects.filter(
            payment_date__lt=payroll.payment_date
        ).order_by('-payment_date').first()
        
        payroll_percentage = 0
        if previous_payroll:
            previous_total = PayrollRecord.objects.filter(
                payroll_period=previous_payroll
            ).aggregate(total=Sum('net_pay'))['total'] or 0
            
            if previous_total > 0:
                payroll_percentage = ((total_payroll - previous_total) / previous_total) * 100
        
        context = {
            'records': records,
            'selected_payroll': payroll,
            'total_payroll': total_payroll,
            'payroll_percentage': payroll_percentage,
            'payday_date': payroll.payment_date,
        }
    else:
        # If no payroll is selected, show nothing or default view
        payroll_periods = PayrollPeriod.objects.all().order_by('-start_date')
        context = {
            'payroll_periods': payroll_periods,
            'records': [],
            'total_payroll': 0,
            'payroll_percentage': 0,
        }
    
    return render(request, 'payroll_system/payroll_record.html', context)

@login_required
def payroll_individual(request, employee_id):
    employee = get_object_or_404(Employee.objects.prefetch_related('payroll_records'), employee_id=employee_id)
    
    # Get the specific payroll record if a period is selected
    payroll_id = request.GET.get('payroll_id')
    selected_record = None
    payroll_records = []
    
    if payroll_id:
        payroll = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_id)
                
        selected_record = PayrollRecord.objects.filter(
            employee=employee,
            payroll_period__payroll_period_id=payroll_id
        ).select_related('payroll_period').first()
        
        # If payroll is in progress, always check and update the record
        if selected_record and payroll.payroll_status == PayrollPeriod.PayrollStatus.INPROGRESS:
            # Check if attendance data has changed
            current_days = selected_record.days_worked
            actual_days = selected_record.calculate_days_worked()
            
            if current_days != actual_days:
                # Update the record with fresh calculations
                selected_record.days_worked = actual_days
                selected_record.gross_pay = selected_record.calculate_gross_pay()
                selected_record.net_pay = selected_record.calculate_net_pay()
                selected_record.save(update_fields=['days_worked', 'gross_pay', 'net_pay'])
                
                # Refresh the record after update
                selected_record = PayrollRecord.objects.filter(
                    employee=employee,
                    payroll_period__payroll_period_id=payroll_id
                ).select_related('payroll_period').first()
        
        # Only get the current payroll record instead of all records
        if selected_record:
            payroll_records = [selected_record]
    else:
        # If no payroll is selected, get all records (fallback behavior)
        payroll_records = PayrollRecord.objects.filter(
            employee=employee
        ).select_related('payroll_period').order_by('-payroll_period__end_date')
    
    # Get attendance records for selected period
    attendance_records = []
    if selected_record:
        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__range=(
                selected_record.payroll_period.start_date,
                selected_record.payroll_period.end_date
            )
        ).order_by('date')
    
    context = {
        'employee': employee,
        'payroll_records': payroll_records,
        'selected_record': selected_record,
        'attendance_records': attendance_records,
    }
    
    return render(request, 'payroll_system/payroll_individual.html', context)

@login_required
def payroll_history(request):
    # Get all processed payroll periods
    processed_periods = PayrollPeriod.objects.filter(
        payroll_status=PayrollPeriod.PayrollStatus.PROCESSED
    ).order_by('-end_date')  # Most recent first
    
    for period in processed_periods:
        period.total_net_pay = period.payroll_records.aggregate(
            total=Sum('net_pay')
        )['total'] or 0
    
    context = {
        'payroll_periods': processed_periods,
    }
    
    return render(request, 'payroll_system/payroll_history.html', context)

@login_required
def edit_deductions(request):
    if request.method == 'POST':
        deduction_form = DeductionForm(request.POST)
        if deduction_form.is_valid():
            # Get form data
            deduction_type = deduction_form.cleaned_data['deduction_type']
            amount = deduction_form.cleaned_data['amount']
            payroll_period = deduction_form.cleaned_data['payroll_period']
            
            # Get all payroll records for the selected period
            payroll_records = PayrollRecord.objects.filter(payroll_period=payroll_period)
            
            # Create a deduction for each payroll record
            for record in payroll_records:
                Deduction.objects.create(
                    payroll_record=record,
                    deduction_type=deduction_type,
                    amount=amount
                )
                
                # Recalculate and save the net pay
                record.save()
                
            messages.success(request, f"{deduction_type} deduction applied to all employees for selected period.")
            return redirect('payroll_system:payroll_record')
        else:
            payroll_records = PayrollRecord.objects.all()

            context = {
                'deduction_form': deduction_form,
                'payroll_records': payroll_records,
            }

            return render(request, 'payroll_system/payroll_record.html', context)

    return redirect('payroll_system:payroll_record')

@login_required
def generate_payroll(request, payroll_period_id):
    # Get the payroll period or return 404
    payroll_period = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_period_id)
    
    try:
        # Try to generate the payroll
        payroll_period.generate()  
        messages.success(request, f"Payroll for period {payroll_period.start_date} to {payroll_period.end_date} has been generated successfully!")
    except ValidationError as e:
        # Catch the validation error and pass it to the template via messages
        messages.error(request, e.message)

    return redirect('payroll_system:payrolls')

@login_required
def update_all_incentives(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        amount = request.POST.get('amount')
        payroll_id = request.POST.get('payroll_id')
        
        try:
            amount = float(amount)
            
            # Get the current payroll period
            if payroll_id:
                payroll_period = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_id)
            else:
                # Default to the most recent in-progress payroll period
                payroll_period = PayrollPeriod.objects.filter(
                    payroll_status=PayrollPeriod.PayrollStatus.INPROGRESS
                ).order_by('-start_date').first()
                
                if not payroll_period:
                    messages.error(request, 'No active payroll period found.')
                    return redirect('payroll_system:payrolls')
            
            # Only allow updates for in-progress periods
            if payroll_period.payroll_status != PayrollPeriod.PayrollStatus.INPROGRESS:
                messages.error(request, 'Can only update incentives for in-progress payroll periods.')
                return redirect('payroll_system:payrolls')
            
            # Get all payroll records for this period
            records = PayrollRecord.objects.filter(payroll_period=payroll_period)
            
            # Update incentives for each record
            for record in records:
                current_incentives = record.incentives or 0  # Handle None values
                
                if action == 'add':
                    record.incentives = current_incentives + amount
                elif action == 'subtract':
                    record.incentives = max(0, current_incentives - amount)
                
                # Recalculate gross pay and net pay
                record.gross_pay = record.calculate_gross_pay()
                record.net_pay = record.calculate_net_pay()
                
                # Save the record with updated values
                record.save(update_fields=['incentives', 'gross_pay', 'net_pay'])
            
            messages.success(request, f'Successfully updated incentives for all employees!')
            
        except ValueError:
            messages.error(request, 'Please enter a valid number for amount')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    # Redirect based on where the request came from
    redirect_url = request.POST.get('redirect_url', 'payroll_system:payroll_record')

    if payroll_id and 'payroll_record' in redirect_url:
        base_url = reverse('payroll_system:payroll_record')
        return redirect(f'{base_url}?payroll_id={payroll_id}')
    else:
        return redirect(redirect_url)

@login_required
def update_employee_incentives(request, employee_id):
    """Update incentives for a specific employee in the current payroll period."""
    if request.method == 'POST':
        action = request.POST.get('action')
        amount_str = request.POST.get('amount')
        payroll_id = request.POST.get('payroll_id')
        
        try:
            # Get the employee
            employee = get_object_or_404(Employee, employee_id=employee_id)
            
            # Get the specified payroll period
            if payroll_id:
                payroll_period = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_id)
            else:
                # Default to the most recent in-progress payroll period
                payroll_period = PayrollPeriod.objects.filter(
                    payroll_status=PayrollPeriod.PayrollStatus.INPROGRESS
                ).order_by('-start_date').first()
                
                if not payroll_period:
                    error_msg = 'No active payroll period found.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_msg})
                    else:
                        messages.error(request, error_msg)
                        return redirect('payroll_system:payroll_individual', employee_id=employee_id)
            
            # Only allow updates for in-progress periods
            if payroll_period.payroll_status != PayrollPeriod.PayrollStatus.INPROGRESS:
                error_msg = 'Can only update incentives for in-progress payroll periods.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                else:
                    messages.error(request, error_msg)
                    return redirect('payroll_system:payroll_individual', employee_id=employee_id)
            
            # Get the payroll record for this employee and period
            payroll_record = PayrollRecord.objects.filter(
                employee=employee,
                payroll_period=payroll_period
            ).first()
            
            if not payroll_record:
                error_msg = 'No payroll record exists for this employee in the selected period.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                else:
                    messages.error(request, error_msg)
                    return redirect('payroll_system:payroll_individual', employee_id=employee_id)
            
            # Convert amount to float
            amount = float(amount_str)
            
            # Update incentives based on action
            current_incentives = payroll_record.incentives or 0
            
            if action == 'add':
                payroll_record.incentives = current_incentives + amount
            elif action == 'subtract':
                # Ensure we don't go below zero
                payroll_record.incentives = max(0, current_incentives - amount)
            
            # Recalculate gross pay and net pay
            payroll_record.gross_pay = payroll_record.calculate_gross_pay()
            payroll_record.net_pay = payroll_record.calculate_net_pay()
            
            # Save the updated record
            payroll_record.save(update_fields=['incentives', 'gross_pay', 'net_pay'])
            
            # Format the values for display
            formatted_incentives = "{:.2f}".format(payroll_record.incentives)
            formatted_gross_pay = "{:.2f}".format(payroll_record.gross_pay)
            formatted_net_pay = "{:.2f}".format(payroll_record.net_pay)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return JSON response for AJAX request
                return JsonResponse({
                    'success': True,
                    'new_incentives': formatted_incentives,
                    'new_gross_pay': formatted_gross_pay,
                    'new_net_pay': formatted_net_pay
                })
            else:
                # Regular form submission
                messages.success(
                    request, 
                    f'Successfully {"added to" if action == "add" else "subtracted from"} incentives for {employee.first_name} {employee.last_name}.'
                )
                redirect_url = f'payroll_system:payroll_individual'
                if payroll_id:
                    return redirect(f'{redirect_url}?payroll_id={payroll_id}', employee_id=employee_id)
                return redirect(redirect_url, employee_id=employee_id)
                
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
def confirm_payroll(request, payroll_period_id):
    if request.method == 'POST':
        try:
            # Get the payroll period to confirm
            payroll_period = get_object_or_404(PayrollPeriod, payroll_period_id=payroll_period_id)
            
            # Use the model method to confirm payroll
            payroll_period.confirm()
            
            # Add success message
            messages.success(request, f"Payroll period from {payroll_period.start_date} to {payroll_period.end_date} has been successfully processed.")
            
            # Redirect to payroll history page
            return redirect('payroll_system:payroll_history')
            
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('payroll_system:payrolls')
        except Exception as e:
            messages.error(request, f'Error confirming payroll: {e}')
            return redirect('payroll_system:payrolls')
    
    # If not POST, redirect to payrolls page
    return redirect('payroll_system:payrolls')

# @login_required
# def payroll_edit(request, employee_id):
#     employee = Employee.objects.get(employee_id=employee_id)
#     today = timezone.now().date()
    
#     # Get an active pending payroll, or create a new one
#     try:
#         payroll = Payroll.objects.get(
#             employee_id_fk=employee,
#             payment_date__gte=today,
#             payroll_status=Payroll.PayrollStatus.PENDING  # Only get PENDING payrolls
#         )
#     except Payroll.DoesNotExist:
#         # If no pending payroll exists, try to get the most recent one as a starting point
#         payroll = Payroll(employee_id_fk=employee)
        
#         # Payment date will be set to next Saturday automatically in the save method
        
#         # Copy data from the most recent payroll if it exists
#         try:
#             prev_payroll = Payroll.objects.filter(
#                 employee_id_fk=employee
#             ).latest('payment_date')
            
#             # Copy relevant fields
#             payroll.rate = prev_payroll.rate
#             payroll.incentives = prev_payroll.incentives
#             payroll.payroll_status = Payroll.PayrollStatus.PENDING  
#         except Payroll.DoesNotExist:
#             # First payroll for this employee, use defaults
#             pass
#     except Payroll.MultipleObjectsReturned:
#         # If multiple pending payrolls exist, get the most recent one
#         payroll = Payroll.objects.filter(
#             employee_id_fk=employee,
#             payment_date__gte=today,
#             payroll_status=Payroll.PayrollStatus.PENDING
#         ).order_by('-payment_date').first()
    
#     if request.method == 'POST':
#         # Check if this is a cash advance submission
#         if 'cash_advance' in request.POST and request.POST.get('number'):
#             try:
#                 cash_amount = float(request.POST.get('number', 0))
#                 if cash_amount > 0:
#                     payroll.cash_advance += cash_amount
#                     payroll.save()
#                     messages.success(request, f"Cash advance of ₱{cash_amount:,.2f} added successfully.")
#                 else:
#                     messages.error(request, "Cash advance amount must be greater than zero.")
#             except ValueError:
#                 messages.error(request, "Invalid cash advance amount.")
            
#             return redirect('payroll_system:payroll_edit', employee_id=employee_id)
#         # Check if this is a payment date change
#         elif 'payment_date' in request.POST and request.POST.get('payment_date'):
#             try:
#                 new_date = datetime.strptime(request.POST.get('payment_date'), '%Y-%m-%d').date()
#                 if new_date >= today:
#                     payroll.payment_date = new_date
#                     payroll.save()
#                     messages.success(request, f"Payment date updated to {new_date.strftime('%Y-%m-%d')}.")
#                 else:
#                     messages.error(request, "Payment date cannot be in the past.")
#             except ValueError:
#                 messages.error(request, "Invalid date format.")
                
#             return redirect('payroll_system:payroll_edit', employee_id=employee_id)
#         else:
#             # Regular payroll form submission
#             form = PayrollForm(request.POST, instance=payroll)
#             if form.is_valid():
#                 form.save()  # This will trigger the salary calculation in the model's save method
                
#                 # Log the history
#                 History.objects.create(description=f"Payroll for {employee.first_name} {employee.last_name} ({employee.employee_id}) was updated.")
                
#                 return redirect('payroll_system:payroll_individual', employee_id=employee_id)
#     else:
#         form = PayrollForm(instance=payroll)

#     # Get the latest payroll for display purposes
#     latest_payroll = employee.payrolls.order_by('-payment_date').first()
    
#     # Get current week's Monday for context display
#     current_weekday = payroll.payment_date.weekday()
#     monday_of_week = payroll.payment_date - timedelta(days=current_weekday)
#     sunday_of_week = monday_of_week + timedelta(days=6)
    
#     context = {
#         'form': form,
#         'employee': employee,
#         'latest_payroll': latest_payroll,
#         'week_start': monday_of_week,
#         'week_end': sunday_of_week,
#         'today': today
#     }
#     return render(request, 'payroll_system/payroll_edit.html', context)

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
        
        # if task_id and task_id != 'undefined':
        #     task = get_object_or_404(Task, task_id=task_id)
            
        #     if 'incentives' in request.POST:
        #         amount = request.POST.get('number')
        #         if amount and float(amount) > 0:
        #             payroll = Payroll.objects.filter(employee_id_fk=task.employee).latest('payment_date')
                    
        #             payroll.incentives = payroll.incentives + float(amount)
        #             payroll.save()
                    
        #         task.task_status = 'Completed'
        #         task.save()
                
        #         return redirect('payroll_system:status')
    
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

# @login_required
# def print(request):
#     employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    
#     query = request.GET.get('q', '')
    
#     latest_attendance_subquery = (
#         Attendance.objects
#         .filter(employee_id_fk=OuterRef('pk'))
#         .order_by('-date')
#         .values('date')[:1]
#     )
    
#     # latest_payroll_subquery = (
#     #     Payroll.objects
#     #     .filter(employee_id_fk=OuterRef('pk'))
#     #     .order_by('-payment_date')
#     #     .values('payroll_status')[:1]
#     # )
    
#     # employees = Employee.objects.annotate(
#     #     latest_attendance_date=Subquery(latest_attendance_subquery),
#     #     latest_payroll_status=Subquery(latest_payroll_subquery)
#     # )
    
#     if query:
#         employees = employees.filter(
#             first_name__icontains=query
#         ) | employees.filter(
#             last_name__icontains=query
#         ) | employees.filter(
#             employee_id__icontains=query
#         )
    
#     total_employees = employees.count()
    
#     # Count employees with different payroll statuses
#     processed_payroll_count = employees.filter(latest_payroll_status='PROCESSED').count()
#     pending_payroll_count = employees.filter(latest_payroll_status='PENDING').count()
    
#     # Calculate the next Saturday for the payday
#     today = now().date()
#     days_until_saturday = (5 - today.weekday()) % 7  # 5 is Saturday
#     next_saturday = today + timedelta(days=days_until_saturday)
    
#     # Get the start and end of the current week (Monday to Sunday)
#     start_of_week = today - timedelta(days=today.weekday())  # Monday
#     end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
#     # Get payroll data for each employee with calculated salary
#     employee_data = []
#     try:
#         for employee in employees:
#             latest_payroll = employee.payrolls.order_by('-payment_date').first()
            
#             if latest_payroll:
#                 # Count attendance for the current week
#                 weekly_attendance_count = Attendance.objects.filter(
#                     employee_id_fk=employee,
#                     date__range=[start_of_week, end_of_week],
#                     attendance_status='Present'
#                 ).count()
                
#                 # Calculate salary using the model method
#                 latest_payroll.calculate_salary(weekly_attendance_count)
#                 latest_payroll.save()  # Save the updated salary
            
#             employee_data.append({
#                 'employee': employee,
#                 'latest_payroll': latest_payroll
#             })
#     except Exception as e:
#         print(f"Error processing employee data: {e}")
    
#     # Calculate statistics for the dashboard
#     current_month_start = today.replace(day=1)
#     previous_month_end = current_month_start - timedelta(days=1)
#     previous_month_start = previous_month_end.replace(day=1)

#     active_employees_per_day = (
#         Attendance.objects.filter(date__range=[start_of_week, end_of_week])
#         .values('date')
#         .annotate(active_count=Count('employee_id_fk', distinct=True))
#     )

#     total_active_counts = sum(day['active_count'] for day in active_employees_per_day)
#     days_counted = len(active_employees_per_day) or 1  # Avoid division by zero
#     avg_active_employees = total_active_counts / days_counted

#     employees_with_latest_payroll = Employee.objects.annotate(latest_payroll_status=Subquery(latest_payroll_subquery))

#     processed_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PROCESSED').count()
#     pending_payroll_count = employees_with_latest_payroll.filter(latest_payroll_status='PENDING').count()
    
#     # Calculate Total Payroll (Sum of all processed salaries)
#     total_payroll = Payroll.objects.filter(payroll_status='PROCESSED').aggregate(Sum('salary'))['salary__sum']

#     if total_payroll is None:
#         total_payroll = "No total payroll yet"

#     # Get the earliest payment_date from PENDING payrolls
#     next_payday = Payroll.objects.filter(payroll_status='PENDING').aggregate(Min('payment_date'))['payment_date__min']

#     if next_payday:
#         formatted_payday = next_payday.strftime('%m/%d/%Y')
#         day_of_week = next_payday.strftime('%a').upper()
#         current_payday = f"{formatted_payday}, {day_of_week}"
#     else:
#         current_payday = "XX/XX/XXXX, SAT"


#     avg_rate = Payroll.objects.filter(rate__gt=0).aggregate(Avg('rate'))['rate__avg']

#     if avg_rate is None:
#         avg_rate = "No rate data"
        
#     # Calculate Total Payroll for current and previous month
#     current_total_payroll = Payroll.objects.filter(
#         payroll_status='PROCESSED',
#         payment_date__gte=current_month_start,
#         payment_date__lte=today
#     ).aggregate(Sum('salary'))['salary__sum'] or 0

#     previous_total_payroll = Payroll.objects.filter(
#         payroll_status='PROCESSED',
#         payment_date__gte=previous_month_start,
#         payment_date__lte=previous_month_end
#     ).aggregate(Sum('salary'))['salary__sum'] or 0

#     # Calculate percentage change for total payroll
#     payroll_percentage = 0
#     if previous_total_payroll > 0:
#         payroll_percentage = ((current_total_payroll - previous_total_payroll) / previous_total_payroll) * 100

#     # Calculate Average Rate for current and previous month
#     current_avg_rate = Payroll.objects.filter(
#         rate__gt=0,
#         payment_date__gte=current_month_start,
#         payment_date__lte=today
#     ).aggregate(Avg('rate'))['rate__avg'] or 0

#     previous_avg_rate = Payroll.objects.filter(
#         rate__gt=0,
#         payment_date__gte=previous_month_start,
#         payment_date__lte=previous_month_end
#     ).aggregate(Avg('rate'))['rate__avg'] or 0

#     rate_percentage = 0
#     if previous_avg_rate > 0:
#         rate_percentage = ((current_avg_rate - previous_avg_rate) / previous_avg_rate) * 100

#     # Format the next payday for display
#     formatted_payday = next_payday.strftime('%m/%d/%Y')
#     day_of_week = next_payday.strftime('%a').upper()
#     formatted_payday_display = f"{formatted_payday}, {day_of_week}"
#     current_payday = formatted_payday_display

#     # Pass all data to the template
#     try:
#         context = {
#             'employee_data': employee_data,
#             'total_employees': total_employees,
#             'avg_active_employees': round(avg_active_employees),
#             'processed_payroll_count': processed_payroll_count,
#             'pending_payroll_count': pending_payroll_count,
#             'total_payroll': total_payroll,  
#             'previous_total_payroll': previous_total_payroll,
#             'payroll_percentage': payroll_percentage,
#             'next_payday': next_payday,  
#             'formatted_payday': formatted_payday_display,
#             'current_payday': current_payday,
#             'previous_avg_rate': previous_avg_rate,
#             'rate_percentage': rate_percentage,
#             'avg_rate': current_avg_rate,
#             'query': query,
#         }
#     except Exception as e:
#         print(f"Error creating context: {e}")
#         context = {
#             'processed_payroll_count': processed_payroll_count,
#             'pending_payroll_count': pending_payroll_count,
#             'total_payroll': total_payroll,  
#             'previous_total_payroll': previous_total_payroll,
#             'payroll_percentage': payroll_percentage,
#             'next_payday': next_payday,
#             'formatted_payday': formatted_payday_display,
#             'previous_avg_rate': previous_avg_rate,
#             'rate_percentage': rate_percentage,
#             'avg_rate': current_avg_rate,
#             'query': query,
#         }

#     return render(request, 'payroll_system/print.html', context)

# @login_required
# def update_payday(request):
#     if request.method == 'POST' and request.POST.get('payday') == 'true':
#         new_date = request.POST.get('date')
#         if new_date:
#             formatted_date = datetime.strptime(new_date, "%Y-%m-%d").date()
#             Payroll.objects.filter(payroll_status='PENDING').update(payment_date=formatted_date)

#             # Format for frontend display (e.g., "05/03/2025, SAT")
#             formatted_display = formatted_date.strftime("%m/%d/%Y") + ", " + formatted_date.strftime("%a").upper()
#             return JsonResponse({'success': True, 'updated_payday': formatted_display})
#         return JsonResponse({'success': False, 'error': 'Invalid date'})
#     return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def get_attendance_stats(request):
    period = request.GET.get('period', 'day')
    
    # Get current date
    today = timezone.now().date()
    
    # Define date range based on period
    if period == 'day':
        start_date = today
        end_date = today
        period_display = "Today's Attendance"
    elif period == 'week':
        # Get the start of the week (Monday)
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        period_display = f"Week: {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
    elif period == 'month':
        start_date = today.replace(day=1)
        # Get last day of month
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = today.replace(day=last_day)
        period_display = f"Month: {today.strftime('%B %Y')}"
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        period_display = f"Year: {today.year}"
    else:
        return JsonResponse({'error': 'Invalid period'}, status=400)
    
    # Query for attendance data
    present_count = Attendance.objects.filter(
        date__gte=start_date, 
        date__lte=end_date,
        attendance_status=Attendance.AttendanceStatus.PRESENT
    ).count()
    
    absent_count = Attendance.objects.filter(
        date__gte=start_date, 
        date__lte=end_date,
        attendance_status=Attendance.AttendanceStatus.ABSENT
    ).count()
    
    # If no data is found, return minimal data to avoid division by zero
    if present_count == 0 and absent_count == 0:
        present_count = 0
        absent_count = 0
    
    # Return data as JSON
    return JsonResponse({
        'labels': ['Present', 'Absent'],
        'data': [present_count, absent_count],
        'period': period,
        'period_display': period_display
    })
    
@login_required
def payroll_by_week(request):
    """
    API endpoint that returns payroll totals for the last 5 weeks using PayrollRecord model
    """
    today = timezone.now().date()
    
    # Get the Saturday of the current week (or the last Saturday if today is Saturday)
    current_weekday = today.weekday()  # 0=Monday, 6=Sunday
    days_since_saturday = (current_weekday - 5) % 7  # 5 represents Saturday
    
    # Last completed Saturday
    latest_saturday = today - timedelta(days=days_since_saturday)
    if days_since_saturday == 0 and current_weekday != 5:  # If calculating for today and it's not Saturday
        latest_saturday -= timedelta(days=7)  # Go to previous Saturday
    
    # Calculate the 5 previous Saturdays
    saturdays = [latest_saturday - timedelta(days=7*i) for i in range(5)]
    saturdays.reverse()  # Put them in chronological order
    
    # Format dates for labels 
    labels = [date.strftime("%b %d") for date in saturdays]
    
    # Get total payroll amount for each payment date by finding PayrollPeriods ending on Saturdays
    amounts = []
    for saturday in saturdays:
        # Find the payroll period that ends on this Saturday
        payroll_records = PayrollRecord.objects.filter(
            payroll_period__end_date=saturday,
            payroll_period__payroll_status=PayrollPeriod.PayrollStatus.PROCESSED
        )
        
        # Sum the net pay for all employees in this period
        weekly_total = payroll_records.aggregate(
            total_net_pay=Sum('net_pay')
        )['total_net_pay'] or 0
        
        amounts.append(round(weekly_total, 2))
    
    return JsonResponse({
        'labels': labels,
        'amounts': amounts
    })
    
#new
@login_required
def calculate_payroll_totals(request):
    """
    Calculate weekly, monthly, and yearly payroll totals based on PayrollRecord data
    """
    today = timezone.now().date()
    
    # Calculate the start and end dates for periods
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    week_end = week_start + timedelta(days=6)  # Sunday of current week
    
    month_start = date_class(today.year, today.month, 1)  # First day of current month
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    month_end = date_class(today.year, today.month, last_day_of_month)  # Last day of current month
    
    year_start = date_class(today.year, 1, 1)  # First day of current year
    year_end = date_class(today.year, 12, 31)  # Last day of current year

    # Query for weekly payroll total
    weekly_payroll = PayrollRecord.objects.filter(
        payroll_period__start_date__gte=week_start,
        payroll_period__end_date__lte=week_end
    ).aggregate(total=Sum('net_pay'))['total'] or 0
    
    # Query for monthly payroll total
    monthly_payroll = PayrollRecord.objects.filter(
        payroll_period__start_date__gte=month_start,
        payroll_period__end_date__lte=month_end
    ).aggregate(total=Sum('net_pay'))['total'] or 0
    
    # Query for yearly payroll total
    yearly_payroll = PayrollRecord.objects.filter(
        payroll_period__start_date__gte=year_start,
        payroll_period__end_date__lte=year_end
    ).aggregate(total=Sum('net_pay'))['total'] or 0

    return {
        'weekly_payroll': weekly_payroll,
        'monthly_payroll': monthly_payroll,
        'yearly_payroll': yearly_payroll
    }

@login_required    
def get_next_payday(employee):
    """
    Get the next payday for a specific employee.
    Returns a formatted date string or None if no upcoming payday is found.
    """
    today = timezone.now().date()
    
    # Get the next upcoming payment date for this employee
    next_payday = PayrollPeriod.objects.filter(
        employee=employee,
        payment_date__gte=today,
        payroll_status=PayrollPeriod.PayrollStatus.PENDING
    ).order_by('payment_date').first()
    
    if next_payday:
        # Format the date as desired, e.g., "May 15, 2025"
        return next_payday.payment_date.strftime("%B %d, %Y")
    
    return None

@login_required
def payroll_stats_api(request):
    """API endpoint to return payroll data for the chart"""
    
    # Get the 5 most recent completed payroll periods that have records
    recent_periods = PayrollPeriod.objects.order_by('-end_date')
    
    dates = []
    amounts = []
    
    # Filter out periods with no payroll records and limit to 5
    valid_periods = []
    for period in recent_periods:
        total = PayrollRecord.objects.filter(payroll_period=period).aggregate(
            total=Sum('net_pay')
        )['total'] or 0
        
        # Only include periods that have payroll records with non-zero totals
        if total > 0:
            valid_periods.append((period, total))
            
        # Stop once we have 5 valid periods
        if len(valid_periods) >= 5:
            break
    
    # If we have valid periods, process them (oldest to newest for the chart)
    for period, total in reversed(valid_periods):
        # Format date as "MMM DD" (e.g., "Apr 15")
        formatted_date = period.end_date.strftime('%b %d')
        dates.append(formatted_date)
        amounts.append(float(total))
    
    return JsonResponse({
        'dates': dates,
        'amounts': amounts
    })

@login_required
def payslip(request):
    return render(request, 'payslip.html')
    
@login_required
def payroll_view(request):
    # Existing view code...
    
    # Calculate average employee rate
    employees = Employee.objects.filter(is_active=True)
    if employees.exists():
        # Calculate the average daily rate from all active employees
        avg_rate = employees.aggregate(Avg('daily_rate'))['daily_rate__avg']
        
        # Compare with previous period for percentage change if needed
        # For example, assuming you have a way to get previous period's average rate
        previous_avg_rate = get_previous_avg_rate()  # You'll need to implement this function
        
        if previous_avg_rate and previous_avg_rate > 0:
            rate_percentage = ((avg_rate - previous_avg_rate) / previous_avg_rate) * 100
        else:
            rate_percentage = 0
    else:
        avg_rate = "No rate data"  
        rate_percentage = 0
    
    context = {
        # Other context data...
        'avg_rate': avg_rate,
        'rate_percentage': rate_percentage,
    }
    
    return render(request, 'payroll_record.html', context)

def get_previous_avg_rate():
    # Implementation to get previous period's average rate
    # For example, you could get employees' rates from the previous payroll period
    # or simply store historical data
    previous_period = PayrollPeriod.objects.filter(
        end_date__lt=timezone.now()
    ).order_by('-end_date').first()
    
    if previous_period:
        # Get the employees who were active during the previous period
        previous_employees = Employee.objects.filter(
            payroll_records__payroll_period=previous_period,
            is_active=True
        ).distinct()
        
        if previous_employees.exists():
            return previous_employees.aggregate(Avg('daily_rate'))['daily_rate__avg']
    
    return None