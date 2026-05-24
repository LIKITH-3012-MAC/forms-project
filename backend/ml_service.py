#!/usr/bin/env python3
"""Backend ML Service – loads a TensorFlow/Keras model saved as a .pkl (HDF5) file.
Provides a utility function `predict_receipt_similarity` compatible with the existing FastAPI
endpoint (`/api/receipt/validate`) used by `app.py`.
"""

import os
import io
import numpy as np
from PIL import Image, UnidentifiedImageError
import tensorflow as tf

# Model configuration
MODEL_VERSION = "receipt-cls-v2"
# Expected location of the trained model (saved as .pkl / HDF5)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "receipt_validator_best.pkl")

# Global session – loaded once at startup
_keras_model = None


def _load_model():
    """Load the Keras model from MODEL_PATH.
    The model is expected to output a single sigmoid probability for the *receipt* class.
    Returns the model instance or None on failure.
    """
    global _keras_model
    if _keras_model is not None:
        return _keras_model
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Model file not found at {MODEL_PATH}")
        return None
    try:
        # .pkl saved via `model.save('file.pkl')` (HDF5 format)
        _keras_model = tf.keras.models.load_model(MODEL_PATH)
        print("✅ Keras model loaded successfully.")
    except Exception as e:
        print(f"Error loading Keras model: {e}")
        _keras_model = None
    return _keras_model


def _preprocess_image(file_bytes: bytes) -> np.ndarray:
    """Resize image to 224×224 and convert to a NCHW tensor suitable for the model.
    Returns a NumPy array with shape (1, 224, 224, 3).
    """
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = img.resize((224, 224), Image.BILINEAR)
    img_array = np.array(img).astype(np.float32) / 255.0
    # Model expects batch dimension first
    return np.expand_dims(img_array, axis=0)


def predict_receipt_similarity(file_bytes: bytes) -> dict:
    """Run inference using the loaded Keras model.
    Returns a dictionary mirroring the original ONNX‑based API.
    """
    # 1. Validate image
    try:
        Image.open(io.BytesIO(file_bytes)).verify()
    except UnidentifiedImageError:
        return {
            "available": False,
            "match_percentage": None,
            "label": "error",
            "provider": None,
            "confidence_message": "Uploaded file is not a valid image.",
            "model_version": MODEL_VERSION,
        }

    model = _load_model()
    if model is None:
        return {
            "available": False,
            "match_percentage": None,
            "label": "not_checked",
            "provider": None,
            "confidence_message": "Receipt recognition model is not trained or unavailable.",
            "model_version": MODEL_VERSION,
        }

    try:
        input_tensor = _preprocess_image(file_bytes)
        # Model outputs a sigmoid probability for the *receipt* class
        prob = float(model.predict(input_tensor, verbose=0)[0][0])
        match_percentage = round(prob * 100, 2)
        if match_percentage >= 85:
            label = "payment_receipt"
            msg = "Strong payment receipt similarity"
        elif match_percentage >= 55:
            label = "needs_review"
            msg = "Review Needed: Uncertain receipt match"
        else:
            label = "non_receipt"
            msg = "Image does not resemble a payment receipt"
        return {
            "available": True,
            "match_percentage": match_percentage,
            "label": label,
            "provider": None,
            "confidence_message": msg,
            "model_version": MODEL_VERSION,
        }
    except Exception as e:
        print(f"Inference error: {e}")
        return {
            "available": False,
            "match_percentage": None,
            "label": "not_checked",
            "provider": None,
            "confidence_message": "AI preview failed. Manual verification will continue.",
            "model_version": MODEL_VERSION,
        }

import io
import numpy as np
from PIL import Image, UnidentifiedImageError
try:
    import onnxruntime as ort
except ImportError as e:
    print(f"Failed to import onnxruntime: {e}")
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
            label = "needs_review"
            msg = "Review Needed: Uncertain receipt match"
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
