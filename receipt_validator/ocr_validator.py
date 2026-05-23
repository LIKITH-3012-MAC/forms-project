#!/usr/bin/env python3
"""
ocr_validator.py — Secondary OCR Verification Layer for Receipt Validation

Uses EasyOCR to extract text from images and detect receipt/payment
signal keywords. This is NOT the primary classifier — it is a secondary
verification layer that runs after the visual model prediction.

Rules:
- A single keyword must NOT automatically approve an image.
- Multiple OCR signals combined with a high visual model score increase confidence.
- OCR alone cannot override a low visual model score.
"""

import re
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

try:
    import easyocr
except ImportError:
    easyocr = None
    print("⚠️ easyocr not installed. OCR verification will be disabled.")
    print("   Install with: pip install easyocr")


# ─── Signal Keywords Configuration ────────────────────────────────────────────

# Keywords are organized by category with associated weights.
# Higher weight = stronger signal that this is a payment receipt.
SIGNAL_KEYWORDS = {
    # Payment status indicators (HIGH weight)
    "payment_status": {
        "weight": 0.25,
        "keywords": [
            r"paid",
            r"payment\s+successful",
            r"transaction\s+successful",
            r"transfer\s+successful",
            r"money\s+sent",
            r"completed",
            r"success",
        ],
    },
    # Financial identifiers (HIGH weight)
    "financial_ids": {
        "weight": 0.25,
        "keywords": [
            r"utr",
            r"transaction\s+id",
            r"txn\s+id",
            r"reference\s+number",
            r"ref\.?\s*no\.?",
            r"bank\s+reference",
            r"order\s+id",
            r"rrn",
        ],
    },
    # Currency symbols (MEDIUM weight)
    "currency": {
        "weight": 0.15,
        "keywords": [
            r"₹",
            r"rs\.?",
            r"inr",
            r"rupees?",
        ],
    },
    # Payment app names (MEDIUM weight)
    "payment_apps": {
        "weight": 0.15,
        "keywords": [
            r"phonepe",
            r"paytm",
            r"google\s*pay",
            r"gpay",
            r"bhim",
            r"amazon\s*pay",
            r"upi",
            r"imps",
            r"neft",
            r"rtgs",
        ],
    },
    # Transaction fields (MEDIUM weight)
    "transaction_fields": {
        "weight": 0.12,
        "keywords": [
            r"amount",
            r"paid\s+to",
            r"sent\s+to",
            r"debited\s+from",
            r"credited\s+to",
            r"merchant",
            r"beneficiary",
            r"receiver",
            r"sender",
        ],
    },
    # Temporal (LOW weight)
    "temporal": {
        "weight": 0.08,
        "keywords": [
            r"date",
            r"time",
            r"\d{2}[/\-]\d{2}[/\-]\d{2,4}",
            r"\d{1,2}:\d{2}\s*(am|pm)?",
        ],
    },
}


