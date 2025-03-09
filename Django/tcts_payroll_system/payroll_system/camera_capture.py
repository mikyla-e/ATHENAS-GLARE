import cv2
import os
import numpy as np
from django.http import JsonResponse
from django.core.files.base import ContentFile
from .models import Employee
from django.conf import settings

TEMP_DIR = os.path.join(settings.MEDIA_ROOT, "temp")  # Temporary storage for images
os.makedirs(TEMP_DIR, exist_ok=True)

def get_next_image_name():
    """Generates a unique image filename based on the database records."""
    count = Employee.objects.count() + 1
    return f"captured_image_{count}.jpg"

def capture_image(request):
   
    if request.method == "POST":
        
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return JsonResponse({"success": False, "error": "Could not access the camera."})

        while True:
            ret, frame = camera.read()
            if not ret:
                return JsonResponse({"success": False, "error": "Failed to capture frame."})

            cv2.imshow("Press SPACE to Capture, ESC to Exit", frame)
            key = cv2.waitKey(1) & 0xFF 

            if key == 32:  # SPACE key - Capture Image
                image_name = get_next_image_name()
                image_path = os.path.join(TEMP_DIR, image_name)

                cv2.imwrite(image_path, frame)  # Save image temporarily

                camera.release()
                cv2.destroyAllWindows()

                return JsonResponse({"success": True, "image_url": f"/media/temp/{image_name}"})

            elif key == 27:  # ESC key - Cancel capture
                camera.release()
                cv2.destroyAllWindows()
                return JsonResponse({"success": False, "error": "Image capture cancelled."})

    return JsonResponse({"success": False, "error": "Invalid request."})
