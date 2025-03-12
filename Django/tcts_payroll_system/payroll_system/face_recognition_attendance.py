import os
import cv2
import pytz
import face_recognition
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
                            # Store the employee's name
                            employee_names[employee_id] = f"{employee.first_name} {employee.last_name}"
                        else:
                            print(f"No encodings generated for employee {employee.employee_id}")
                    else:
                        print(f"No face detected in image for employee {employee.employee_id}")
                else:
                    print(f"Image does not exist at path: {image_path}")
            except Exception as e:
                print(f"Error processing image for employee {employee.employee_id}: {str(e)}")

    return registered_faces, employee_names

def compare_faces(known_encoding, captured_encoding):
    # Returns True if the face matches, False otherwise.
    match = face_recognition.compare_faces([known_encoding], captured_encoding, tolerance=0.4)[0]
    
    # For additional security, also check the distance
    distance = face_recognition.face_distance([known_encoding], captured_encoding)[0]
    print(f"Face match: {match}, distance: {distance}")  # Helpful for debugging
    
    # Return True only if the built-in comparison says it's a match AND the distance is small enough
    return match and distance < 0.5

def mark_attendance(employee):
    timezone_ph = pytz.timezone("Asia/Manila")
    time_in_ph = datetime.now(timezone_ph)
    
    today = time_in_ph.strftime("%Y-%m-%d")
    current_time = time_in_ph.strftime("%H:%M:%S")
    
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

def recognize_face(employee_id):
    registered_faces, employee_names = load_registered_faces()
    employee_id = str(employee_id)

    if employee_id not in registered_faces:
        return "Employee not found or no image uploaded."

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Initialize a counter for consecutive successful matches
    consecutive_matches = 0
    required_matches = 2  # Require 2 consecutive matches for confirmation
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if face_locations:
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Draw rectangle around face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Check if face matches the registered employee
                if compare_faces(registered_faces[employee_id], face_encoding):
                    consecutive_matches += 1
                    
                    # Display employee name in green
                    name = employee_names[employee_id]
                    cv2.putText(frame, name, (left, top - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                    
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
                    
                    # Display "Unknown" in red
                    cv2.putText(frame, "Unknown", (left, top - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
        
        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return "Face not recognized. Please try again."