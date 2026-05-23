import os
import shutil
from pathlib import Path
import argparse

def copy_seed_images(src_dir: Path, dest_dir: Path):
    """Copy one representative seed image from each detected family.
    Family detection is based on filename patterns provided in the plan.
    """
    # Define regex patterns for families (simplified generic detection)
    import re
    patterns = [
        r"image1_\d+\.jpg",
        r"paytm_\d+\.jpg",
        r"thread-166147785-.*_\d+\.png",
        r"WhatsApp Image \d{4}-\d{2}-\d{2} at \d{2}\.\d{2}\.\d{2}_\d+\.jpeg",
        r"WhatsApp Image \d{4}-\d{2}-\d{2} at \d{2}\.\d{2}\.\d{2}_\d+\.jpeg",
    ]
    copied = 0
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for file in src_dir.iterdir():
            if file.is_file() and regex.fullmatch(file.name):
                # select the *_001 version if exists, else first match
                base, ext = os.path.splitext(file.name)
                seed_name = base.rsplit('_', 1)[0] + "_001" + ext
                candidate = src_dir / seed_name
                src = candidate if candidate.exists() else file
                dest = dest_dir / src.name
                shutil.copy2(src, dest)
                copied += 1
                break
    return copied

def main():
    parser = argparse.ArgumentParser(description="Prepare dataset by copying seed receipt images.")
    parser.add_argument("--source", type=str, default=os.path.expanduser("~/Desktop/receipt_copies"), help="Source directory containing raw receipt images.")
    parser.add_argument("--dest", type=str, default="./receipt_validator/dataset/raw_seeds/receipt", help="Destination directory for seed receipt images.")
    args = parser.parse_args()

    src_dir = Path(args.source)
    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = copy_seed_images(src_dir, dest_dir)
    print(f"Copied {copied} seed receipt images to {dest_dir}")
    # Create remaining folder hierarchy
    base = Path(dest_dir).parents[2]  # receipt_validator/dataset
    for sub in ["not_receipt", "generated/train/receipt", "generated/train/not_receipt",
                "generated/val/receipt", "generated/val/not_receipt",
                "generated/test/receipt", "generated/test/not_receipt",
                "external_test/receipt", "external_test/not_receipt"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    print("Created full dataset folder structure.")

if __name__ == "__main__":
    main()
