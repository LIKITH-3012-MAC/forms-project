#!/usr/bin/env python3
"""Simple test script for the receipt classifier.

Usage:
    python test_prediction.py --image /path/to/image.jpg

It loads the Keras model via backend.ml_service.predict_receipt_similarity
and prints the prediction dictionary.
"""

import argparse
import os
import sys

# Adjust import path to locate the backend package
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from backend.ml_service import predict_receipt_similarity
except ImportError as e:
    print(f"Failed to import predict function: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Test receipt classifier on a single image.")
    parser.add_argument("--image", required=True, help="Path to the image file to classify.")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"Image file not found: {args.image}")
        sys.exit(1)

    with open(args.image, "rb") as f:
        img_bytes = f.read()

    result = predict_receipt_similarity(img_bytes)
    print("Prediction result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
