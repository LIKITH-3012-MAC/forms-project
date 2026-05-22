# AI Payment Receipt Similarity Model Pipeline

This directory contains the machine learning pipeline for creating an AI visual assistant that detects payment receipts.

## Privacy Warning
**DO NOT COMMIT RAW PAYMENT SCREENSHOTS TO GITHUB.**
Real payment screenshots contain sensitive data (UTRs, names, phone numbers, balances).
All private datasets must be kept locally in `dataset_private/` which is ignored by `.gitignore`.

## Getting Started

1. **Install Dependencies:**
   ```bash
   pip install -r requirements-training.txt
   ```

2. **Prepare Datasets:**
   - Add your local private images to the project and run `python scripts/inspect_local_images.py` to view them.
   - Edit `LOCAL_IMAGE_LABELS` in `scripts/copy_local_seed_images.py` with your confirmed labels, then run it.
   - Run `python scripts/redact_private_images.py` to interactively blur sensitive info.
   - Download public receipts (SROIE, Nano Receipts): `python scripts/download_public_datasets.py --all`
   - Build the final dataset structure: `python scripts/build_binary_dataset.py`

3. **Train the Model:**
   - YOLO Classification (Recommended): `python train_yolo_classifier.py`
   - CNN Transfer Learning (Alternative): `python train_cnn_transfer_learning.py`

4. **Evaluate and Export:**
   - `python evaluate_model.py`
   - `python export_to_onnx.py`

5. **Deploy:**
   Copy the exported `best.onnx` file to the backend:
   ```bash
   cp outputs/receipt_classifier/weights/best.onnx ../backend/models/payment_receipt_classifier.onnx
   ```
