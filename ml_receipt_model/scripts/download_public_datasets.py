import argparse
import os
import json
from datetime import datetime
from pathlib import Path
try:
    from datasets import load_dataset
except ImportError:
    print("Please pip install datasets")
    exit(1)

DOWNLOAD_DIR = Path(__file__).parent.parent / "dataset_downloads"

def record_metadata(source, split, local_file, assigned_class, is_synthetic):
    metadata_file = DOWNLOAD_DIR / "metadata.jsonl"
    record = {
        "source_dataset": source,
        "original_split": split,
        "local_filename": local_file,
        "assigned_class": assigned_class,
        "synthetic_or_real": "synthetic" if is_synthetic else "real",
        "downloaded_at": datetime.now().isoformat()
    }
    with open(metadata_file, "a") as f:
        f.write(json.dumps(record) + "\n")

def download_sroie(max_images):
    print("Downloading SROIE...")
    out_dir = DOWNLOAD_DIR / "sroie" / "payment_receipt_like_document"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        ds = load_dataset("Voxel51/scanned_receipts", split="train", streaming=True)
        count = 0
        for item in ds:
            if count >= max_images:
                break
            image = item["image"]
            filename = f"sroie_{count}.jpg"
            save_path = out_dir / filename
            image.convert("RGB").save(save_path)
            record_metadata("Voxel51/scanned_receipts", "train", str(save_path), "payment_receipt_like_document", False)
            count += 1
            if count % 50 == 0:
                print(f"Saved {count} SROIE images")
    except Exception as e:
        print(f"Failed to download SROIE: {e}")

def download_nano_receipts(max_images):
    print("Downloading Nano Receipts...")
    out_dir = DOWNLOAD_DIR / "nano_receipts" / "payment_receipt_like_document"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        ds = load_dataset("34data/nano-receipts", split="train", streaming=True)
        count = 0
        for item in ds:
            if count >= max_images:
                break
            image = item["image"]
            filename = f"nano_{count}.jpg"
            save_path = out_dir / filename
            image.convert("RGB").save(save_path)
            record_metadata("34data/nano-receipts", "train", str(save_path), "payment_receipt_like_document", True)
            count += 1
            if count % 50 == 0:
                print(f"Saved {count} Nano images")
    except Exception as e:
        print(f"Failed to download Nano Receipts: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download public datasets safely.")
    parser.add_argument("--sroie", action="store_true")
    parser.add_argument("--nano-receipts", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--max-images", type=int, default=500)
    args = parser.parse_args()
    
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.sroie or args.all:
        download_sroie(args.max_images)
    if args.nano_receipts or args.all:
        download_nano_receipts(args.max_images)
    
    print("Done downloading public datasets.")
