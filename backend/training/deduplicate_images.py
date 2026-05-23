import os
import shutil
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import imagehash
import matplotlib.pyplot as plt

def get_file_hash(filepath):
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_synthetic_negatives(not_receipt_dir):
    """Generate diverse synthetic non-receipt images for robust negative-class training."""
    print("Generating synthetic non-receipt images...")
    
    # 1. Solid colors
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), 
        (255, 255, 0), (255, 0, 255), (0, 255, 255), 
        (0, 0, 0), (128, 128, 128), (255, 255, 255), (255, 128, 0)
    ]
    for idx, c in enumerate(colors):
        img = Image.new("RGB", (224, 224), c)
        img.save(not_receipt_dir / f"synthetic_solid_{idx}.png")
        
    # 2. Noise images
    for idx in range(10):
        arr = np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        img.save(not_receipt_dir / f"synthetic_noise_{idx}.png")
        
    # 3. Geometric patterns
    for idx in range(20):
        img = Image.new("RGB", (224, 224), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        # Draw random shapes
        for _ in range(10):
            shape_type = np.random.choice(["circle", "rectangle", "line"])
            coords = np.random.randint(10, 210, 4)
            color = tuple(np.random.randint(0, 256, 3).tolist())
            x0, x1 = sorted([coords[0], coords[2]])
            y0, y1 = sorted([coords[1], coords[3]])
            if shape_type == "circle":
                r = np.random.randint(5, 50)
                draw.ellipse([x0-r, y0-r, x0+r, y0+r], fill=color)
            elif shape_type == "rectangle":
                draw.rectangle([x0, y0, x1, y1], fill=color)
            else:
                draw.line([coords[0], coords[1], coords[2], coords[3]], fill=color, width=np.random.randint(1, 5))
        img.save(not_receipt_dir / f"synthetic_pattern_{idx}.png")
        
    # 4. Text documents (not receipts)
    for idx in range(20):
        img = Image.new("RGB", (224, 224), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw lines of text simulator
        for line_y in range(20, 210, 15):
            line_len = np.random.randint(50, 180)
            draw.line([20, line_y, 20 + line_len, line_y], fill=(50, 50, 50), width=4)
        img.save(not_receipt_dir / f"synthetic_doc_{idx}.png")
        
    # 5. Matplotlib plots
    plt.ioff()
    for idx in range(20):
        fig, ax = plt.subplots(figsize=(3, 3), dpi=75) # ~225x225
        plot_type = np.random.choice(["line", "bar", "scatter"])
        x = np.linspace(0, 10, 20)
        if plot_type == "line":
            ax.plot(x, np.sin(x + idx))
        elif plot_type == "bar":
            ax.bar(x, np.abs(np.random.randn(20)))
        else:
            ax.scatter(x, np.random.randn(20))
        ax.set_title(f"Plot {idx}")
        fig.tight_layout()
        plot_path = not_receipt_dir / f"synthetic_plot_{idx}.png"
        fig.savefig(str(plot_path))
        plt.close(fig)
        
    print(f"✓ Generated 80 synthetic negative images in {not_receipt_dir}")

def collect_real_negatives(not_receipt_dir):
    """Collect real world non-receipt images from venv and sklearn."""
    print("Collecting real-world non-receipt images...")
    base_proj = Path(__file__).parent.parent.parent
    
    # 1. Look for scikit-learn dataset images
    sklearn_img_dir = base_proj / "backend/venv/lib"
    sklearn_images = list(sklearn_img_dir.glob("**/sklearn/datasets/images/*.jpg"))
    for idx, f in enumerate(sklearn_images):
        dest = not_receipt_dir / f"real_sklearn_{idx}_{f.name}"
        shutil.copy2(f, dest)
        print(f"  Found sklearn image: {f.name}")
        
    # 2. Extract representative image1 (human photo) from old dataset
    old_binary_dir = base_proj / "ml_receipt_model/processed_dataset/binary"
    if old_binary_dir.exists():
        old_non_receipts = list(old_binary_dir.glob("**/non_receipt/image1*.jpg"))
        if old_non_receipts:
            # All are copies, take the first one
            shutil.copy2(old_non_receipts[0], not_receipt_dir / "real_human_image1.jpg")
            print("  Found old human photo (image1)")
            
    print(f"✓ Done collecting real-world negatives.")

def deduplicate_class(src_dir, dest_dir):
    """Perform deduplication on a class directory to prevent data leakage."""
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    
    files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        files.extend(src_path.glob(ext))
        
    seen_phash = {}
    seen_exact = {}
    copied_count = 0
    
    for f in files:
        # Exact SHA256 Check
        sha = get_file_hash(f)
        if sha in seen_exact:
            continue
        seen_exact[sha] = f
        
        # Perceptual hash check (for near duplicates)
        try:
            with Image.open(f) as img:
                h = imagehash.phash(img)
                # Allow a small threshold of similarity (hamming distance <= 2)
                is_near_dup = False
                for existing_h, existing_file in seen_phash.items():
                    if h - existing_h <= 2:
                        is_near_dup = True
                        break
                if not is_near_dup:
                    seen_phash[h] = f
                    shutil.copy2(f, dest_path / f.name)
                    copied_count += 1
        except Exception as e:
            print(f"  Error reading {f.name}: {e}")
            # Fallback to copy if imagehash fails
            shutil.copy2(f, dest_path / f.name)
            copied_count += 1
            
    print(f"✓ Deduplicated {src_path.name}: {len(files)} raw files -> {copied_count} unique files in {dest_path}")

def main():
    base_dir = Path(__file__).parent.parent.parent / "dataset"
    
    # 1. Collect negatives first
    generate_synthetic_negatives(base_dir / "raw/not_receipt")
    collect_real_negatives(base_dir / "raw/not_receipt")
    
    # 2. Deduplicate both classes into deduplicated/
    deduplicate_class(base_dir / "raw/receipt", base_dir / "deduplicated/receipt")
    deduplicate_class(base_dir / "raw/not_receipt", base_dir / "deduplicated/not_receipt")

if __name__ == "__main__":
    main()
