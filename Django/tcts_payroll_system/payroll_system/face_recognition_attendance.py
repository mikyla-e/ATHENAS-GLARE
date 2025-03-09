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
            print(f"Employee ID: {employee.employee_id}, Image path: {employee.employee_image.name}")
            try:
                # Get the actual path from the database
                image_path = employee.employee_image.path
                
                # Debug info
                print(f"Loading face for employee {employee.employee_id} from {image_path}")
                
                # Check if the file exists
                if os.path.exists(image_path):
                    image = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(image)
                    
                    if len(encodings) > 0:
                        registered_faces[str(employee.employee_id)] = encodings[0]
                    else:
                        print(f"No face found in image for employee employee_id: {employee.id}")
                else:
                    print(f"Image does not exist at path: {image_path}")
            except Exception as e:
                print(f"Error processing image for employee {employee.employee_id}: {str(e)}")
    
    return registered_faces


# Compare captured face with stored face encodings
def compare_faces(known_encoding, captured_encoding):
    """Returns True if the face matches, False otherwise."""
    distance = np.linalg.norm(known_encoding - captured_encoding)
    return distance < 0.6  # Threshold for recognition (adjust if needed)


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
    registered_faces = load_registered_faces()  # Load saved faces
    employee_id = str(employee_id)  # Ensure consistent key type

    print(f"Checking employee_id type: {type(employee_id)}, Value: {employee_id}")
    print("Loaded registered faces keys:", registered_faces.keys())

    if employee_id not in registered_faces:
        return "Employee not found or no image uploaded."

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow on Windows for better webcam handling

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB (face_recognition expects RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            if compare_faces(registered_faces[employee_id], face_encoding):   # No list wrapping
                try:
                    employee = Employee.objects.get(employee_id=employee_id)
                except Employee.DoesNotExist:
                    return "Employee record not found."

                message = mark_attendance(employee)

                cap.release()
                cv2.destroyAllWindows()
                return message

        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):  # Press 'q' to exit
            break

    cap.release()
    cv2.destroyAllWindows()
    return "Face not recognized. Please try again."