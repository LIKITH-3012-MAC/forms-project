import os
import shutil
import hashlib
from pathlib import Path

def get_file_hash(filepath):
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def prepare_directories():
    """Create all required dataset directories."""
    base_dir = Path(__file__).parent.parent.parent / "dataset"
    
    dirs = [
        "raw/receipt",
        "raw/not_receipt",
        "deduplicated/receipt",
        "deduplicated/not_receipt",
        "train/receipt",
        "train/not_receipt",
        "val/receipt",
        "val/not_receipt",
        "test/receipt",
        "test/not_receipt",
        "hard_negatives/humans",
        "hard_negatives/random_screenshots",
        "hard_negatives/social_media",
        "hard_negatives/documents",
        "hard_negatives/blank_blurred",
        "hard_negatives/payment_failed_pending",
        "hard_negatives/edited_fake_receipts"
    ]
    
    for d in dirs:
        (base_dir / d).mkdir(parents=True, exist_ok=True)
    
    print(f"✓ All dataset directories created under: {base_dir}")
    return base_dir

def collect_receipt_seeds(source_dir, raw_receipt_dir):
    """Group copies by hash, extract unique originals, and copy to raw seeds."""
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"Error: Source directory {source_dir} does not exist!")
        return []
        
    print(f"Scanning local receipt copies in: {source_dir}...")
    all_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.JPEG", "*.PNG", "*.WEBP"]:
        all_files.extend(source_path.glob(ext))
        
    print(f"Found {len(all_files)} total files in source.")
    
    # Deduplicate based on hash
    hash_to_files = {}
    for f in all_files:
        h = get_file_hash(f)
        if h not in hash_to_files:
            hash_to_files[h] = []
        hash_to_files[h].append(f)
        
    print(f"Deduplication complete. Found {len(hash_to_files)} unique receipt seeds.")
    
    copied_seeds = []
    for i, (h, files) in enumerate(hash_to_files.items(), 1):
        representative = files[0]
        # Detect family name from representative filename
        name = representative.name
        # Copy to raw_seeds
        dest_filename = f"receipt_seed_{i}{representative.suffix}"
        dest_path = raw_receipt_dir / dest_filename
        shutil.copy2(representative, dest_path)
        copied_seeds.append((name, len(files), dest_path))
        print(f"  Seed {i}: Representative='{name}', CopiesCount={len(files)} -> {dest_path.name}")
        
    print(f"✓ Copied {len(copied_seeds)} unique receipt seeds to {raw_receipt_dir}")
    print("Warning: Reliable generalization cannot be measured from copied receipt images alone.")
    return copied_seeds

def main():
    source_dir = "/Users/likithnaidu/Desktop/receipt_copies"
    base_dir = prepare_directories()
    
    # 1. Collect receipt seeds
    collect_receipt_seeds(source_dir, base_dir / "raw/receipt")
    
    # Write folder instructions for not_receipt
    readme_content = """# Raw Negative Class Seeds
Place diverse invalid uploads here:
- Human selfies, group photos
- Scenery, landscapes, food
- Random mobile screenshots, chat screenshots
- Blank, blurred, or corrupted images
- QR-only images
- Plain documents that are not payment receipts
"""
    with open(base_dir / "raw/not_receipt" / "README.md", "w") as f:
        f.write(readme_content)
        
if __name__ == "__main__":
    main()
