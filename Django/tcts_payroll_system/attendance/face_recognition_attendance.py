import os
import cv2
import face_recognition
from django.core.exceptions import ValidationError
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from payroll_system.models import Employee, Attendance 

# Cache the face encodings to avoid reloading them for every frame
@lru_cache(maxsize=1)
def load_registered_faces():
    registered_faces = {}
    employee_names = {}
    employees = Employee.objects.all()
    
    print("Loading registered faces...")
    
    for employee in employees:
        if employee.employee_image:
            try:
                image_path = employee.employee_image.path
                
                if os.path.exists(image_path):
                    # Load the image directly without resizing at first
                    image = cv2.imread(image_path)
                    if image is None:
                        print(f"Failed to load image for employee {employee.employee_id}")
                        continue
                    
                    # Convert to RGB (face_recognition uses RGB)
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Try to detect faces using HOG model
                    face_locations = face_recognition.face_locations(rgb_image, model="hog")
                    
                    if not face_locations:
                        print(f"No face detected in image for employee {employee.employee_id}")
                        # Try using CNN model as a fallback (more accurate but slower)
                        face_locations = face_recognition.face_locations(rgb_image, model="cnn")
                        
                        if not face_locations:
                            print(f"Still no face detected using CNN model for employee {employee.employee_id}")
                            continue
                    
                    # Get the largest face by area
                    largest_face = max(face_locations, key=lambda rect: (rect[2]-rect[0])*(rect[3]-rect[1]))
                    
                    # Create encoding
                    encodings = face_recognition.face_encodings(rgb_image, [largest_face])

                    if encodings:
                        employee_id = str(employee.employee_id)
                        registered_faces[employee_id] = encodings[0]
                        employee_names[employee_id] = f"{employee.first_name} {employee.last_name}"
                        print(f"Successfully loaded face for {employee_names[employee_id]}")
                    else:
                        print(f"Failed to encode face for employee {employee.employee_id}")
                else:
                    print(f"Image path does not exist: {image_path}")
            except Exception as e:
                print(f"Error processing image for employee {employee.employee_id}: {str(e)}")
    
    print(f"Loaded {len(registered_faces)} face encodings")
    return registered_faces, employee_names

def compare_faces(known_encoding, captured_encoding):
    """
    Compare face encodings with improved matching logic
    """
    # Calculate distance between face encodings
    distance = face_recognition.face_distance([known_encoding], captured_encoding)[0]
    
    # Use a more lenient tolerance for better matching
    # 0.6 is more lenient than the default 0.5
    tolerance = 0.6
    
    # Use built-in compare_faces function
    match = face_recognition.compare_faces([known_encoding], captured_encoding, tolerance=tolerance)[0]
    
    # Return match status and distance (for debugging)
    return match, distance

def check_attendance_status(employee, start_date=None, end_date=None):
    """
    Check the attendance status of an employee with optional date filtering.
    
    Args:
        employee: Employee model instance
        start_date: Optional start date for filtering (YYYY-MM-DD)
        end_date: Optional end date for filtering (YYYY-MM-DD)
        
    Returns:
        Dictionary with attendance status and logs
    """
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    # Get today's attendance logs
    today_logs = Attendance.objects.filter(
        employee=employee,
        date=today_str
    ).order_by('time_in')
    
    # Check if employee has an open session (time_in but no time_out)
    open_session = today_logs.filter(time_in__isnull=False, time_out__isnull=True).first()
    has_open_session = open_session is not None
    
    # Format today's logs for frontend
    formatted_today_logs = []
    for log in today_logs:
        formatted_today_logs.append({
            'time_in': log.time_in.strftime('%H:%M:%S') if log.time_in else None,
            'time_out': log.time_out.strftime('%H:%M:%S') if log.time_out else None,
        })
    
    # Get historical logs with date filtering if provided
    history_query = Attendance.objects.filter(employee=employee)
    
    if start_date and end_date:
        # Filter by date range
        history_query = history_query.filter(
            date__gte=start_date,
            date__lte=end_date,
            date__lt=today_str  # Exclude today's logs from history
        )
    else:
        # Default: Last 30 days excluding today
        thirty_days_ago = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        history_query = history_query.filter(
            date__gte=thirty_days_ago,
            date__lt=today_str
        )
    
    # Order by date descending
    history_logs = history_query.order_by('-date', 'time_in')
    
    # Format historical logs for frontend
    formatted_history_logs = []
    for log in history_logs:
        formatted_history_logs.append({
            'date': log.date.strftime('%Y-%m-%d'),
            'time_in': log.time_in.strftime('%H:%M:%S') if log.time_in else None,
            'time_out': log.time_out.strftime('%H:%M:%S') if log.time_out else None,
        })
    
    result = {
        'status': 'success',
        'has_open_session': has_open_session,
        'today_logs': formatted_today_logs,
        'history_logs': formatted_history_logs
    }
    
    # Add the open session ID if there is one
    if has_open_session:
        result['current_log_id'] = open_session.attendance_id
    
    return result

