import os
import shutil
from pathlib import Path

# Important: Only use these mappings AFTER visual inspection confirms the label.
# These paths are currently placeholder examples from the spec.
LOCAL_IMAGE_LABELS = {
    "/Users/likithnaidu/Desktop/forms-project/paytm.jpg": "payment_receipt/paytm",
    "/Users/likithnaidu/Desktop/forms-project/image1.jpg": "non_receipt/random_photo",
    "/Users/likithnaidu/Desktop/forms-project/thread-166147785-16862839286301891037.png": "payment_receipt/phonepe"
}

def setup_dirs(base_dir):
    raw_dir = base_dir / "raw_labeled"
    orig_dir = base_dir / "original_local_images"
    raw_dir.mkdir(parents=True, exist_ok=True)
    orig_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir, orig_dir

def copy_local_images():
    base_dir = Path(__file__).parent.parent / "dataset_private"
    raw_dir, orig_dir = setup_dirs(base_dir)
    
    print(f"Preparing to copy {len(LOCAL_IMAGE_LABELS)} local images into private dataset structure...")
    
    for src_path_str, relative_class_path in LOCAL_IMAGE_LABELS.items():
        src_path = Path(src_path_str)
        if not src_path.exists():
            print(f"⚠️ Source file missing: {src_path}")
            continue
            
        # Copy to original backup
        backup_path = orig_dir / src_path.name
        if not backup_path.exists():
            shutil.copy2(src_path, backup_path)
            
        # Copy to labeled folder
        target_dir = raw_dir / relative_class_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / src_path.name
        if not target_path.exists():
            shutil.copy2(src_path, target_path)
            print(f"✅ Copied {src_path.name} -> {target_path}")
        else:
            print(f"ℹ️ Already exists: {target_path}")

if __name__ == "__main__":
    copy_local_images()
