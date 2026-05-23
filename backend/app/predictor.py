"""
Stages B & D: Visual Receipt Classifier + Fusion Decision.
Loads the trained .keras feature extractor and .pkl calibrated classifier.
Combines visual embeddings, quality features, and OCR signals for final prediction.
"""
import io
import threading
import numpy as np
from PIL import Image
from app.settings import (
    FEATURE_EXTRACTOR_PATH, CLASSIFIER_PATH, SCALER_PATH,
    THRESHOLD_LIKELY_RECEIPT, THRESHOLD_UNCERTAIN_LOW
)
from app.image_validator import validate_image
from app.ocr_analyzer import analyze_receipt_text, get_ocr_reader

# Global model references (loaded once at startup)
_feature_session = None
_feature_input_name = None
_feature_output_name = None
_classifier = None
_scaler = None
_models_loaded = False
_models_loading = False
_load_error = None


def load_models():
    """Load all ML models at application startup."""
    global _feature_session, _feature_input_name, _feature_output_name, _classifier, _scaler, _models_loaded, _models_loading, _load_error

    if _models_loaded:
        return True

    _models_loading = True

    try:
        import onnxruntime as ort
        import joblib

        # Load feature extractor ONNX session
        if not FEATURE_EXTRACTOR_PATH.exists():
            print(f"⚠️ Feature extractor not found at {FEATURE_EXTRACTOR_PATH}")
            _models_loading = False
            return False

        sess_options = ort.SessionOptions()
        sess_options.inter_op_num_threads = 1
        sess_options.intra_op_num_threads = 1
        sess_options.enable_mem_pattern = False

        _feature_session = ort.InferenceSession(
            str(FEATURE_EXTRACTOR_PATH),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"]
        )
        _feature_input_name = _feature_session.get_inputs()[0].name
        _feature_output_name = _feature_session.get_outputs()[0].name
        print(f"✓ Feature extractor loaded from {FEATURE_EXTRACTOR_PATH}")

        # Load sklearn classifier
        if not CLASSIFIER_PATH.exists():
            print(f"⚠️ Classifier not found at {CLASSIFIER_PATH}")
            _models_loading = False
            return False

        _classifier = joblib.load(str(CLASSIFIER_PATH))
        print(f"✓ Classifier loaded from {CLASSIFIER_PATH}")

        # Load scaler
        if not SCALER_PATH.exists():
            print(f"⚠️ Scaler not found at {SCALER_PATH}")
            _models_loading = False
            return False

        _scaler = joblib.load(str(SCALER_PATH))
        print(f"✓ Feature scaler loaded from {SCALER_PATH}")

        # Pre-initialize OCR reader
        get_ocr_reader()

        _models_loaded = True
        _models_loading = False
        print("✓ All models loaded successfully.")
        return True

    except Exception as e:
        import traceback
        _load_error = f"{str(e)}\n{traceback.format_exc()}"
        _models_loading = False
        print(f"❌ Model loading failed: {_load_error}")
        return False


def load_models_background():
    """Load models in a background thread so server can bind to port immediately."""
    thread = threading.Thread(target=load_models, daemon=True)
    thread.start()
    print("⏳ Model loading started in background thread...")


def get_model_status() -> dict:
    """Return status of loaded models."""
    return {
        "visual_model_loaded": _feature_session is not None,
        "classifier_loaded": _classifier is not None,
        "scaler_loaded": _scaler is not None,
        "ocr_loaded": get_ocr_reader() not in (None, "unavailable"),
        "load_error": _load_error,
    }


