import os
import cv2
import pytz
import face_recognition
import numpy as np
from datetime import datetime
from payroll_system.models import Employee, Attendance

def load_registered_faces():
    registered_faces = {}
    employee_names = {}
    employees = Employee.objects.all()
    
    for employee in employees:
        if employee.employee_image:
            try:
                image_path = employee.employee_image.path
                
                if os.path.exists(image_path):
                    image = face_recognition.load_image_file(image_path)
                    
                    # Try to detect faces first
                    face_locations = face_recognition.face_locations(image)
                    
                    if face_locations:
                        
                        # Only encode if we actually found a face
                        encodings = face_recognition.face_encodings(image, face_locations)

                        if len(encodings) > 0:
                            employee_id = str(employee.employee_id)
                            registered_faces[employee_id] = encodings[0]
                            employee_names[employee_id] = f"{employee.first_name} {employee.last_name}"
                            
            except Exception:
                pass

    return registered_faces, employee_names

def compare_faces(known_encoding, captured_encoding):
    
    # Returns True if the face matches, False otherwise.
    match = face_recognition.compare_faces([known_encoding], captured_encoding, tolerance=0.5)[0]
    
    # For additional security, also check the distance
    distance = face_recognition.face_distance([known_encoding], captured_encoding)[0]
    
    # Return True only if the built-in comparison says it's a match AND the distance is small enough
    return match and distance < 0.6  # Slightly more lenient for web camera

def check_attendance_status(employee):
    timezone_ph = pytz.timezone("Asia/Manila")
    today = datetime.now(timezone_ph).strftime("%Y-%m-%d")
    
    # Get all attendance logs for today
    logs = Attendance.objects.filter(employee_id_fk=employee, date=today).order_by('created_at')
    
    logs_data = []
    for log in logs:
        logs_data.append({
            "time_in": log.time_in.strftime("%H:%M:%S") if log.time_in else None,
            "time_out": log.time_out.strftime("%H:%M:%S") if log.time_out else None,
        })
    
    # Check if we have an "open" session (time_in without time_out)
    open_session = logs.filter(time_out__isnull=True).first()
    
    return {
        "status": "success",
        "has_open_session": open_session is not None,
        "logs": logs_data,
        "current_log_id": open_session.attendance_id if open_session else None
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
    if action == "time_in":
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
    elif action == "time_out":
        if not has_open_session:
            # Create an attendance record with only time_out for admin to fix later
            try:
                log = Attendance.objects.create(
                    employee_id_fk=employee, 
                    date=today,
                    time_in=None,
                    time_out=current_time
                )
                
                return {
                    "status": "warning", 
                    "message": f"Time Out recorded without Time In. Admin will need to adjust this."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}
        
        # Update open session with time_out
        try:
            log = Attendance.objects.get(
                attendance_id=status_info["current_log_id"],
                employee_id_fk=employee, 
                date=today
            )
            log.time_out = current_time
            log.save()
            
            return {
                "status": "success", 
                "message": f"Time Out recorded: {employee.first_name} at {current_time}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # Default behavior (for backward compatibility)
    else:
        if has_open_session:
            
            # Close open session
            try:
                log = Attendance.objects.get(attendance_id=status_info["current_log_id"])
                log.time_out = current_time
                log.save()
                message = f"Time Out recorded: {employee.first_name} at {current_time}"
                status = "success"
            except Exception as e:
                message = f"Error: {str(e)}"
                status = "error"
        else:
            # Create new session
            try:
                log = Attendance.objects.create(
                    employee_id_fk=employee, 
                    date=today,
                    time_in=current_time,
                    time_out=None
                )
                message = f"Time In recorded: {employee.first_name} at {current_time}"
                status = "success"
            except Exception as e:
                message = f"Error: {str(e)}"
                status = "error"
                
        return {"message": message, "status": status}

# Process a single frame from the web interface
def process_frame_recognition(frame):
    registered_faces, employee_names = load_registered_faces()
    
    # Convert to RGB for face_recognition library if not already in RGB format
    if len(frame.shape) == 3 and frame.shape[2] == 3:
        if frame.dtype == np.uint8:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = frame  # Assume it's already RGB
    else:
        return {'status': 'error', 'message': 'Invalid frame format'}
    
    # Find faces in the frame
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if not face_locations:
        return {'status': 'waiting', 'message': 'No face detected'}
    
    # Process the first (largest) face
    face_location = face_locations[0]
    face_encodings = face_recognition.face_encodings(rgb_frame, [face_location])
    
    if not face_encodings:
        return {'status': 'waiting', 'message': 'Cannot encode face'}
    
    face_encoding = face_encodings[0]
    
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