def get_filtered_attendance(employee, start_date, end_date):
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Adjust end_date to include the full day
    end_date_obj = datetime.combine(end_date_obj, datetime.max.time()).date()
    
    # Get today's date
    today = datetime.now().date()
    
    # Get today's logs
    today_logs = Attendance.objects.filter(
        employee=employee,
        date=today
    ).order_by('time_in')
    
    # Get history logs within the date range
    history_logs = Attendance.objects.filter(
        employee=employee,
        date__gte=start_date_obj,
        date__lte=end_date_obj,
        date__lt=today  # Exclude today's logs from history
    ).order_by('-date', 'time_in')
    
    # Format logs for JSON response
    formatted_today = []
    for log in today_logs:
        formatted_today.append({
            'date': log.date.strftime('%Y-%m-%d'),
            'time_in': log.time_in.strftime('%H:%M:%S') if log.time_in else None,
            'time_out': log.time_out.strftime('%H:%M:%S') if log.time_out else None,
        })
    
    formatted_history = []
    for log in history_logs:
        formatted_history.append({
            'date': log.date.strftime('%Y-%m-%d'),
            'time_in': log.time_in.strftime('%H:%M:%S') if log.time_in else None,
            'time_out': log.time_out.strftime('%H:%M:%S') if log.time_out else None,
        })
    
    return {
        'status': 'success',
        'today_logs': formatted_today,
        'history_logs': formatted_history,
        'has_open_session': any(log.time_in and not log.time_out for log in today_logs),
    }
        
def mark_attendance(employee, action):
    """
    Marks employee attendance for time_in or time_out actions
    Returns appropriate status message
    """
    today = datetime.now().date()
    current_time = datetime.now().time()
    
    # Define work hour boundaries
    WORK_START_TIME = time(8, 0)  # 8:00 AM
    WORK_END_TIME = time(17, 0)   # 5:00 PM
    
    # For time_in action
    if action == 'time_in':
        # Check if employee already has an active session
        today_attendance = Attendance.objects.filter(
            employee=employee, 
            date=today,
            time_in__isnull=False,
            time_out__isnull=True
        ).first()
        
        if today_attendance:
            # Already has an open session
            return {
                'status': 'success',
                'message': f'Already timed in at {today_attendance.time_in.strftime("%I:%M %p")}.',
                'has_open_session': True
            }
        
        try:
            # Create new attendance record
            attendance = Attendance(
                employee=employee,
                date=today,
                time_in=current_time,
                attendance_status=Attendance.AttendanceStatus.PRESENT
            )
            attendance.save()
            
            return {
                'status': 'success',
                'message': f'Time in recorded at {current_time.strftime("%I:%M %p")}.',
                'employee_name': f'{employee.first_name} {employee.last_name}',
                'employee_id': employee.employee_id,
                'time': current_time.strftime("%I:%M %p"),
                'has_open_session': True
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error recording time in: {str(e)}'
            }
    
    # For time_out action
    elif action == 'time_out':
        try:
            # Find today's attendance record with an open session
            today_attendance = Attendance.objects.filter(
                employee=employee, 
                date=today,
                time_in__isnull=False,
                time_out__isnull=True
            ).first()
            
            if not today_attendance:
                return {
                    'status': 'warning', 
                    'message': 'No active session found to time out from.'
                }
            
            # Record time out
            today_attendance.time_out = current_time
            today_attendance.save()
            
            # Calculate hours worked
            today_attendance.calculate_hours_worked()
            
            # Format the time for display
            formatted_hours = today_attendance.get_formatted_hours_worked()
            
            return {
                'status': 'success',
                'message': f'Time out recorded at {current_time.strftime("%I:%M %p")}. You worked {formatted_hours}.',
                'employee_name': f'{employee.first_name} {employee.last_name}',
                'employee_id': employee.employee_id,
                'time': current_time.strftime("%I:%M %p"),
                'hours_worked': formatted_hours,
                'has_open_session': False
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error recording time out: {str(e)}'
            }
    
    return {
        'status': 'error',
        'message': 'Invalid action specified.'
    }