def predict_receipt(file_bytes: bytes, content_type: str = None, filename: str = "upload") -> dict:
    """
    Full multi-stage receipt prediction pipeline.
    Returns structured prediction result.
    """
    # Stage A: Image Quality Gate
    quality = validate_image(file_bytes, content_type)

    if not quality["valid"]:
        return {
            "success": False,
            "filename": filename,
            "prediction": "invalid",
            "status": "invalid_image",
            "allow_submission": False,
            "receipt_probability": 0.0,
            "not_receipt_probability": 100.0,
            "quality": quality,
            "ocr_signals": None,
            "threshold": THRESHOLD_LIKELY_RECEIPT * 100,
            "message": quality.get("reason", "Invalid image file."),
        }

    if not quality["acceptable"]:
        return {
            "success": True,
            "filename": filename,
            "prediction": "uncertain",
            "status": "uncertain",
            "allow_submission": False,
            "receipt_probability": 0.0,
            "not_receipt_probability": 0.0,
            "quality": quality,
            "ocr_signals": None,
            "threshold": THRESHOLD_LIKELY_RECEIPT * 100,
            "message": quality.get("reason", "Image quality is too poor for reliable receipt analysis."),
        }

    # Check if models are loaded
    if not _models_loaded:
        return {
            "success": True,
            "filename": filename,
            "prediction": "not_checked",
            "status": "model_unavailable",
            "allow_submission": True,
            "receipt_probability": 0.0,
            "not_receipt_probability": 0.0,
            "quality": quality,
            "ocr_signals": None,
            "threshold": THRESHOLD_LIKELY_RECEIPT * 100,
            "message": "Receipt recognition model is not available. Manual verification will be required.",
        }

    # Stage B: Visual Feature Extraction
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img_resized = img.resize((224, 224), Image.BILINEAR)
        img_array = np.array(img_resized, dtype=np.float32)

        # Batch dimension first: shape (1, 224, 224, 3)
        img_batch = np.expand_dims(img_array, axis=0)

        # Run ONNX inference
        outputs = _feature_session.run([_feature_output_name], {_feature_input_name: img_batch})
        visual_embedding = outputs[0].flatten()

        # Quality features
        blur_score = quality["blur_score"]
        brightness = quality["brightness_score"]
        orig_w = quality["width"]
        orig_h = quality["height"]
        aspect_ratio = orig_w / max(orig_h, 1)

        quality_features = np.array([blur_score, brightness, aspect_ratio, orig_w, orig_h], dtype=np.float32)
        combined = np.concatenate([visual_embedding, quality_features]).reshape(1, -1)

        # Scale and predict
        combined_scaled = _scaler.transform(combined)
        proba = _classifier.predict_proba(combined_scaled)[0]

        receipt_prob = float(proba[1])
        not_receipt_prob = float(proba[0])

    except Exception as e:
        print(f"Visual prediction error: {e}")
        return {
            "success": True,
            "filename": filename,
            "prediction": "error",
            "status": "prediction_error",
            "allow_submission": False,
            "receipt_probability": 0.0,
            "not_receipt_probability": 100.0,
            "quality": quality,
            "ocr_signals": None,
            "threshold": THRESHOLD_LIKELY_RECEIPT * 100,
            "message": "AI analysis failed. Manual verification will be required.",
        }

    # Stage C: OCR Analysis
    ocr_result = analyze_receipt_text(file_bytes)

    # Stage D: Final Decision
    has_failure = ocr_result.get("has_failure_or_pending_keyword", False)
    ocr_confirms = (
        ocr_result.get("has_amount", False)
        and ocr_result.get("has_success_keyword", False)
        and (ocr_result.get("has_transaction_reference", False) or ocr_result.get("has_payment_app_keyword", False))
    )

    # Decision logic
    receipt_pct = receipt_prob * 100  # convert to percentage for readability

    if has_failure:
        status = "suspicious_or_not_successful"
        prediction = "receipt_like_but_not_successful"
        allow_submission = False
        message = "This image resembles a payment screen but does not show a confirmed successful payment."
    elif receipt_prob >= THRESHOLD_LIKELY_RECEIPT and ocr_confirms:
        status = "likely_receipt"
        prediction = "receipt"
        allow_submission = True
        message = "This appears to be a successful payment receipt. Transaction verification is still required."
    elif receipt_prob >= THRESHOLD_LIKELY_RECEIPT and not ocr_confirms:
        # High visual score but OCR doesn't confirm — still accept but with caution
        status = "likely_receipt"
        prediction = "receipt"
        allow_submission = True
        message = "This appears to be a payment receipt. OCR could not fully confirm transaction details. Manual verification recommended."
    elif ocr_confirms:
        # OCR confirms success, app, and amount, but visual score is low (e.g. new receipt format).
        # We allow submission but flag it as uncertain for manual verification.
        status = "likely_receipt"
        prediction = "receipt"
        allow_submission = True
        message = "Receipt layout not fully recognized, but transaction details verified. Manual verification recommended."
    elif receipt_pct >= 75:
        # 75%+ visual confidence without OCR — still confident enough
        status = "likely_receipt"
        prediction = "receipt"
        allow_submission = True
        message = "Your screenshot seems original and accurate. Manual verification will confirm the transaction."
    elif receipt_pct >= 60:
        # 60-75% — confident it's original
        status = "likely_receipt"
        prediction = "receipt"
        allow_submission = True
        message = "Your screenshot seems original and accurate. Manual verification will confirm the transaction."
    elif receipt_pct >= 50:
        # 50-60% — borderline, seems 50-50 but still allow submission
        status = "uncertain"
        prediction = "uncertain"
        allow_submission = True
        message = "Your receipt seems 50-50 — we'll verify it manually. You can proceed with submission."
    elif receipt_pct >= THRESHOLD_UNCERTAIN_LOW * 100:
        # Between uncertain_low (default 70% but effectively 40-50% range now) and 50%
        status = "uncertain"
        prediction = "uncertain"
        allow_submission = False
        message = "Receipt confidence is not high enough. Please upload a clearer successful payment screenshot."
    else:
        status = "not_receipt"
        prediction = "not_receipt"
        allow_submission = False
        message = "This image does not appear to be a valid successful payment receipt."

    return {
        "success": True,
        "filename": filename,
        "prediction": prediction,
        "status": status,
        "allow_submission": allow_submission,
        "receipt_probability": round(receipt_prob * 100, 2),
        "not_receipt_probability": round(not_receipt_prob * 100, 2),
        "quality": {
            "acceptable": quality["acceptable"],
            "blur_detected": quality["blur_detected"],
            "brightness_issue": quality["brightness_issue"],
        },
        "ocr_signals": {
            "has_amount": ocr_result.get("has_amount", False),
            "has_success_keyword": ocr_result.get("has_success_keyword", False),
            "has_transaction_reference": ocr_result.get("has_transaction_reference", False),
            "has_failure_or_pending_keyword": has_failure,
            "signals_found": ocr_result.get("signals_found", []),
            "ocr_signal_score": ocr_result.get("ocr_signal_score", 0.0),
        },
        "threshold": THRESHOLD_LIKELY_RECEIPT * 100,
        "message": message,
    }
