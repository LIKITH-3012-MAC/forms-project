import os
import shutil
import random
from pathlib import Path

def prepare_data():
    src_dir = Path("/Users/likithnaidu/Desktop/receipt_copies")
    base_dir = Path(__file__).parent.parent
    out_dir = base_dir / "processed_dataset" / "binary"
    
    if not src_dir.exists():
        print(f"Error: Source directory {src_dir} does not exist!")
        return

    # Clear previous dataset if any
    if out_dir.exists():
        print(f"Clearing existing output directory {out_dir}")
        shutil.rmtree(out_dir)
        
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Ingest files
    all_files = []
    for ext in ["*.jpg", "*.png", "*.jpeg", "*.webp", "*.JPG", "*.PNG", "*.JPEG", "*.WEBP"]:
        all_files.extend(src_dir.glob(ext))
        
    print(f"Found {len(all_files)} total images in {src_dir}")
    
    # Classify by prefix
    groups = {
        "paytm": [],
        "thread": [],
        "image1": []
    }
    
    for f in all_files:
        name = f.name.lower()
        if name.startswith("paytm"):
            groups["paytm"].append(f)
        elif name.startswith("thread"):
            groups["thread"].append(f)
        elif name.startswith("image1"):
            groups["image1"].append(f)
        else:
            print(f"Skipping unknown file: {f.name}")
            
    print(f"Groups parsed:")
    print(f"  paytm: {len(groups['paytm'])}")
    print(f"  thread: {len(groups['thread'])}")
    print(f"  image1: {len(groups['image1'])}")
    
    random.seed(42)
    splits = {"train": 0.7, "val": 0.15, "test": 0.15}
    
    for name, files in groups.items():
        if not files:
            continue
            
        random.shuffle(files)
        total = len(files)
        train_end = int(total * splits["train"])
        val_end = train_end + int(total * splits["val"])
        
        split_files = {
            "train": files[:train_end],
            "val": files[train_end:val_end],
            "test": files[val_end:]
        }
        
        # Decide class
        cls = "receipt" if name in ["paytm", "thread"] else "non_receipt"
        
        for split_name, s_files in split_files.items():
            split_dir = out_dir / split_name / cls
            split_dir.mkdir(parents=True, exist_ok=True)
            for i, f in enumerate(s_files):
                dest = split_dir / f"{name}_{split_name}_{i}{f.suffix}"
                shutil.copy2(f, dest)
                
    print("Dataset preparation complete!")
    # Print summary of output
    for split_name in ["train", "val", "test"]:
        for cls in ["receipt", "non_receipt"]:
            p = out_dir / split_name / cls
            count = len(list(p.glob("*"))) if p.exists() else 0
            print(f"  {split_name}/{cls}: {count} files")

if __name__ == "__main__":
    prepare_data()
