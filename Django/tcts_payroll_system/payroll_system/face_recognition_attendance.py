import cv2
import numpy as np
import os
from django.utils.timezone import now
from .models import Employee, Attendance

# Load saved face images
def train_face_recognizer():
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()  # Create recognizer
    faces = []
    labels = []

    for employee in Employee.objects.all():
        if not employee.employee_image:
            print(f"Skipping {employee.first_name} (No image uploaded)")
            continue  

        image_path = employee.employee_image.path
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            print(f"Error loading image for {employee.first_name}")
            continue

        faces.append(image)
        labels.append(int(employee.employee_id))  # Use employee ID as label

    if faces:
        face_recognizer.train(faces, np.array(labels))  # Train the recognizer

    return face_recognizer


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
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0)
    
    face_recognizer = train_face_recognizer()  # Train the recognizer

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.2, minNeighbors=7, minSize=(100, 100))

        for (x, y, w, h) in faces:
            captured_face = gray_frame[y:y+h, x:x+w]
            
            # Predict the recognized employee ID
            label, confidence = face_recognizer.predict(captured_face)

            if label == int(employee_id) and confidence < 50:  # Adjust confidence threshold
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