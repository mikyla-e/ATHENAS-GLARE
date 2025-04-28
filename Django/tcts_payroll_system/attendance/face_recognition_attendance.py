import os
import cv2
import pytz
import face_recognition
from datetime import date, datetime, timedelta
from functools import lru_cache
from payroll_system.models import Employee, Attendance

# Cache the face encodings to avoid reloading them for every frame
@lru_cache(maxsize=1)
def load_registered_faces():
    registered_faces = {}
    employee_names = {}
    employees = Employee.objects.all()
    
    for employee in employees:
        if employee.employee_image:
            try:
                image_path = employee.employee_image.path
                
                if os.path.exists(image_path):
                    # Reduce image size for faster processing before encoding
                    image = cv2.imread(image_path)
                    if image is None:
                        continue
                    
                    # Resize image to 1/4 size for faster processing
                    small_image = cv2.resize(image, (0, 0), fx=0.25, fy=0.25)
                    rgb_small_image = cv2.cvtColor(small_image, cv2.COLOR_BGR2RGB)
                    
                    # Try to detect faces first - use HOG model for speed
                    face_locations = face_recognition.face_locations(rgb_small_image, model="hog")
                    
                    if face_locations:
                        # Only encode if we actually found a face
                        encodings = face_recognition.face_encodings(rgb_small_image, face_locations)

                        if len(encodings) > 0:
                            employee_id = str(employee.employee_id)
                            registered_faces[employee_id] = encodings[0]
                            employee_names[employee_id] = f"{employee.first_name} {employee.last_name}"
                            
            except Exception:
                pass

    return registered_faces, employee_names

def compare_faces(known_encoding, captured_encoding):
    # Returns True if the face matches, False otherwise.
    # The tolerance value controls strictness: lower = stricter (0.6 is lenient)
    match = face_recognition.compare_faces([known_encoding], captured_encoding, tolerance=0.55)[0]
    
    # For additional security, also check the distance
    distance = face_recognition.face_distance([known_encoding], captured_encoding)[0]
    
    # Return True only if the built-in comparison says it's a match AND the distance is small enough
    return match and distance < 0.6  # Slightly more lenient for web camera

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
        employee_id_fk=employee,
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
    history_query = Attendance.objects.filter(employee_id_fk=employee)
    
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
        employee_id_fk=employee,
        date=today
    ).order_by('time_in')
    
    # Get history logs within the date range
    history_logs = Attendance.objects.filter(
        employee_id_fk=employee,
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
        
def mark_attendance(employee, action=None):
    timezone_ph = pytz.timezone("Asia/Manila")
    time_now = datetime.now(timezone_ph)
    
    today = time_now.strftime("%Y-%m-%d")
    current_time = time_now.strftime("%H:%M:%S")
    
    # Get current status
    status_info = check_attendance_status(employee)
    has_open_session = status_info["has_open_session"]
    
    # Handle time_in action
    if action == "time_in" or (action is None and not has_open_session):
        if has_open_session:
            return {
                "status": "warning", 
                "message": f"You already have an open session. Please time out first."
            }
        
        # Create new time in entry
        try:
            log = Attendance.objects.create(
                employee_id_fk=employee, 
                date=today,
                time_in=current_time,
                time_out=None
            )
                
            return {
                "status": "success", 
                "message": f"Time In recorded: {employee.first_name} at {current_time}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # Handle time_out action
    elif action == "time_out" or (action is None and has_open_session):
        if not has_open_session:
            return {
                "status": "warning", 
                "message": f"No open session found for {employee.first_name}. Please time in first."
            }
        
        # Update open session with time_out
        try:
            # Get the open session ID
            if 'current_log_id' in status_info:
                log = Attendance.objects.get(
                    attendance_id=status_info["current_log_id"],
                    employee_id_fk=employee
                )
                log.time_out = current_time
                log.save()
                
                return {
                    "status": "success", 
                    "message": f"Time Out recorded: {employee.first_name} at {current_time}"
                }
            else:
                # Fallback if we don't have the ID (should not happen with the updated code)
                open_log = Attendance.objects.filter(
                    employee_id_fk=employee,
                    date=today,
                    time_in__isnull=False,
                    time_out__isnull=True
                ).first()
                
                if open_log:
                    open_log.time_out = current_time
                    open_log.save()
                    return {
                        "status": "success", 
                        "message": f"Time Out recorded: {employee.first_name} at {current_time}"
                    }
                else:
                    return {
                        "status": "error", 
                        "message": "Could not find the open session to time out."
                    }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # Default fallback
    return {"status": "error", "message": "Invalid action"}

# Process a single frame from the web interface
def process_frame_recognition(frame):
    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    
    # Convert to RGB for face_recognition library
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    # Find faces in the frame - use HOG model for speed
    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
    
    if not face_locations:
        return {'status': 'waiting', 'message': 'No face detected'}
    
    # Process the first (largest) face
    face_location = face_locations[0]
    face_encodings = face_recognition.face_encodings(rgb_small_frame, [face_location])
    
    if not face_encodings:
        return {'status': 'waiting', 'message': 'Cannot encode face'}
    
    face_encoding = face_encodings[0]
    
    # Load face database (uses cached version after first call)
    registered_faces, employee_names = load_registered_faces()
    
    # Check against all registered faces
    for employee_id, known_encoding in registered_faces.items():
        if compare_faces(known_encoding, face_encoding):
            # Match found
            return {
                'status': 'recognized',
                'employee_id': employee_id,
                'name': employee_names[employee_id],
            }
    
    return {'status': 'unknown', 'message': 'Face not recognized'}