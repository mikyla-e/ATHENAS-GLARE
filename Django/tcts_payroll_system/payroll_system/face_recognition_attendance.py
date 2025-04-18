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
3
#New
def calculate_face_movement(previous_location, current_location):
    #Calculate how much a face has moved between frames
    if previous_location is None or current_location is None:
        return float('inf') #large value signifies movements
    
    # Calculate center points of previous and current face bounding boxes
    prev_center = ((previous_location[1] + previous_location[3]) // 2, 
                  (previous_location[0] + previous_location[2]) // 2)
    curr_center = ((current_location[1] + current_location[3]) // 2, 
                  (current_location[0] + current_location[2]) // 2)
    
    # Calculate Euclidean distance between centers
    movement = np.sqrt((prev_center[0] - curr_center[0])**2 + 
                       (prev_center[1] - curr_center[1])**2)
    
    return movement

def recognize_face(employee_id):
    registered_faces, employee_names = load_registered_faces()
    employee_id = str(employee_id)

    if employee_id not in registered_faces:
        return "Employee not found or no image uploaded."

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Initialize a counter for consecutive successful matches
    consecutive_matches = 0
    required_matches = 2  # Require 2 consecutive matches for confirmation
    
    # NEW: Stability detection
    stability_frames = 0
    required_stability_frames = 45  # ~3 seconds at 30fps
    previous_face_location = None
    stability_threshold = 10  # Maximum allowed movement to be considered "stable"
    stable_face_detected = False
    recognition_started = False
    
    status_text = "Waiting for face..."
    status_color = (0, 0, 255) #Red
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        # MODIFIED: This entire if-else block is restructured
        if face_locations:
            # We only check the first face found (largest/closest)
            face_location = face_locations[0]
            top, right, bottom, left = face_location
            
            # NEW: Added stability check before starting recognition
            if not stable_face_detected:
                # Check if the face is stable
                movement = calculate_face_movement(previous_face_location, face_location)
                
                if movement < stability_threshold:
                    stability_frames += 1
                    progress = min(stability_frames / required_stability_frames, 1.0)
                    
                    # Update status with progress
                    if stability_frames < required_stability_frames:
                        seconds_left = (required_stability_frames - stability_frames) / 30
                        status_text = f"Hold still: {seconds_left:.1f}s left"
                        # status_color = (0, 165, 255)  # Orange
                        
                        # # Draw progress bar
                        # cv2.rectangle(frame, (left, bottom + 20), (left + 200, bottom + 40), (0, 0, 0), cv2.FILLED)
                        # cv2.rectangle(frame, (left, bottom + 20), (left + int(200 * progress), bottom + 40), (0, 165, 255), cv2.FILLED)
                else:
                    # Reset stability count if there's significant movement
                    stability_frames = 0
                
                # If stable for required period, start recognition
                if stability_frames >= required_stability_frames:
                    stable_face_detected = True
                    status_text = "Face stable! Starting recognition..."
                    status_color = (0, 255, 0)  # Green
            
            # Store current face location for next iteration
            previous_face_location = face_location
                
            # Draw rectangle around face (this was in the original code)
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            
            # MODIFIED: Original code immediately processed face recognition
            # New code only does recognition after stability is confirmed
            if stable_face_detected:
                if not recognition_started:
                    recognition_started = True
                    status_text = "Recognizing face..."
                    status_color = (255, 255, 0)  # Cyan
                
                # This part is from original code but moved inside stability check
                face_encodings = face_recognition.face_encodings(rgb_frame, [face_location])
                if face_encodings:
                    face_encoding = face_encodings[0]
                    
                    # Check if face matches the registered employee
                    if compare_faces(registered_faces[employee_id], face_encoding):
                        consecutive_matches += 1
                        name = employee_names[employee_id]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        
                        # NEW: Added status text
                        status_text = f"Matching... ({consecutive_matches}/{required_matches})"
                        status_color = (0, 255, 0)  # Green
                        
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
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.putText(frame, "Unknown", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                        
                        # NEW: Added status text
                        status_text = "Face doesn't match registered employee"
                        status_color = (0, 0, 255)  # Red
        else:
            # NEW: Reset stability if no face is detected
            stability_frames = 0
            previous_face_location = None
            stable_face_detected = False
            recognition_started = False
            status_text = "Waiting for face..."
        
        # NEW: Display status text at the bottom of the frame
        cv2.putText(frame, status_text, (10, frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        cv2.imshow("Face Recognition Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    # MODIFIED: Slightly changed return message
    return "Face not recognized or process cancelled. Please try again."