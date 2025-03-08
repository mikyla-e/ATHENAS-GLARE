import cv2
import numpy as np
import face_recognition
from django.utils.timezone import now
from .models import Employee, Attendance

# Load and encode registered faces
def load_registered_faces():
    registered_faces = {}  # Store encoded faces

    for employee in Employee.objects.all():
        if not employee.employee_image:  # Skip employees without images
            print(f"Skipping {employee.first_name} (No image uploaded)")
            continue  

        image_path = employee.employee_image.path
        image = face_recognition.load_image_file(image_path)
        
        # Get the face encoding (assuming only one face per image)
        face_encodings = face_recognition.face_encodings(image)

        if not face_encodings:  # Ensure a face was found
            print(f"Warning: No face detected in {employee.first_name}'s image.")
            continue

        registered_faces[employee.employee_id] = face_encodings[0]  # Store the first encoding

    return registered_faces


# Compare captured face with stored face encodings
def compare_faces(known_encoding, captured_encoding):
    """Returns True if the face matches, False otherwise."""
    distance = np.linalg.norm(known_encoding - captured_encoding)
    return distance < 0.6  # Threshold for recognition (adjust if needed)


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


# Start real-time face recognition
def recognize_face(employee_id):
    registered_faces = load_registered_faces()  # Load saved faces

    if str(employee_id) not in registered_faces:
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
            if compare_faces(registered_faces[employee_id], face_encoding):
                employee = Employee.objects.get(employee_id=employee_id)
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