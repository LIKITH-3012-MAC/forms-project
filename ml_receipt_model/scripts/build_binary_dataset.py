import os
import shutil
import hashlib
import random
from pathlib import Path

random.seed(42)

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def build_dataset():
    base_dir = Path(__file__).parent.parent
    src_private = base_dir / "dataset_private" / "raw_labeled"
    src_downloads = base_dir / "dataset_downloads"
    out_dir = base_dir / "processed_dataset" / "binary"
    
    # Define classes mapping
    # Anything under payment_receipt or payment_receipt_like_document -> payment_receipt
    # Anything under non_receipt or failed_or_pending_payment -> non_receipt
    
    seen_hashes = set()
    dataset = {"payment_receipt": [], "non_receipt": []}
    
    def add_files(dir_path, class_name):
        if not dir_path.exists():
            return
        for ext in ["*.jpg", "*.png", "*.jpeg", "*.webp"]:
            for f in dir_path.rglob(ext):
                h = hash_file(f)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    dataset[class_name].append(f)
    
    # 1. Collect Private Images
    add_files(src_private / "payment_receipt", "payment_receipt")
    add_files(src_private / "non_receipt", "non_receipt")
    add_files(src_private / "failed_or_pending_payment", "non_receipt")
    
    # 2. Collect Public Images
    add_files(src_downloads / "sroie", "payment_receipt")
    add_files(src_downloads / "nano_receipts", "payment_receipt")
    add_files(src_downloads / "places365", "non_receipt")
    
    print(f"Total Unique Images - Receipt: {len(dataset['payment_receipt'])}, Non-Receipt: {len(dataset['non_receipt'])}")
    
    # Balance classes (Optional: based on minimum class size, or just use all)
    min_size = min(len(dataset["payment_receipt"]), len(dataset["non_receipt"]))
    if min_size == 0:
        print("Warning: One of the classes is empty! Cannot balance. Collecting everything available.")
    else:
        print(f"Balancing to {min_size} images per class.")
        dataset["payment_receipt"] = random.sample(dataset["payment_receipt"], min_size)
        dataset["non_receipt"] = random.sample(dataset["non_receipt"], min_size)
    
    # Split: 70/15/15
    splits = {"train": 0.7, "val": 0.15, "test": 0.15}
    
    for cls, files in dataset.items():
        random.shuffle(files)
        total = len(files)
        train_end = int(total * splits["train"])
        val_end = train_end + int(total * splits["val"])
        
        split_files = {
            "train": files[:train_end],
            "val": files[train_end:val_end],
            "test": files[val_end:]
        }
        
        for split_name, s_files in split_files.items():
            split_dir = out_dir / split_name / cls
            split_dir.mkdir(parents=True, exist_ok=True)
            for i, f in enumerate(s_files):
                dest = split_dir / f"{cls}_{split_name}_{i}{f.suffix}"
                shutil.copy2(f, dest)
                
    print(f"Dataset successfully built in {out_dir}")

if __name__ == "__main__":
    build_dataset()
