import os
import cv2
import pytz
import face_recognition
import numpy as np
from datetime import datetime
from .models import Employee, Attendance

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

def mark_attendance(employee):
    timezone_ph = pytz.timezone("Asia/Manila")
    time_in_ph = datetime.now(timezone_ph)
    
    today = time_in_ph.strftime("%Y-%m-%d")
    current_time = time_in_ph.strftime("%H:%M:%S")
    
    # Check for existing attendance records for today
    try:
        attendance = Attendance.objects.get(employee_id_fk=employee, date=today)
        
        # Employee has an attendance record for today
        if attendance.time_in is not None and attendance.time_out is None:
            
            # They've timed in but not out yet
            attendance.time_out = current_time
            attendance.save()
            message = f"Time Out recorded: {employee.first_name} at {current_time}"
            status = "success"
        elif attendance.time_in is not None and attendance.time_out is not None:
            
            # They've already timed in and out
            message = "Already recorded"
            status = "warning"  # New status for already recorded
        else:
            
            # This shouldn't happen normally, but just in case there's a record with no time_in
            attendance.time_in = current_time
            attendance.save()
            message = f"Time In recorded: {employee.first_name} at {current_time}"
            status = "success"
            
    except Attendance.DoesNotExist:
        
        # No attendance record for today, create one for time in
        attendance = Attendance.objects.create(
            employee_id_fk=employee, 
            date=today,
            time_in=current_time,
            time_out=None
        )
        message = f"Time In recorded: {employee.first_name} at {current_time}"
        status = "success"
    except Attendance.MultipleObjectsReturned:
        
        # Handle case where multiple records exist (data inconsistency)
        # Get the first record and update it
        attendance = Attendance.objects.filter(employee_id_fk=employee, date=today).first()
        
        if attendance.time_out is None:
            attendance.time_out = current_time
            attendance.save()
            message = f"Time Out recorded: {employee.first_name} at {current_time}"
            status = "success"
        else:
            message = "Already recorded"
            status = "warning"  # New status for already recorded
    
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