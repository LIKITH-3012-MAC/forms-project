#!/usr/bin/env python3
"""
predict_receipt.py — Combined Receipt Prediction Pipeline

Loads the trained visual model and runs OCR verification to produce
a final receipt/not_receipt prediction with safety thresholds.

Combines:
  1. Visual model score (EfficientNetB0, primary signal)
  2. OCR signal score (EasyOCR, secondary verification)
  3. Safety threshold logic

Thresholds:
  - visual >= 0.85 AND ocr >= 0.30  → Accept
  - visual >= 0.55                   → Needs Review
  - visual < 0.55                    → Reject
"""

import os
import json
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_DIR / "models" / "receipt_validator_best.keras"
CLASS_NAMES_PATH = PROJECT_DIR / "models" / "class_names.json"
IMG_SIZE = (224, 224)

# Safety thresholds
ACCEPT_VISUAL_THRESHOLD = 0.85
REVIEW_VISUAL_THRESHOLD = 0.55
ACCEPT_OCR_THRESHOLD = 0.30

# Confidence weighting
VISUAL_WEIGHT = 0.75
OCR_WEIGHT = 0.25


class ReceiptPredictor:
    """Combined visual + OCR receipt predictor with safety thresholds."""

    def __init__(self, model_path: str = None, class_names_path: str = None):
        """
        Initialize the predictor.

        Args:
            model_path: Path to the trained Keras model.
            class_names_path: Path to the class_names.json file.
        """
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.class_names_path = (
            Path(class_names_path) if class_names_path else CLASS_NAMES_PATH
        )
        self._model = None
        self._class_names = None
        self._ocr_validator = None

    @property
    def model(self):
        """Lazy-load the Keras model."""
        if self._model is None:
            import tensorflow as tf

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model not found at: {self.model_path}\n"
                    "Run train_model.py first to train the model."
                )
            print(f"  📦 Loading model from: {self.model_path}")
            self._model = tf.keras.models.load_model(str(self.model_path))
        return self._model

    @property
    def class_names(self):
        """Load class name mapping."""
        if self._class_names is None:
            if self.class_names_path.exists():
                with open(self.class_names_path, "r") as f:
                    self._class_names = json.load(f)
            else:
                # Default mapping
                self._class_names = {"0": "not_receipt", "1": "receipt"}
                print(
                    f"  ⚠️ class_names.json not found, using default: {self._class_names}"
                )
        return self._class_names

    @property
    def ocr_validator(self):
        """Lazy-load the OCR validator."""
        if self._ocr_validator is None:
            from ocr_validator import OCRValidator

            self._ocr_validator = OCRValidator()
        return self._ocr_validator

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Load and preprocess an image for model inference.

        Args:
            image_path: Path to the image file.

        Returns:
            Preprocessed numpy array of shape (1, 224, 224, 3).
        """
        img = Image.open(image_path).convert("RGB")
        img = img.resize(IMG_SIZE, Image.BILINEAR)
        img_array = np.array(img, dtype=np.float32)

        # Apply EfficientNet preprocessing (scale to [0, 1] range)
        # EfficientNet expects pixel values in [0, 255] by default with
        # tf.keras.applications.efficientnet.preprocess_input, but since we
        # trained with image_dataset_from_directory which gives [0, 255],
        # and apply preprocessing inside the model, we pass raw [0, 255].
        # However, our model includes preprocess_input in the pipeline.
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def get_visual_score(self, image_path: str) -> float:
        """
        Run the visual model and return the receipt probability.

        Args:
            image_path: Path to the image file.

        Returns:
            float: Receipt probability (0.0 to 1.0).
        """
        img_array = self.preprocess_image(image_path)
        prediction = self.model.predict(img_array, verbose=0)

        # Model output is sigmoid (binary): probability of the positive class
        # We need to check which class is 'receipt' vs 'not_receipt'
        receipt_prob = float(prediction[0][0])

        # If class 0 is 'not_receipt' and class 1 is 'receipt',
        # the sigmoid output is the probability of class 1 (receipt)
        # Check class_names to determine mapping
        if self.class_names.get("0") == "receipt":
            # Class 0 is receipt, sigmoid gives prob of class 1 (not_receipt)
            receipt_prob = 1.0 - receipt_prob
        # else: class 1 is receipt (default), sigmoid output is receipt prob

        return receipt_prob

    def get_ocr_result(self, image_path: str) -> dict:
        """
        Run OCR verification on the image.

        Args:
            image_path: Path to the image file.

        Returns:
            dict with ocr_signal_score and ocr_signals_found.
        """
        try:
            result = self.ocr_validator.validate(image_path)
            return {
                "ocr_signal_score": result.get("ocr_signal_score", 0.0),
                "ocr_signals_found": result.get("ocr_signals_found", []),
            }
        except Exception as e:
            print(f"  ⚠️ OCR verification failed: {e}")
            return {
                "ocr_signal_score": 0.0,
                "ocr_signals_found": [],
            }

    def predict(self, image_path: str, skip_ocr: bool = False) -> dict:
        """
        Run the full prediction pipeline: visual model + OCR verification.

        Args:
            image_path: Path to the image file.
            skip_ocr: If True, skip OCR verification (faster inference).

        Returns:
            dict with prediction, confidence, visual_model_score,
            ocr_signal_score, ocr_signals_found, and message.
        """
        image_path = str(image_path)

        # Validate image exists
        if not Path(image_path).exists():
            return {
                "prediction": "error",
                "confidence": 0.0,
                "visual_model_score": 0.0,
                "ocr_signal_score": 0.0,
                "ocr_signals_found": [],
                "message": f"Error: Image file not found: {image_path}",
            }

        # Validate it's a readable image
        try:
            img = Image.open(image_path)
            img.verify()
        except Exception:
            return {
                "prediction": "error",
                "confidence": 0.0,
                "visual_model_score": 0.0,
                "ocr_signal_score": 0.0,
                "ocr_signals_found": [],
                "message": "Error: Uploaded file is not a valid image.",
            }

        print(f"\n🔎 Analyzing: {Path(image_path).name}")
        print("─" * 50)

        # Step 1: Visual model prediction
        print("  📸 Running visual model inference...")
        visual_score = self.get_visual_score(image_path)
        print(f"  📊 Visual model score: {visual_score:.4f}")

        # Step 2: OCR verification (optional)
        ocr_score = 0.0
        ocr_signals = []

        if not skip_ocr:
            ocr_result = self.get_ocr_result(image_path)
            ocr_score = ocr_result["ocr_signal_score"]
            ocr_signals = ocr_result["ocr_signals_found"]

        # Step 3: Combined confidence
        confidence = (VISUAL_WEIGHT * visual_score) + (OCR_WEIGHT * ocr_score)
        confidence = round(min(confidence, 1.0), 4)

        # Step 4: Apply safety thresholds
        if visual_score >= ACCEPT_VISUAL_THRESHOLD and ocr_score >= ACCEPT_OCR_THRESHOLD:
            prediction = "receipt"
            message = "Accepted: This image appears to be a payment receipt."
        elif visual_score >= ACCEPT_VISUAL_THRESHOLD and skip_ocr:
            # If OCR was skipped but visual score is high
            prediction = "receipt"
            message = "Accepted: This image appears to be a payment receipt (OCR skipped)."
        elif visual_score >= ACCEPT_VISUAL_THRESHOLD and ocr_score < ACCEPT_OCR_THRESHOLD:
            # High visual but low OCR — still cautiously accept but flag
            prediction = "needs_review"
            message = (
                "Needs Review: Image visually resembles a receipt but OCR could not "
                "verify sufficient payment indicators. Please upload a clearer image."
            )
        elif visual_score >= REVIEW_VISUAL_THRESHOLD:
            prediction = "needs_review"
            message = (
                "Needs Review: The uploaded image may be a receipt, but verification "
                "is insufficient. Please upload a clearer image."
            )
        else:
            prediction = "not_receipt"
            message = "Rejected: This image does not appear to be a valid payment receipt."

        result = {
            "prediction": prediction,
            "confidence": confidence,
            "visual_model_score": round(visual_score, 4),
            "ocr_signal_score": round(ocr_score, 4),
            "ocr_signals_found": ocr_signals,
            "message": message,
        }

        # Print result
        print(f"\n  {'=' * 46}")
        print(f"  ┃ PREDICTION:  {result['prediction'].upper():<30} ┃")
        print(f"  ┃ Confidence:  {result['confidence']:<30.4f} ┃")
        print(f"  ┃ Visual:      {result['visual_model_score']:<30.4f} ┃")
        print(f"  ┃ OCR:         {result['ocr_signal_score']:<30.4f} ┃")
        print(f"  {'=' * 46}")
        print(f"  💬 {result['message']}")

        if ocr_signals:
            print(f"  🔤 OCR signals: {ocr_signals}")

        return result


# ─── CLI Interface ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Receipt Validator — Predict if an image is a payment receipt"
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the image to classify",
    )
    parser.add_argument(
        "--model",
        default=str(MODEL_PATH),
        help=f"Path to the trained model (default: {MODEL_PATH})",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Skip OCR verification (faster but less accurate)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON only",
    )
    args = parser.parse_args()

    predictor = ReceiptPredictor(model_path=args.model)
    result = predictor.predict(args.image, skip_ocr=args.skip_ocr)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
