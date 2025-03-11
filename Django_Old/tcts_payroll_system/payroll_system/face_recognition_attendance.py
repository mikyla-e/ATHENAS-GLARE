import cv2
import os
import numpy as np
import face_recognition
from django.utils.timezone import now
from .models import Employee, Attendance
from datetime import datetime
import pytz

# Load and encode registered faces
def load_registered_faces():
    registered_faces = {}
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
                            registered_faces[str(employee.employee_id)] = encodings[0]
                        else:
                            print(f"No encodings generated for employee {employee.employee_id}")
                    else:
                        print(f"No face detected in image for employee {employee.employee_id}")
                else:
                    print(f"Image does not exist at path: {image_path}")
            except Exception as e:
                print(f"Error processing image for employee {employee.employee_id}: {str(e)}")
    
    return registered_faces


# Compare captured face with stored face encodings
def compare_faces(known_encoding, captured_encoding):
    """Returns True if the face matches, False otherwise."""
    # Use face_recognition's built-in comparison instead of manual distance
    # This is more reliable than a simple Euclidean distance
    match = face_recognition.compare_faces([known_encoding], captured_encoding, tolerance=0.4)[0]
    
    # For additional security, also check the distance
    distance = face_recognition.face_distance([known_encoding], captured_encoding)[0]
    print(f"Face match: {match}, distance: {distance}")  # Helpful for debugging
    
    # Return True only if the built-in comparison says it's a match AND the distance is small enough
    return match and distance < 0.5


# Mark attendance (time in/out)
def mark_attendance(employee):
    timezone_ph = pytz.timezone("Asia/Manila")
    time_in_ph = datetime.now(timezone_ph)
    
    today = time_in_ph.strftime("%Y-%m-%d")
    current_time = time_in_ph.strftime("%H:%M:%S")
    # today = now().date()
    # current_time = now().time()

    attendance, created = Attendance.objects.get_or_create(employee_id_fk=employee, date=today)

    if created or attendance.time_in is None:
        attendance.time_in = current_time
        message = f"Time In recorded: {employee.first_name} at {current_time}"
    elif attendance.time_out is None:
        attendance.time_out = current_time
        message = f"Time Out recorded: {employee.first_name} at {current_time}"
    else:
        message = f"{employee.first_name} has already timed out today."

    attendance.save()
    return message


# Start real-time face recognition
def recognize_face(employee_id):
    registered_faces = load_registered_faces()
    employee_id = str(employee_id)

    if employee_id not in registered_faces:
        return "Employee not found or no image uploaded."

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Initialize a counter for consecutive successful matches
    # This helps prevent false positives from a single frame
    consecutive_matches = 0
    required_matches = 3  # Require 3 consecutive matches for confirmation
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        # Draw rectangles around detected faces
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        if face_locations:
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for face_encoding in face_encodings:
                if compare_faces(registered_faces[employee_id], face_encoding):
                    consecutive_matches += 1
                    # Display match confidence on screen
                    distance = face_recognition.face_distance([registered_faces[employee_id]], face_encoding)[0]
                    confidence = f"Match: {100 * (1 - distance):.1f}%"
                    cv2.putText(frame, confidence, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    if consecutive_matches >= required_matches:
                        try:
                            employee = Employee.objects.get(employee_id=employee_id)
                        except Employee.DoesNotExist:
                            return "Employee record not found."

                        message = mark_attendance(employee)
                        cap.release()
                        cv2.destroyAllWindows()
                        return message
                else:
                    consecutive_matches = 0  # Reset on any non-match
                    
        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return "Face not recognized. Please try again."