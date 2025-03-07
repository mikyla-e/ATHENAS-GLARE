import cv2
import numpy as np
import os
from django.utils.timezone import now
from .models import Employee, Attendance

# Load saved face images
def load_registered_faces():
    face_encodings = {}
    for employee in Employee.objects.all():
        if not employee.employee_image:  # Check if the image exists
            print(f"Skipping {employee.first_name} (No image uploaded)")
            continue  # Skip this employee

        image_path = employee.employee_image.path
        image = cv2.imread(image_path)
        
        if image is None:  # Ensure image loads correctly
            print(f"Error loading image for {employee.first_name}")
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_encodings[employee.employee_id] = gray

    return face_encodings

# Compare captured face with stored face
def compare_faces(known_face, captured_face):
    try:
        difference = np.linalg.norm(known_face - captured_face)
        return difference < 3000  # Adjust threshold as needed
    except:
        return False

# Mark attendance (time in/out)
def mark_attendance(employee):
    today = now().date()
    current_time = now().time()

    attendance, created = Attendance.objects.get_or_create(employee=employee, date=today)

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

# Start face recognition
def recognize_face(employee_id):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)  # Open webcam
    registered_faces = load_registered_faces()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            captured_face = gray_frame[y:y+h, x:x+w]

            if employee_id in registered_faces and compare_faces(registered_faces[employee_id], captured_face):
                employee = Employee.objects.get(employee_id=employee_id)
                message = mark_attendance(employee)
                cap.release()
                cv2.destroyAllWindows()
                return message

        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return "Face not recognized. Please try again."