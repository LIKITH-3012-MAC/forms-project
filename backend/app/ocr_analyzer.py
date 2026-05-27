"""
Stage C: OCR and Receipt Structure Analysis.
Uses RapidOCR to extract text from payment screenshots and detect receipt signals.
"""
import re
import numpy as np
from PIL import Image
import io

from app.settings import (
    OCR_SUCCESS_KEYWORDS, OCR_AMOUNT_KEYWORDS,
    OCR_TRANSACTION_KEYWORDS, OCR_PAYMENT_APP_KEYWORDS,
    OCR_FAILURE_KEYWORDS, DATE_PATTERN, AMOUNT_PATTERN
)

# RapidOCR engine singleton
_ocr_engine = None

def get_ocr_reader():
    """Verify and initialize the RapidOCR engine."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            print("✓ RapidOCR reader initialized.")
        except Exception as e:
            print(f"⚠️ RapidOCR not available: {e}")
            _ocr_engine = None
    return _ocr_engine


def analyze_receipt_text(file_bytes: bytes) -> dict:
    """
    Perform OCR on uploaded image bytes and detect receipt signals.
    Returns structured OCR analysis.
    """
    result = {
        "ocr_available": False,
        "ocr_text": "",
        "has_amount": False,
        "has_success_keyword": False,
        "has_transaction_reference": False,
        "has_payment_app_keyword": False,
        "has_date_pattern": False,
        "has_failure_or_pending_keyword": False,
        "receipt_keyword_count": 0,
        "failure_keyword_count": 0,
        "signals_found": [],
        "failure_signals_found": [],
        "ocr_signal_score": 0.0,
    }

    engine = get_ocr_reader()
    if engine is None:
        return result

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img_np = np.array(img)

        # Run OCR
        ocr_result, elapse = engine(img_np)
        
        if ocr_result:
            # Join all detected text boxes
            full_text = " ".join([item[1] for item in ocr_result]).lower()
            result["ocr_available"] = True
            result["ocr_text"] = full_text[:500]  # Limit stored text
        else:
            full_text = ""

        if not full_text:
            return result

        # 1. Check success keywords
        for kw in OCR_SUCCESS_KEYWORDS:
            if kw.lower() in full_text:
                result["has_success_keyword"] = True
                result["signals_found"].append(kw)
                result["receipt_keyword_count"] += 1

        # 2. Check amount patterns
        for kw in OCR_AMOUNT_KEYWORDS:
            if kw.lower() in full_text:
                result["has_amount"] = True
                if kw not in result["signals_found"]:
                    result["signals_found"].append(kw)
                result["receipt_keyword_count"] += 1
                break

        # Also check regex amount pattern
        if re.search(AMOUNT_PATTERN, full_text, re.IGNORECASE):
            result["has_amount"] = True

        # 3. Check transaction reference keywords
        for kw in OCR_TRANSACTION_KEYWORDS:
            if kw.lower() in full_text:
                result["has_transaction_reference"] = True
                if kw not in result["signals_found"]:
                    result["signals_found"].append(kw)
                result["receipt_keyword_count"] += 1

        # 4. Check payment app keywords
        for kw in OCR_PAYMENT_APP_KEYWORDS:
            if kw.lower() in full_text:
                result["has_payment_app_keyword"] = True
                if kw not in result["signals_found"]:
                    result["signals_found"].append(kw)
                result["receipt_keyword_count"] += 1

        # 5. Check date pattern
        if re.search(DATE_PATTERN, full_text):
            result["has_date_pattern"] = True
            result["signals_found"].append("date_pattern")
            result["receipt_keyword_count"] += 1

        # 6. Check failure keywords
        for kw in OCR_FAILURE_KEYWORDS:
            if kw.lower() in full_text:
                result["has_failure_or_pending_keyword"] = True
                result["failure_signals_found"].append(kw)
                result["failure_keyword_count"] += 1

        # 7. Compute OCR signal score (0.0 to 1.0)
        max_positive_signals = 5  # success, amount, txn ref, app name, date
        positive_count = sum([
            result["has_success_keyword"],
            result["has_amount"],
            result["has_transaction_reference"],
            result["has_payment_app_keyword"],
            result["has_date_pattern"],
        ])
        result["ocr_signal_score"] = round(positive_count / max_positive_signals, 2)

        # Penalize if failure keywords found
        if result["has_failure_or_pending_keyword"]:
            result["ocr_signal_score"] = max(0.0, result["ocr_signal_score"] - 0.5)

    except Exception as e:
        print(f"OCR analysis error: {e}")

    return result
