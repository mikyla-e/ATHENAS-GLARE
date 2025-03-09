from contextlib import redirect_stderr
from http.client import HTTPResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import EmployeeForm, PayrollForm
from .models import Employee, Payroll
from .face_recognition_attendance import recognize_face
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from .camera_capture import capture_image  # Import OpenCV function
from django.http import JsonResponse

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
            employee = form.save(commit=False)  # Save without committing

            # Get the captured image path from the form
            captured_image_path = request.POST.get("employee_image")
            if captured_image_path:
                employee.employee_image = captured_image_path

            employee.save()  # Save employee record
            return redirect('/payroll_system/employee_registration')
    else:
        form = EmployeeForm()

    return render(request, 'payroll_system/employee_registration.html', {'form': form})

def capture_image_view(request):
    
    response = capture_image(request)  # `capture_image` returns a JsonResponse

    return response  # Directly return JsonResponse instead of checking dict


@login_required
def employees(request):
    employees = Employee.objects.prefetch_related('payrolls', 'attendances').all()
    context = {
        'employees': employees
    }
    return render(request, 'payroll_system/employees.html', context)

@login_required
def employee_profile(request, employee_id):
    employee = Employee.objects.prefetch_related('payrolls', 'attendances').get(employee_id=employee_id)
    context = {
        'employee' : employee,
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
