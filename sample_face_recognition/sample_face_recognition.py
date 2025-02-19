import face_recognition
import cv2
import numpy as np
import csv
import os
from datetime import datetime

video_capture = cv2.VideoCapture(0)

# Function to load and encode a single face
def load_face_encoding(image_path, name):
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            return encodings[0]
        else:
            print(f"Warning: No face found in {name}.jpg")
            return None
    except Exception as e:
        print(f"Error loading {name}.jpg: {e}")
        return None

# Load known faces
face_data = {
    "ejay": r"C:\\Users\\Acer\\Desktop\\ATHENAS-GLARE\\face_recognition\\sample_face_recognition\\photos\\ejay.jpg",
    "aaron": r"C:\\Users\\Acer\\Desktop\\ATHENAS-GLARE\\face_recognition\\sample_face_recognition\\photos\\aaron.jpg",
    "tappy": r"C:\\Users\\Acer\\Desktop\\ATHENAS-GLARE\\face_recognition\\sample_face_recognition\\photos\\tappy.jpg",
}

known_face_encoding = []
known_face_name = []

for name, path in face_data.items():
    encoding = load_face_encoding(path, name)
    if encoding is not None:
        known_face_encoding.append(encoding)
        known_face_name.append(name)

# Ensure there are known faces
if not known_face_encoding:
    print("No faces were loaded. Exiting...")
    exit()

students = known_face_name.copy()

face_locations = []
face_encodings = []
face_names = []
s = True

now = datetime.now()
current_date = now.strftime("%Y-%m-%d")

# Open CSV file
f = open(current_date + '.csv', 'w+', newline='')
lnwriter = csv.writer(f)

while True:
    ret, frame = video_capture.read()
    if not ret:
        print("Failed to capture frame.")
        break
    
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)  # Resize for faster processing
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)  # Ensure correct color format

    if s:
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        if not face_locations:
            print("No faces detected in the frame.")
            continue  # Skip to the next loop iteration

        print(f"Detected {len(face_locations)} face(s).")

        # Extract face encodings
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        if not face_encodings:
            print("No face encodings found, skipping frame.")
            continue

        face_names = []

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encoding, face_encoding)
            name = "Unknown"

            if any(matches):
                face_distance = face_recognition.face_distance(known_face_encoding, face_encoding)
                best_match_index = np.argmin(face_distance)
                if matches[best_match_index]:
                    name = known_face_name[best_match_index]

            face_names.append(name)

            if name in students:
                students.remove(name)
                print(f"{name} marked as present.")
                current_time = datetime.now().strftime("%H:%M:%S")
                lnwriter.writerow([name, current_time])

    cv2.imshow("Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()
f.close()