class OCRValidator:
    """OCR-based secondary verification for receipt images."""

    def __init__(self, languages: list = None):
        """
        Initialize the OCR validator.

        Args:
            languages: List of language codes for EasyOCR (default: ['en'])
        """
        self.languages = languages or ["en"]
        self._reader = None

    @property
    def reader(self):
        """Lazy-load EasyOCR reader (it's heavy, only load when needed)."""
        if self._reader is None:
            if easyocr is None:
                raise ImportError(
                    "easyocr is not installed. Install with: pip install easyocr"
                )
            print("  🔤 Loading EasyOCR model (first load may download models)...")
            self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
        return self._reader

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image using EasyOCR.

        Args:
            image_path: Path to the image file.

        Returns:
            Concatenated text extracted from the image.
        """
        try:
            results = self.reader.readtext(str(image_path), detail=0)
            full_text = " ".join(results)
            return full_text
        except Exception as e:
            print(f"  ⚠️ OCR extraction failed: {e}")
            return ""

    def detect_signals(self, text: str) -> dict:
        """
        Detect receipt/payment signal keywords in the extracted text.

        Args:
            text: Text extracted from the image via OCR.

        Returns:
            dict with:
                - ocr_signal_score (float): 0.0 to 1.0
                - ocr_signals_found (list): list of matched signal strings
                - category_scores (dict): per-category match details
        """
        if not text or not text.strip():
            return {
                "ocr_signal_score": 0.0,
                "ocr_signals_found": [],
                "category_scores": {},
                "raw_text_length": 0,
            }

        text_lower = text.lower().strip()
        total_score = 0.0
        signals_found = []
        category_scores = {}

        for category, config in SIGNAL_KEYWORDS.items():
            weight = config["weight"]
            keywords = config["keywords"]
            category_matches = []

            for keyword_pattern in keywords:
                pattern = re.compile(keyword_pattern, re.IGNORECASE)
                matches = pattern.findall(text_lower)
                if matches:
                    # Use the original keyword pattern as the signal name
                    clean_name = keyword_pattern.replace(r"\s+", " ").replace(
                        r"\s*", ""
                    ).replace(r"\.?", ".").replace(r"\.?\s*", " ").strip("\\")
                    # Get the actual matched text
                    actual_match = matches[0] if isinstance(matches[0], str) else matches[0]
                    category_matches.append(actual_match.strip())

            if category_matches:
                # Each category contributes its weight, scaled by how many keywords matched
                # Cap at 1.0 contribution per category (diminishing returns)
                match_ratio = min(len(category_matches) / max(len(keywords) * 0.3, 1), 1.0)
                category_contribution = weight * match_ratio
                total_score += category_contribution
                signals_found.extend(category_matches)

                category_scores[category] = {
                    "matches": category_matches,
                    "contribution": round(category_contribution, 4),
                }

        # Normalize score to 0.0–1.0 range
        # The maximum possible score is the sum of all weights = 1.0
        final_score = min(total_score, 1.0)

        # Apply a penalty if very few signals found (single keyword shouldn't score high)
        if len(signals_found) == 1:
            final_score *= 0.4  # Heavy penalty for single keyword
        elif len(signals_found) == 2:
            final_score *= 0.7  # Moderate penalty

        return {
            "ocr_signal_score": round(final_score, 4),
            "ocr_signals_found": signals_found,
            "category_scores": category_scores,
            "raw_text_length": len(text_lower),
        }

    def validate(self, image_path: str) -> dict:
        """
        Run full OCR validation pipeline on an image.

        Args:
            image_path: Path to the image file.

        Returns:
            dict with ocr_signal_score, ocr_signals_found, extracted_text, etc.
        """
        print(f"  🔍 Running OCR verification on: {Path(image_path).name}")

        # Extract text
        extracted_text = self.extract_text(image_path)

        if not extracted_text:
            print("  ℹ️ No text detected in image.")
            return {
                "ocr_signal_score": 0.0,
                "ocr_signals_found": [],
                "extracted_text": "",
                "category_scores": {},
            }

        # Detect signals
        result = self.detect_signals(extracted_text)

        # Add the extracted text to the result
        result["extracted_text"] = extracted_text

        # Log findings
        if result["ocr_signals_found"]:
            print(f"  ✅ OCR signals found: {result['ocr_signals_found']}")
            print(f"  📊 OCR signal score: {result['ocr_signal_score']:.2f}")
        else:
            print("  ℹ️ No receipt-related signals found in OCR text.")

        return result


# ─── Standalone Usage ─────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="OCR-based receipt verification (secondary layer)"
    )
    parser.add_argument(
        "--image", required=True, help="Path to the image to verify"
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["en"],
        help="OCR languages (default: en)",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"❌ Image not found: {args.image}")
        return

    validator = OCRValidator(languages=args.languages)
    result = validator.validate(args.image)

    print("\n" + "=" * 50)
    print("  OCR VERIFICATION RESULT")
    print("=" * 50)
    print(f"  Image:          {Path(args.image).name}")
    print(f"  Signal Score:   {result['ocr_signal_score']:.4f}")
    print(f"  Signals Found:  {result['ocr_signals_found']}")
    print(f"  Text Length:    {result.get('raw_text_length', len(result.get('extracted_text', '')))}")
    print()
    print("  Extracted Text Preview:")
    text = result.get("extracted_text", "")
    preview = text[:300] + "..." if len(text) > 300 else text
    print(f"  {preview}")
    print("=" * 50)


if __name__ == "__main__":
    main()
