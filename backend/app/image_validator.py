"""
Stage A: Image Safety and Quality Gate.
Validates uploaded images for corruption, blur, brightness, and minimum size.
Uses pure PIL/numpy — no OpenCV dependency (saves ~200MB RAM).
"""
import io
import numpy as np
from PIL import Image, ImageFilter, UnidentifiedImageError
from app.settings import (
    MAX_FILE_SIZE_BYTES, ALLOWED_MIME_TYPES, MIN_IMAGE_DIMENSION,
    BLUR_THRESHOLD, BRIGHTNESS_LOW, BRIGHTNESS_HIGH
)


def _laplacian_variance(gray_array: np.ndarray) -> float:
    """
    Compute Laplacian variance for blur detection using pure numpy.
    Equivalent to cv2.Laplacian(gray, cv2.CV_64F).var().
    """
    # 3x3 Laplacian kernel
    kernel = np.array([[0, 1, 0],
                       [1, -4, 1],
                       [0, 1, 0]], dtype=np.float64)

    # Resize to a manageable size to save memory and speed up
    h, w = gray_array.shape
    if h > 512 or w > 512:
        from PIL import Image as _Img
        pil_gray = _Img.fromarray(gray_array)
        pil_gray = pil_gray.resize((min(w, 512), min(h, 512)), _Img.BILINEAR)
        gray_array = np.array(pil_gray, dtype=np.float64)
    else:
        gray_array = gray_array.astype(np.float64)

    h, w = gray_array.shape
    # Pad image
    padded = np.pad(gray_array, 1, mode='edge')
    # Apply convolution using fast NumPy slicing
    result = padded[0:h, 1:1+w] + padded[2:2+h, 1:1+w] + padded[1:1+h, 0:w] + padded[1:1+h, 2:2+w] - 4.0 * gray_array

    return float(np.var(result))



def validate_image(file_bytes: bytes, content_type: str = None) -> dict:
    """
    Validate uploaded image bytes for safety and quality.
    Returns a dict with validation results.
    """
    result = {
        "valid": False,
        "acceptable": False,
        "blur_detected": False,
        "brightness_issue": False,
        "too_small": False,
        "reason": None,
        "blur_score": 0.0,
        "brightness_score": 0.0,
        "width": 0,
        "height": 0,
    }

    # 1. File size check
    if len(file_bytes) == 0:
        result["reason"] = "Empty file uploaded."
        return result

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        result["reason"] = f"File size exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)}MB limit."
        return result

    # 2. MIME type check
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        result["reason"] = f"Invalid file type: {content_type}. Accepted: JPG, PNG, WEBP."
        return result

    # 3. Decode image safely
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        # Re-open after verify (verify consumes the stream)
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except UnidentifiedImageError:
        result["reason"] = "Uploaded file is not a valid image."
        return result
    except Exception as e:
        result["reason"] = f"Corrupted or unreadable image file: {str(e)}"
        return result

    w, h = img.size
    result["width"] = w
    result["height"] = h
    result["valid"] = True

    # 4. Minimum dimension check
    if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
        result["too_small"] = True
        result["reason"] = "Image is too small for reliable analysis."
        return result

    # 5. Convert to grayscale using PIL (no OpenCV needed)
    gray_img = img.convert("L")
    gray_array = np.array(gray_img)

    # 6. Blur detection (Laplacian variance via pure numpy)
    blur_score = _laplacian_variance(gray_array)
    result["blur_score"] = round(blur_score, 2)

    if blur_score < BLUR_THRESHOLD:
        result["blur_detected"] = True

    # 7. Brightness check
    brightness = float(np.mean(gray_array))
    result["brightness_score"] = round(brightness, 2)

    if brightness < BRIGHTNESS_LOW:
        result["brightness_issue"] = True
        result["reason"] = "Image is extremely dark."
    elif brightness > BRIGHTNESS_HIGH:
        result["brightness_issue"] = True
        result["reason"] = "Image is extremely overexposed."

    # 8. Overall acceptability
    # Only block if BOTH blur AND brightness are bad. Either alone is a warning, not a block.
    # Payment screenshots often have very bright/white backgrounds — don't block on brightness alone.
    if result["blur_detected"] and result["brightness_issue"]:
        result["acceptable"] = False
        result["reason"] = "Image quality is too poor for reliable receipt analysis."
    elif result["blur_detected"]:
        result["acceptable"] = True  # Blurry but not blocking
    elif result["brightness_issue"]:
        result["acceptable"] = True  # Bright/dark but let ML model decide
    else:
        result["acceptable"] = True
        result["reason"] = None

    return result
