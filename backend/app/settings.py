"""
Settings for the receipt validation system.
All thresholds, model paths, and keyword lists are centralized here.
"""
import os
from pathlib import Path

# Model paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"

FEATURE_EXTRACTOR_PATH = MODELS_DIR / "receipt_feature_extractor.onnx"
CLASSIFIER_PATH = MODELS_DIR / "receipt_classifier.pkl"
SCALER_PATH = MODELS_DIR / "feature_scaler.pkl"
MODEL_CONFIG_PATH = MODELS_DIR / "model_config.json"

# Decision thresholds
THRESHOLD_LIKELY_RECEIPT = 0.92
THRESHOLD_UNCERTAIN_LOW = 0.70
# Below THRESHOLD_UNCERTAIN_LOW => not_receipt

# Image quality limits
MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIN_IMAGE_DIMENSION = 50
BLUR_THRESHOLD = 30.0  # Laplacian variance below this = blurry
BRIGHTNESS_LOW = 20.0
BRIGHTNESS_HIGH = 245.0

# OCR positive receipt keywords (case-insensitive matching)
OCR_SUCCESS_KEYWORDS = [
    "payment successful", "paid successfully", "transaction successful",
    "transfer successful", "money sent", "payment completed",
    "paid", "success", "successful", "completed",
    "transaction completed",
]

OCR_AMOUNT_KEYWORDS = [
    "₹", "rs.", "rs ", "inr", "amount", "total",
]

OCR_TRANSACTION_KEYWORDS = [
    "utr", "upi", "transaction id", "reference number",
    "ref no", "bank reference", "ref id", "txn id",
    "order id", "payment id",
]

OCR_PAYMENT_APP_KEYWORDS = [
    "phonepe", "paytm", "google pay", "gpay", "bhim",
    "amazon pay", "cred", "mobikwik", "freecharge",
    "whatsapp pay", "sbi", "hdfc", "icici", "axis",
]

# OCR negative / failure keywords (if found, block acceptance)
OCR_FAILURE_KEYWORDS = [
    "failed", "unsuccessful", "pending", "cancelled",
    "declined", "processing", "failure", "error",
    "refund", "reversed", "not successful",
    "could not", "unable to", "try again",
]

# Date pattern regex (DD/MM/YYYY, DD-MM-YYYY, etc.)
DATE_PATTERN = r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'

# Amount pattern regex (₹700, Rs. 700, 700.00, etc.)
AMOUNT_PATTERN = r'(?:₹|rs\.?\s*|inr\s*)[\d,]+(?:\.\d{2})?|\d{1,7}(?:\.\d{2})?'
