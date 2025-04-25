import base64
import cv2
import io
import numpy as np
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from payroll_system.models import Employee
from .face_recognition_attendance import process_frame_recognition, mark_attendance, check_attendance_status
from PIL import Image

# Create your views here.

@csrf_exempt
def attendance(request):
    if request.method == "GET":
        return render(request, "attendance/index.html")
    
    elif request.method == "POST":
        
        # For AJAX face recognition request
        if 'image_data' in request.POST:
            try:
                # Get the image data from the ajax request
                image_data = request.POST.get('image_data')
                
                # Remove the data:image/jpeg;base64, part
                image_data = image_data.split(',')[1]
                
                # Convert base64 to image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Convert to OpenCV format
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Process face recognition on this frame
                result = process_frame_recognition(opencv_image)
                
                return JsonResponse(result)
            
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        
        # For checking attendance status
        elif request.POST.get('action') == 'check_status':
            employee_id = request.POST.get('employee_id')
            
            if not employee_id:
                return JsonResponse({'status': 'error', 'message': 'No employee detected'})
            
            try:
                employee = Employee.objects.get(employee_id=employee_id)
                result = check_attendance_status(employee)
                return JsonResponse(result)
                
            except Employee.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Employee not found'})
        
        # For time in/out actions
        elif request.POST.get('action') in ['time_in', 'time_out']:
            action = request.POST.get('action')
            employee_id = request.POST.get('employee_id')
            
            if not employee_id:
                return JsonResponse({'status': 'error', 'message': 'No employee detected'})
            
            try:
                employee = Employee.objects.get(employee_id=employee_id)
                result = mark_attendance(employee, action)
                return JsonResponse(result)
                
            except Employee.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Employee not found'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})