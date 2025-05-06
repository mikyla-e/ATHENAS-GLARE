import base64
import cv2
import io
import numpy as np
import logging
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from payroll_system.models import Employee
from .face_recognition_attendance import process_frame_recognition, mark_attendance, check_attendance_status, get_filtered_attendance
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

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
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                
                try:
                    # Convert base64 to image
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Convert to OpenCV format - support both RGB and RGBA
                    np_image = np.array(image)
                    if len(np_image.shape) == 3 and np_image.shape[2] == 4:
                        # RGBA image, convert to RGB
                        opencv_image = cv2.cvtColor(np_image, cv2.COLOR_RGBA2BGR)
                    else:
                        # RGB image
                        opencv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
                    
                    # Process face recognition on this frame
                    result = process_frame_recognition(opencv_image)
                    
                    return JsonResponse(result)
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
                    return JsonResponse({'status': 'error', 'message': f"Error processing image: {str(e)}"})
            
            except Exception as e:
                logger.error(f"Error in image data handling: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)})
        
        # For checking attendance status with optional date filtering
        elif request.POST.get('action') == 'check_status':
            employee_id = request.POST.get('employee_id')
            
            if not employee_id:
                return JsonResponse({'status': 'error', 'message': 'No employee detected'})
            
            try:
                employee = Employee.objects.get(employee_id=employee_id)
                
                # Check if date filter params are provided
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                
                if start_date and end_date:
                    # Use date filtered attendance check
                    result = check_attendance_status(employee, start_date, end_date)
                else:
                    # Use default attendance check
                    result = check_attendance_status(employee)
                    
                return JsonResponse(result)
                
            except Employee.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Employee not found'})
        
        # For handling explicit date filtering requests
        elif request.POST.get('action') == 'filter_history':
            employee_id = request.POST.get('employee_id')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if not employee_id:
                return JsonResponse({'status': 'error', 'message': 'No employee detected'})
                
            if not start_date or not end_date:
                return JsonResponse({'status': 'error', 'message': 'Start and end dates are required'})
            
            try:
                # Validate date formats
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                except ValueError:
                    return JsonResponse({'status': 'error', 'message': 'Invalid date format. Please use YYYY-MM-DD'})
                
                # Check if end date is after start date
                if start_date > end_date:
                    return JsonResponse({'status': 'error', 'message': 'End date must be after start date'})
                
                employee = Employee.objects.get(employee_id=employee_id)
                result = get_filtered_attendance(employee, start_date, end_date)
                return JsonResponse(result)
                
            except Employee.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Employee not found'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        
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