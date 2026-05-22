import os
import io
import numpy as np
from PIL import Image, UnidentifiedImageError
try:
    import onnxruntime as ort
except ImportError:
    ort = None

MODEL_VERSION = "receipt-cls-v1"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "payment_receipt_classifier.onnx")

# Try loading the model globally so it's loaded only once at startup
_ort_session = None

def _get_session():
    global _ort_session
    if ort is None:
        return None
    if _ort_session is None and os.path.exists(MODEL_PATH):
        try:
            _ort_session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
        except Exception as e:
            print(f"Error loading ONNX model: {e}")
            _ort_session = None
    return _ort_session

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)

def predict_receipt_similarity(file_bytes: bytes) -> dict:
    """
    Analyzes the uploaded bytes using the ONNX model to determine
    how closely it resembles a payment receipt.
    """
    # 1. Validate it's an image
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except UnidentifiedImageError:
        return {
            "available": False,
            "match_percentage": None,
            "label": "error",
            "provider": None,
            "confidence_message": "Uploaded file is not a valid image.",
            "model_version": MODEL_VERSION
        }
        
    session = _get_session()
    if session is None:
        return {
            "available": False,
            "match_percentage": None,
            "label": "not_checked",
            "provider": None,
            "confidence_message": "Receipt recognition model is not trained or unavailable. You may continue submission. Final payment verification is completed manually.",
            "model_version": MODEL_VERSION
        }

    # 3. Preprocess for YOLO classification
    try:
        # Re-open the image for processing since .verify() closes or exhausts it sometimes
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img = img.resize((224, 224), Image.BILINEAR)
        
        # Convert to numpy and NCHW
        img_data = np.array(img).astype(np.float32) / 255.0
        img_data = np.transpose(img_data, (2, 0, 1))
        img_data = np.expand_dims(img_data, axis=0)
        
        # 4. Inference
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: img_data})
        
        # YOLO classification ONNX exports include the Softmax activation,
        # so the output values are already probabilities summing to 1.0.
        probs = outputs[0][0]
        
        # Assume binary: class 0 is non_receipt, class 1 is payment_receipt
        # If YOLO exports alphabetically, non_receipt is 0, payment_receipt is 1.
        # But for robustness, we map standardly.
        receipt_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
        match_percentage = round(receipt_prob * 100, 2)
        
        if match_percentage >= 75:
            label = "payment_receipt"
            msg = "Strong payment receipt similarity"
        elif match_percentage >= 40:
            label = "uncertain"
            msg = "Uncertain receipt match"
        else:
            label = "non_receipt"
            msg = "This image does not strongly resemble a payment receipt."
            
        return {
            "available": True,
            "match_percentage": match_percentage,
            "label": label,
            "provider": None,
            "confidence_message": msg,
            "model_version": MODEL_VERSION
        }
    except Exception as e:
        print(f"Inference error: {e}")
        return {
            "available": False,
            "match_percentage": None,
            "label": "not_checked",
            "provider": None,
            "confidence_message": "AI preview failed. Manual verification will continue.",
            "model_version": MODEL_VERSION
        }
