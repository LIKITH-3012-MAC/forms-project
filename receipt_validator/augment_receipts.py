import os
import argparse
from pathlib import Path
import random
import cv2
import numpy as np
import albumentations as A

def get_transform():
    return A.Compose([
        A.RandomBrightnessContrast(p=0.5),
        A.GaussianBlur(p=0.3),
        A.MotionBlur(p=0.2),
        A.GaussNoise(p=0.3),
        A.ImageCompression(quality_lower=30, quality_upper=90, p=0.3),
        A.Perspective(scale=(0.05, 0.1), p=0.3),
        A.Rotate(limit=10, p=0.5),
        A.RandomScale(scale_limit=0.2, p=0.5),
        A.RandomCrop(width=200, height=200, p=0.3),
        A.Downscale(scale_min=0.5, scale_max=0.9, p=0.2),
        A.Lambda(image=apply_glare, p=0.2),
        A.Lambda(image=apply_shadow, p=0.2),
        A.RandomBrightness(limit=(-0.4, 0), p=0.2),
        A.HueSaturationValue(p=0.3),
        A.Sharpen(p=0.2),
        A.PadIfNeeded(min_height=224, min_width=224, border_mode=cv2.BORDER_CONSTANT, p=0.2),
    ])

def apply_glare(image, **kwargs):
    h, w = image.shape[:2]
    overlay = np.zeros_like(image, dtype=np.uint8)
    # bright ellipse in random position
    center = (random.randint(int(w*0.3), int(w*0.7)), random.randint(int(h*0.3), int(h*0.7)))
    axes = (random.randint(int(w*0.1), int(w*0.2)), random.randint(int(h*0.1), int(h*0.2)))
    cv2.ellipse(overlay, center, axes, 0, 0, 360, (255,255,255), -1)
    alpha = random.uniform(0.1, 0.3)
    return cv2.addWeighted(image, 1.0, overlay, alpha, 0)

def apply_shadow(image, **kwargs):
    h, w = image.shape[:2]
    overlay = np.zeros_like(image, dtype=np.uint8)
    pts = np.array([
        [random.randint(0, w), random.randint(0, h)],
        [random.randint(0, w), random.randint(0, h)],
        [random.randint(0, w), random.randint(0, h)],
    ])
    cv2.fillPoly(overlay, [pts], (0,0,0))
    alpha = random.uniform(0.2, 0.4)
    return cv2.addWeighted(image, 1.0, overlay, alpha, 0)

def augment_folder(src_dir: Path, dest_dir: Path, aug_per_seed: int):
    transform = get_transform()
    for img_path in src_dir.iterdir():
        if img_path.is_file() and img_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            img = cv2.imread(str(img_path))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            for i in range(aug_per_seed):
                augmented = transform(image=img)['image']
                aug_name = f"{img_path.stem}_aug{i}{img_path.suffix}"
                cv2.imwrite(str(dest_dir / aug_name), cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR))

def main():
    parser = argparse.ArgumentParser(description="Augment receipt and not_receipt images.")
    parser.add_argument("--seed-dir", type=str, default="./receipt_validator/dataset/raw_seeds", help="Root of raw seed folders.")
    parser.add_argument("--output-dir", type=str, default="./receipt_validator/dataset/generated", help="Where to store augmented data.")
    parser.add_argument("--aug-per-seed-train", type=int, default=60)
    parser.add_argument("--aug-per-seed-val", type=int, default=20)
    parser.add_argument("--aug-per-seed-test", type=int, default=20)
    args = parser.parse_args()

    seed_root = Path(args.seed_dir)
    out_root = Path(args.output_dir)
    splits = {
        'train': args.aug_per_seed_train,
        'val': args.aug_per_seed_val,
        'test': args.aug_per_seed_test,
    }
    # Mapping seeds to splits (simple round-robin over available seeds)
    for cls in ['receipt', 'not_receipt']:
        src = seed_root / cls
        seed_files = sorted([p for p in src.iterdir() if p.is_file()])
        if not seed_files:
            print(f"No seed images found for {cls}, skipping augmentation.")
            continue
        for idx, seed_path in enumerate(seed_files):
            split_idx = idx % 3  # 0=train,1=val,2=test
            split_name = list(splits.keys())[split_idx]
            dest = out_root / split_name / cls
            dest.mkdir(parents=True, exist_ok=True)
            # copy original seed as part of dataset
            shutil.copy2(seed_path, dest / seed_path.name)
            augment_folder(Path(seed_path).parent, dest, splits[split_name])
    print("Augmentation completed.")

if __name__ == "__main__":
    main()
