import cv2
import numpy as np
import os
from PIL import Image

def get_image_sharpness(gray_img):
    """Calculates the Laplacian variance to measure blur/sharpness."""
    return cv2.Laplacian(gray_img, cv2.CV_64F).var()

def preprocess_image_for_ocr(image_path, output_path=None):
    """
    Applies gentle preprocessing to optimize image for OCR without destructive degradation.
    - Resizes if oversized (> 3000px) or too tiny (< 600px width)
    - Grayscale conversion
    - Contrast enhancement (CLAHE) if low contrast
    - Slight denoising if needed
    """
    try:
        if not os.path.exists(image_path):
            return image_path
            
        # Read image using OpenCV (support unicode paths via cv2.imdecode)
        with open(image_path, 'rb') as f:
            bytes_data = bytearray(f.read())
            numpy_array = np.asarray(bytes_data, dtype=np.uint8)
            img = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            
        if img is None:
            return image_path

        h, w = img.shape[:2]
        
        # Resize if too large
        max_dim = 2500
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]
            
        # Resize if too small for legible OCR
        if w < 700:
            scale = 800.0 / float(w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            
        # Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Check contrast: if low variance, apply CLAHE
        if gray.std() < 50:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(gray)
        else:
            processed = gray

        # Mild sharpening if blurry
        sharpness = get_image_sharpness(processed)
        if sharpness < 100:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            processed = cv2.filter2D(processed, -1, kernel)

        if not output_path:
            output_path = os.path.splitext(image_path)[0] + "_proc.png"

        # Save processed image safely
        success, encoded_img = cv2.imencode('.png', processed)
        if success:
            with open(output_path, 'wb') as f:
                f.write(encoded_img)
            return output_path
            
        return image_path
    except Exception as e:
        # Fallback to original image on any processing error
        return image_path