# Process a single frame from the web interface
def process_frame_recognition(frame):
    """
    Process a video frame to recognize faces with improved detection
    """
    # Debug flag
    debug = True
    
    # Make sure we have a valid frame
    if frame is None or frame.size == 0:
        return {'status': 'error', 'message': 'Invalid frame received'}
    
    # Increase detection reliability by trying multiple sizes
    # First try normal size
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    
    # If no face detected, try with smaller resize
    if not face_locations:
        if debug:
            print("No face detected at normal size, trying smaller size")
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        
        # If still no face detected, try with different size
        if not face_locations:
            if debug:
                print("No face detected at half size, trying quarter size")
            smaller_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_smaller_frame = cv2.cvtColor(smaller_frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_smaller_frame, model="hog")
            
            if face_locations:
                if debug:
                    print(f"Face detected at quarter size: {face_locations}")
                # Use the quarter size frame for encoding
                frame_to_use = rgb_smaller_frame
            else:
                return {'status': 'waiting', 'message': 'No face detected'}
        else:
            if debug:
                print(f"Face detected at half size: {face_locations}")
            # Use the half size frame for encoding
            frame_to_use = rgb_small_frame
    else:
        if debug:
            print(f"Face detected at normal size: {face_locations}")
        # Use the normal size frame for encoding
        frame_to_use = rgb_frame
    
    # Get the largest face by area
    largest_face = max(face_locations, key=lambda rect: (rect[2]-rect[0])*(rect[3]-rect[1]))
    
    # Try to encode the face
    face_encodings = face_recognition.face_encodings(frame_to_use, [largest_face])
    
    if not face_encodings:
        return {'status': 'waiting', 'message': 'Cannot encode face'}
    
    face_encoding = face_encodings[0]
    
    # Load face database (uses cached version after first call)
    registered_faces, employee_names = load_registered_faces()
    
    if not registered_faces:
        return {'status': 'error', 'message': 'No registered faces available'}
    
    # Check against all registered faces
    best_match = None
    best_distance = 1.0  # Lower is better, 0 is perfect match
    
    for employee_id, known_encoding in registered_faces.items():
        match, distance = compare_faces(known_encoding, face_encoding)
        
        if debug:
            print(f"Employee {employee_id}: Match={match}, Distance={distance}")
        
        if match and distance < best_distance:
            best_match = employee_id
            best_distance = distance
    
    if best_match:
        return {
            'status': 'recognized',
            'employee_id': best_match,
            'name': employee_names[best_match],
            'confidence': 1 - best_distance  # Convert distance to confidence (0-1)
        }
    
    return {'status': 'unknown', 'message': 'Face not recognized'}