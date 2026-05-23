import os
import shutil
import random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import albumentations as A

random.seed(42)

def split_dataset():
    """Split deduplicated images into train/val/test folders.
    Receipts are split by family (seed id) to avoid any leakage.
    Not_receipts are split randomly.
    """
    base_dir = Path(__file__).parent.parent.parent / "dataset"
    
    # 1. Split Receipts by family (there are 5 seeds from 5 original receipt families)
    receipt_files = sorted(list((base_dir / "deduplicated/receipt").glob("*")))
    
    # Let's shuffle and assign to train/val/test
    # 3 seeds for train, 1 seed for val, 1 seed for test
    random.shuffle(receipt_files)
    
    train_receipt_seeds = receipt_files[:3]
    val_receipt_seeds = receipt_files[3:4]
    test_receipt_seeds = receipt_files[4:]
    
    for f in train_receipt_seeds:
        shutil.copy2(f, base_dir / "train/receipt" / f.name)
    for f in val_receipt_seeds:
        shutil.copy2(f, base_dir / "val/receipt" / f.name)
    for f in test_receipt_seeds:
        shutil.copy2(f, base_dir / "test/receipt" / f.name)
        
    print(f"Receipt seeds split: Train={len(train_receipt_seeds)}, Val={len(val_receipt_seeds)}, Test={len(test_receipt_seeds)}")
    
    # 2. Split Not_receipts randomly
    not_receipt_files = sorted(list((base_dir / "deduplicated/not_receipt").glob("*")))
    random.shuffle(not_receipt_files)
    
    total = len(not_receipt_files)
    train_end = int(total * 0.70)
    val_end = train_end + int(total * 0.15)
    
    train_not_receipts = not_receipt_files[:train_end]
    val_not_receipts = not_receipt_files[train_end:val_end]
    test_not_receipts = not_receipt_files[val_end:]
    
    for f in train_not_receipts:
        shutil.copy2(f, base_dir / "train/not_receipt" / f.name)
    for f in val_not_receipts:
        shutil.copy2(f, base_dir / "val/not_receipt" / f.name)
    for f in test_not_receipts:
        shutil.copy2(f, base_dir / "test/not_receipt" / f.name)
        
    print(f"Not_receipt split: Train={len(train_not_receipts)}, Val={len(val_not_receipts)}, Test={len(test_not_receipts)}")
    return base_dir

def get_augmentation_pipeline():
    """Define realistic albumentations pipeline for receipt screenshots."""
    return A.Compose([
        A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.05, rotate_limit=8, border_mode=cv2.BORDER_CONSTANT, value=(255, 255, 255), p=0.7),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.8),
        A.GaussianBlur(blur_limit=(3, 5), p=0.4),
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
        A.ImageCompression(quality_range=(30, 80), p=0.5),
        A.Perspective(scale=(0.01, 0.05), border_mode=cv2.BORDER_CONSTANT, pad_val=(255, 255, 255), p=0.4),
        # Sharpening, border shifts, shadow/glare are simulated implicitly or can be added
        A.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.02, p=0.4),
    ])

def augment_train_class(class_dir, num_target_samples):
    """Augment files in train class folder up to num_target_samples."""
    class_path = Path(class_dir)
    files = sorted(list(class_path.glob("*")))
    if not files:
        return
        
    # Exclude any previously augmented files if script is re-run
    seed_files = [f for f in files if "aug_" not in f.name]
    num_seeds = len(seed_files)
    
    # Calculate how many augs per seed
    augs_needed = num_target_samples - num_seeds
    if augs_needed <= 0:
        print(f"Already have {len(files)} files in {class_path.name}. No augmentations needed.")
        return
        
    augs_per_seed = int(np.ceil(augs_needed / num_seeds))
    print(f"Augmenting {class_path.name}: {num_seeds} seeds, producing ~{augs_per_seed} augmentations per seed...")
    
    transform = get_augmentation_pipeline()
    total_generated = 0
    
    for f in seed_files:
        try:
            img = cv2.imread(str(f))
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            for i in range(augs_per_seed):
                if total_generated >= augs_needed:
                    break
                augmented = transform(image=img_rgb)["image"]
                augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR)
                
                dest_path = class_path / f"aug_{f.stem}_{i}.png"
                cv2.imwrite(str(dest_path), augmented_bgr)
                total_generated += 1
        except Exception as e:
            print(f"Error augmenting {f.name}: {e}")
            
    print(f"✓ Generated {total_generated} augmented samples in {class_path}")

def main():
    base_dir = split_dataset()
    
    # Augment training split ONLY
    # Target 300 samples per class in training
    augment_train_class(base_dir / "train/receipt", 300)
    augment_train_class(base_dir / "train/not_receipt", 300)

if __name__ == "__main__":
    main()
