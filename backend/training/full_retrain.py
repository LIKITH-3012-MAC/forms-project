"""
Full end-to-end retraining pipeline for receipt classifier.
1. Ingest new photos from PHOTOS-TRAIN folder
2. Generate diverse synthetic negatives
3. Apply heavy augmentation to receipt images
4. Re-extract features via ONNX feature extractor
5. Train multiple classifiers with StratifiedKFold cross-validation
6. Calibrate probabilities and select the best model
7. Save final classifier + scaler + metrics
"""

import os
import sys
import json
import shutil
import random
import hashlib
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2

# ─── Configuration ───────────────────────────────────────────────────────
NEW_PHOTOS_DIR = Path("/Users/likithnaidu/Desktop/PHOTOS-TRAIN/photos")
BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "dataset"
MODELS_DIR = BASE_DIR / "backend" / "models"
FEATURES_DIR = MODELS_DIR / "features"

TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR = DATASET_DIR / "val"
TEST_DIR = DATASET_DIR / "test"

# Augmentation count per original receipt image for training set
AUGMENT_PER_IMAGE = 8
# Number of synthetic negatives to generate
NUM_SYNTHETIC_NEGATIVES = 500
# Target image size for feature extraction
IMG_SIZE = (224, 224)

random.seed(42)
np.random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Ingest new photos into dataset splits
# ═══════════════════════════════════════════════════════════════════════

def get_image_hash(path):
    """Get a perceptual hash to avoid exact duplicates."""
    try:
        img = Image.open(path).convert("RGB").resize((64, 64))
        return hashlib.md5(np.array(img).tobytes()).hexdigest()
    except Exception:
        return None


def ingest_new_photos():
    """Copy new photos into train/val/test receipt folders with proper splitting."""
    print("\n" + "="*70)
    print("STEP 1: Ingesting new photos from PHOTOS-TRAIN")
    print("="*70)

    if not NEW_PHOTOS_DIR.exists():
        print(f"ERROR: {NEW_PHOTOS_DIR} does not exist!")
        sys.exit(1)

    # Collect all image files
    image_files = sorted([
        f for f in NEW_PHOTOS_DIR.iterdir()
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
        and not f.name.startswith('.')
    ])
    print(f"Found {len(image_files)} images in {NEW_PHOTOS_DIR}")

    # Get hashes of existing images in dataset to avoid duplicates
    existing_hashes = set()
    for split in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
        receipt_dir = split / "receipt"
        if receipt_dir.exists():
            for f in receipt_dir.iterdir():
                h = get_image_hash(f)
                if h:
                    existing_hashes.add(h)

    # Filter out duplicates
    new_images = []
    for f in image_files:
        h = get_image_hash(f)
        if h and h not in existing_hashes:
            new_images.append(f)
            existing_hashes.add(h)
        elif h in existing_hashes:
            print(f"  SKIP (duplicate): {f.name}")

    print(f"New unique images to add: {len(new_images)}")

    if len(new_images) == 0:
        print("No new images to add.")
        return

    # Shuffle and split: 70% train, 15% val, 15% test
    random.shuffle(new_images)
    n = len(new_images)
    n_train = max(1, int(n * 0.70))
    n_val = max(1, int(n * 0.15))
    n_test = n - n_train - n_val

    train_imgs = new_images[:n_train]
    val_imgs = new_images[n_train:n_train + n_val]
    test_imgs = new_images[n_train + n_val:]

    print(f"  Split: train={len(train_imgs)}, val={len(val_imgs)}, test={len(test_imgs)}")

    for split_name, split_imgs, split_dir in [
        ("train", train_imgs, TRAIN_DIR),
        ("val", val_imgs, VAL_DIR),
        ("test", test_imgs, TEST_DIR),
    ]:
        receipt_dir = split_dir / "receipt"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        for img_path in split_imgs:
            dest = receipt_dir / f"new_{img_path.name}"
            if not dest.exists():
                shutil.copy2(img_path, dest)
                print(f"  → {split_name}/receipt/{dest.name}")

    print("✓ New photos ingested into dataset splits.")


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Generate diverse synthetic negative samples
# ═══════════════════════════════════════════════════════════════════════

def generate_gradient_image(size=(224, 224)):
    """Generate a random gradient image."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    c1 = np.random.randint(0, 255, 3)
    c2 = np.random.randint(0, 255, 3)
    for y in range(size[1]):
        ratio = y / size[1]
        color = (c1 * (1 - ratio) + c2 * ratio).astype(np.uint8)
        img[y, :] = color
    return Image.fromarray(img)


def generate_noise_image(size=(224, 224)):
    """Generate random noise image."""
    noise = np.random.randint(0, 255, (size[1], size[0], 3), dtype=np.uint8)
    return Image.fromarray(noise)


def generate_solid_color(size=(224, 224)):
    """Generate solid color image."""
    color = tuple(np.random.randint(0, 255, 3).tolist())
    return Image.new("RGB", size, color)


def generate_text_screenshot(size=(224, 224)):
    """Generate a fake text screenshot (chat, article, etc.)."""
    bg_colors = [(255, 255, 255), (240, 240, 240), (30, 30, 30), (245, 245, 220)]
    bg = random.choice(bg_colors)
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)

    # Draw random text-like lines
    text_color = (0, 0, 0) if bg[0] > 128 else (255, 255, 255)
    y = 10
    while y < size[1] - 20:
        line_width = random.randint(80, size[0] - 20)
        draw.rectangle([10, y, 10 + line_width, y + 8], fill=text_color)
        y += random.randint(14, 25)

    return img


def generate_selfie_like(size=(224, 224)):
    """Generate a selfie-like image with skin tones and oval shape."""
    bg = random.choice([(200, 220, 255), (180, 255, 200), (255, 230, 200), (60, 60, 80)])
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)

    # Skin-tone oval (face-like)
    skin_tones = [(255, 224, 189), (241, 194, 125), (198, 134, 66), (141, 85, 36)]
    skin = random.choice(skin_tones)
    cx, cy = size[0] // 2, size[1] // 2 - 20
    rw, rh = random.randint(40, 70), random.randint(50, 80)
    draw.ellipse([cx-rw, cy-rh, cx+rw, cy+rh], fill=skin)

    # Hair
    hair_color = random.choice([(30, 20, 10), (60, 40, 20), (100, 60, 30)])
    draw.ellipse([cx-rw-5, cy-rh-15, cx+rw+5, cy-rh+20], fill=hair_color)

    # Eyes
    draw.ellipse([cx-20, cy-10, cx-10, cy], fill=(255, 255, 255))
    draw.ellipse([cx+10, cy-10, cx+20, cy], fill=(255, 255, 255))

    return img


def generate_nature_like(size=(224, 224)):
    """Generate nature-like scenery (sky + green ground)."""
    img = Image.new("RGB", size, (135, 206, 235))
    draw = ImageDraw.Draw(img)
    horizon = random.randint(size[1]//3, 2*size[1]//3)
    greens = [(34, 139, 34), (0, 128, 0), (85, 107, 47)]
    draw.rectangle([0, horizon, size[0], size[1]], fill=random.choice(greens))
    # Sun
    sx, sy = random.randint(20, size[0]-20), random.randint(10, horizon-20)
    sr = random.randint(15, 30)
    draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(255, 255, 0))
    return img


def generate_ui_screenshot(size=(224, 224)):
    """Generate a generic UI screenshot (not payment-related)."""
    bg = random.choice([(255, 255, 255), (245, 245, 245), (18, 18, 18)])
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)

    # Status bar
    bar_color = random.choice([(33, 150, 243), (76, 175, 80), (244, 67, 54), (156, 39, 176)])
    draw.rectangle([0, 0, size[0], 30], fill=bar_color)

    # Random rectangles (buttons/cards)
    card_color = (200, 200, 200) if bg[0] > 128 else (50, 50, 50)
    for _ in range(random.randint(2, 6)):
        x1 = random.randint(10, size[0]//2)
        y1 = random.randint(40, size[1]-60)
        w = random.randint(60, size[0]-x1-10)
        h = random.randint(20, 50)
        draw.rectangle([x1, y1, x1+w, y1+h], fill=card_color, outline=(100,100,100))

    return img


def generate_meme_like(size=(224, 224)):
    """Generate meme-like image with bold text blocks."""
    bg = random.choice([(0, 0, 0), (255, 255, 255), (255, 255, 0)])
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)

    # Top and bottom text blocks
    text_bg = (0, 0, 0) if bg[0] > 128 else (255, 255, 255)
    draw.rectangle([0, 0, size[0], 40], fill=text_bg)
    draw.rectangle([0, size[1]-40, size[0], size[1]], fill=text_bg)

    # Center image block
    center_color = tuple(np.random.randint(50, 200, 3).tolist())
    draw.rectangle([10, 50, size[0]-10, size[1]-50], fill=center_color)

    return img


def generate_synthetic_negatives():
    """Generate diverse synthetic negative images."""
    print("\n" + "="*70)
    print("STEP 2: Generating synthetic negative samples")
    print("="*70)

    generators = [
        ("gradient", generate_gradient_image),
        ("noise", generate_noise_image),
        ("solid", generate_solid_color),
        ("text_screenshot", generate_text_screenshot),
        ("selfie", generate_selfie_like),
        ("nature", generate_nature_like),
        ("ui_screenshot", generate_ui_screenshot),
        ("meme", generate_meme_like),
    ]

    # Split counts: 80% train, 10% val, 10% test
    n_train = int(NUM_SYNTHETIC_NEGATIVES * 0.80)
    n_val = int(NUM_SYNTHETIC_NEGATIVES * 0.10)
    n_test = NUM_SYNTHETIC_NEGATIVES - n_train - n_val

    for split_name, count, split_dir in [
        ("train", n_train, TRAIN_DIR),
        ("val", n_val, VAL_DIR),
        ("test", n_test, TEST_DIR),
    ]:
        neg_dir = split_dir / "not_receipt"
        neg_dir.mkdir(parents=True, exist_ok=True)

        generated = 0
        for i in range(count):
            gen_name, gen_func = random.choice(generators)
            img = gen_func()

            # Random post-processing
            if random.random() < 0.3:
                img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 2.0)))
            if random.random() < 0.3:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(random.uniform(0.5, 1.5))

            fname = f"synth_{gen_name}_{i:04d}.jpg"
            img.save(neg_dir / fname, "JPEG", quality=85)
            generated += 1

        print(f"  {split_name}: generated {generated} synthetic negatives")

    print("✓ Synthetic negatives generated.")


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Augment receipt images in training set
# ═══════════════════════════════════════════════════════════════════════

def augment_image(img):
    """Apply random augmentation to a PIL Image."""
    augmented = img.copy()

    # Random rotation
    if random.random() < 0.4:
        angle = random.uniform(-15, 15)
        augmented = augmented.rotate(angle, fillcolor=(0, 0, 0), expand=False)

    # Random crop and resize back
    if random.random() < 0.5:
        w, h = augmented.size
        crop_pct = random.uniform(0.05, 0.15)
        left = int(w * crop_pct * random.random())
        top = int(h * crop_pct * random.random())
        right = w - int(w * crop_pct * random.random())
        bottom = h - int(h * crop_pct * random.random())
        augmented = augmented.crop((left, top, right, bottom))
        augmented = augmented.resize((w, h), Image.BILINEAR)

    # Brightness
    if random.random() < 0.5:
        enhancer = ImageEnhance.Brightness(augmented)
        augmented = enhancer.enhance(random.uniform(0.6, 1.4))

    # Contrast
    if random.random() < 0.4:
        enhancer = ImageEnhance.Contrast(augmented)
        augmented = enhancer.enhance(random.uniform(0.7, 1.3))

    # Color saturation
    if random.random() < 0.3:
        enhancer = ImageEnhance.Color(augmented)
        augmented = enhancer.enhance(random.uniform(0.5, 1.5))

    # Sharpness
    if random.random() < 0.3:
        enhancer = ImageEnhance.Sharpness(augmented)
        augmented = enhancer.enhance(random.uniform(0.5, 2.0))

    # Gaussian blur
    if random.random() < 0.2:
        augmented = augmented.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.5)))

    # Horizontal flip (mirror)
    if random.random() < 0.3:
        augmented = augmented.transpose(Image.FLIP_LEFT_RIGHT)

    # Add noise
    if random.random() < 0.3:
        arr = np.array(augmented, dtype=np.float32)
        noise = np.random.normal(0, random.uniform(3, 15), arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        augmented = Image.fromarray(arr)

    # JPEG compression artifact simulation
    if random.random() < 0.3:
        import io
        buffer = io.BytesIO()
        augmented.save(buffer, "JPEG", quality=random.randint(20, 60))
        buffer.seek(0)
        augmented = Image.open(buffer).copy()

    return augmented


def augment_training_receipts():
    """Create augmented copies of receipt images in training set."""
    print("\n" + "="*70)
    print("STEP 3: Augmenting receipt training images")
    print("="*70)

    receipt_dir = TRAIN_DIR / "receipt"
    if not receipt_dir.exists():
        print("ERROR: No receipt training directory found!")
        return

    originals = [
        f for f in receipt_dir.iterdir()
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
        and not f.name.startswith('aug_')
    ]
    print(f"Found {len(originals)} original receipt images in training set")

    total_augmented = 0
    for img_path in originals:
        try:
            img = Image.open(img_path).convert("RGB")
            for aug_idx in range(AUGMENT_PER_IMAGE):
                augmented = augment_image(img)
                aug_name = f"aug_{img_path.stem}_{aug_idx:02d}.jpg"
                augmented.save(receipt_dir / aug_name, "JPEG", quality=90)
                total_augmented += 1
        except Exception as e:
            print(f"  Error augmenting {img_path.name}: {e}")

    print(f"✓ Created {total_augmented} augmented receipt images")

    # Count final totals
    final_count = len(list(receipt_dir.glob("*")))
    print(f"  Total receipt images in training: {final_count}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Extract fused features via ONNX
# ═══════════════════════════════════════════════════════════════════════

def compute_blur_score(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def compute_brightness(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(np.mean(gray))


def extract_features():
    """Extract features using the ONNX feature extractor."""
    print("\n" + "="*70)
    print("STEP 4: Extracting fused features via ONNX")
    print("="*70)

    import onnxruntime as ort

    onnx_path = MODELS_DIR / "receipt_feature_extractor.onnx"
    if not onnx_path.exists():
        print(f"ERROR: ONNX model not found at {onnx_path}")
        sys.exit(1)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print(f"  ONNX model loaded. Input: {input_name}, Output: {output_name}")

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    for split_name in ["train", "val", "test"]:
        split_dir = DATASET_DIR / split_name
        if not split_dir.exists():
            print(f"Skipping {split_name}: directory not found")
            continue

        print(f"\nExtracting features for {split_name}...")

        all_features = []
        all_labels = []
        all_filenames = []

        for class_name, label in [("not_receipt", 0), ("receipt", 1)]:
            class_dir = split_dir / class_name
            if not class_dir.exists():
                continue

            files = sorted([
                f for f in class_dir.iterdir()
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
            ])

            extracted = 0
            for f in files:
                try:
                    img = Image.open(f).convert("RGB")
                    img_resized = img.resize(IMG_SIZE, Image.BILINEAR)
                    img_array = np.array(img_resized, dtype=np.float32)
                    img_batch = np.expand_dims(img_array, axis=0)

                    outputs = session.run([output_name], {input_name: img_batch})
                    visual_embedding = outputs[0].flatten()

                    # Quality features
                    img_orig_array = np.array(img)
                    blur_score = compute_blur_score(img_orig_array)
                    brightness = compute_brightness(img_orig_array)
                    orig_w, orig_h = img.size
                    aspect_ratio = orig_w / max(orig_h, 1)

                    quality_features = np.array([blur_score, brightness, aspect_ratio, orig_w, orig_h], dtype=np.float32)
                    combined = np.concatenate([visual_embedding, quality_features])

                    all_features.append(combined)
                    all_labels.append(label)
                    all_filenames.append(str(f))
                    extracted += 1
                except Exception as e:
                    print(f"  Error processing {f.name}: {e}")

            print(f"  {class_name}: {extracted} samples extracted")

        X = np.array(all_features, dtype=np.float32)
        y = np.array(all_labels, dtype=np.int32)

        np.save(str(FEATURES_DIR / f"X_{split_name}.npy"), X)
        np.save(str(FEATURES_DIR / f"y_{split_name}.npy"), y)

        with open(FEATURES_DIR / f"filenames_{split_name}.json", "w") as f:
            json.dump(all_filenames, f, indent=2)

        print(f"  Saved {split_name}: X shape={X.shape}, y shape={y.shape}")
        print(f"  Class distribution: not_receipt={np.sum(y==0)}, receipt={np.sum(y==1)}")

    print("\n✓ Feature extraction complete.")


# ═══════════════════════════════════════════════════════════════════════
# STEP 5: Train classifiers with cross-validation
# ═══════════════════════════════════════════════════════════════════════

def train_and_select_model():
    """Train multiple classifiers, cross-validate, calibrate, and select the best."""
    print("\n" + "="*70)
    print("STEP 5: Training classifiers with cross-validation")
    print("="*70)

    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.ensemble import (
        HistGradientBoostingClassifier, ExtraTreesClassifier,
        RandomForestClassifier, GradientBoostingClassifier
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, precision_score,
        recall_score, f1_score, roc_auc_score, brier_score_loss,
        classification_report
    )
    from sklearn.calibration import CalibratedClassifierCV
    import joblib

    # Load features
    X_train = np.load(str(FEATURES_DIR / "X_train.npy"))
    y_train = np.load(str(FEATURES_DIR / "y_train.npy"))
    X_val = np.load(str(FEATURES_DIR / "X_val.npy"))
    y_val = np.load(str(FEATURES_DIR / "y_val.npy"))
    X_test = np.load(str(FEATURES_DIR / "X_test.npy"))
    y_test = np.load(str(FEATURES_DIR / "y_test.npy"))

    print(f"Train: X={X_train.shape}, receipt={np.sum(y_train==1)}, not_receipt={np.sum(y_train==0)}")
    print(f"Val:   X={X_val.shape}, receipt={np.sum(y_val==1)}, not_receipt={np.sum(y_val==0)}")
    print(f"Test:  X={X_test.shape}, receipt={np.sum(y_test==1)}, not_receipt={np.sum(y_test==0)}")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Save scaler
    joblib.dump(scaler, str(MODELS_DIR / "feature_scaler.pkl"))
    print("✓ Feature scaler saved.")

    # Define candidate models with tuned hyperparameters
    candidates = {
        "LogisticRegression": LogisticRegression(
            class_weight="balanced", max_iter=5000, C=0.5, solver="lbfgs"
        ),
        "SVC_RBF": SVC(
            kernel="rbf", probability=True, class_weight="balanced",
            C=10.0, gamma="scale"
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=500, learning_rate=0.05, max_depth=6,
            min_samples_leaf=3, l2_regularization=0.1
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=500, class_weight="balanced",
            max_depth=15, min_samples_leaf=2, n_jobs=-1
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=500, class_weight="balanced",
            max_depth=15, min_samples_leaf=2, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=5,
            min_samples_leaf=3, subsample=0.8
        ),
    }

    # Cross-validation on training data
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    results = []
    trained_models = {}

    for name, model in candidates.items():
        print(f"\nTraining {name}...")

        # 5-fold CV on training set
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=skf, scoring="balanced_accuracy")
        print(f"  CV Balanced Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # Fit on full training set
        model.fit(X_train_scaled, y_train)

        # Evaluate on validation set
        y_pred_val = model.predict(X_val_scaled)
        y_proba_val = model.predict_proba(X_val_scaled)[:, 1] if hasattr(model, "predict_proba") else None

        metrics = {
            "name": name,
            "cv_balanced_accuracy_mean": float(cv_scores.mean()),
            "cv_balanced_accuracy_std": float(cv_scores.std()),
            "val_accuracy": float(accuracy_score(y_val, y_pred_val)),
            "val_balanced_accuracy": float(balanced_accuracy_score(y_val, y_pred_val)),
            "val_precision_receipt": float(precision_score(y_val, y_pred_val, pos_label=1, zero_division=0)),
            "val_recall_receipt": float(recall_score(y_val, y_pred_val, pos_label=1, zero_division=0)),
            "val_f1_receipt": float(f1_score(y_val, y_pred_val, pos_label=1, zero_division=0)),
        }

        # False positive rate
        fp = np.sum((y_pred_val == 1) & (y_val == 0))
        tn = np.sum((y_pred_val == 0) & (y_val == 0))
        metrics["val_false_positive_rate"] = float(fp / max(fp + tn, 1))

        if y_proba_val is not None:
            try:
                metrics["val_roc_auc"] = float(roc_auc_score(y_val, y_proba_val))
            except ValueError:
                metrics["val_roc_auc"] = None

        results.append(metrics)
        trained_models[name] = model

        print(f"  Val Accuracy: {metrics['val_accuracy']:.4f}")
        print(f"  Val Balanced Accuracy: {metrics['val_balanced_accuracy']:.4f}")
        print(f"  Val Precision (receipt): {metrics['val_precision_receipt']:.4f}")
        print(f"  Val Recall (receipt): {metrics['val_recall_receipt']:.4f}")
        print(f"  Val F1 (receipt): {metrics['val_f1_receipt']:.4f}")
        print(f"  Val FP Rate: {metrics['val_false_positive_rate']:.4f}")

    # Select best model: prioritize low FP rate + high recall + high CV score
    print("\n" + "-"*50)
    print("Selecting best model...")

    best_result = None
    best_score = -float('inf')

    for r in results:
        fp_rate = r.get("val_false_positive_rate", 1.0)
        recall = r.get("val_recall_receipt", 0.0)
        cv_mean = r.get("cv_balanced_accuracy_mean", 0.0)
        bal_acc = r.get("val_balanced_accuracy", 0.0)

        # Higher is better: recall + cv_mean + bal_acc - 3*fp_rate
        score = recall + cv_mean + bal_acc - 3 * fp_rate
        if score > best_score:
            best_score = score
            best_result = r

    best_name = best_result["name"]
    print(f"✓ Selected: {best_name}")

    # Calibrate the best model
    best_model = trained_models[best_name]

    # Use isotonic calibration with cross-validation on combined train+val
    X_cal = np.vstack([X_train_scaled, X_val_scaled])
    y_cal = np.concatenate([y_train, y_val])

    try:
        from sklearn.calibration import FrozenEstimator
        calibrated = CalibratedClassifierCV(
            estimator=FrozenEstimator(best_model), method="isotonic"
        )
        calibrated.fit(X_val_scaled, y_val)
    except ImportError:
        # Fallback for older sklearn
        calibrated = CalibratedClassifierCV(
            estimator=best_model, cv="prefit", method="isotonic"
        )
        calibrated.fit(X_val_scaled, y_val)

    print("✓ Model calibrated with isotonic regression.")

    # Final evaluation on TEST set
    y_pred_test = calibrated.predict(X_test_scaled)
    y_proba_test = calibrated.predict_proba(X_test_scaled)[:, 1]

    test_metrics = {
        "selected_model": best_name,
        "calibration_method": "isotonic",
        "test_accuracy": float(accuracy_score(y_test, y_pred_test)),
        "test_balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred_test)),
        "test_precision_receipt": float(precision_score(y_test, y_pred_test, pos_label=1, zero_division=0)),
        "test_recall_receipt": float(recall_score(y_test, y_pred_test, pos_label=1, zero_division=0)),
        "test_f1_receipt": float(f1_score(y_test, y_pred_test, pos_label=1, zero_division=0)),
        "test_brier_score": float(brier_score_loss(y_test, y_proba_test)),
    }

    try:
        test_metrics["test_roc_auc"] = float(roc_auc_score(y_test, y_proba_test))
    except ValueError:
        test_metrics["test_roc_auc"] = None

    # False positive rate on test
    fp_test = np.sum((y_pred_test == 1) & (y_test == 0))
    tn_test = np.sum((y_pred_test == 0) & (y_test == 0))
    test_metrics["test_false_positive_rate"] = float(fp_test / max(fp_test + tn_test, 1))

    print(f"\n{'='*50}")
    print(f"FINAL TEST RESULTS ({best_name} + isotonic calibration)")
    print(f"{'='*50}")
    print(classification_report(y_test, y_pred_test, target_names=["not_receipt", "receipt"]))
    for k, v in test_metrics.items():
        print(f"  {k}: {v}")

    # Save final model
    final_path = MODELS_DIR / "receipt_classifier.pkl"
    joblib.dump(calibrated, str(final_path))
    print(f"\n✓ Final calibrated classifier saved to: {final_path}")

    # Save all candidate results
    with open(MODELS_DIR / "candidate_model_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save model config
    config = {
        "model_name": best_name,
        "calibration": "isotonic",
        "feature_dim": int(X_train.shape[1]),
        "visual_embedding_dim": int(X_train.shape[1] - 5),
        "quality_features": ["blur_score", "brightness", "aspect_ratio", "width", "height"],
        "classes": ["not_receipt", "receipt"],
        "training_samples": {
            "train_receipt": int(np.sum(y_train == 1)),
            "train_not_receipt": int(np.sum(y_train == 0)),
            "val_receipt": int(np.sum(y_val == 1)),
            "val_not_receipt": int(np.sum(y_val == 0)),
            "test_receipt": int(np.sum(y_test == 1)),
            "test_not_receipt": int(np.sum(y_test == 0)),
        },
        "thresholds": {
            "likely_receipt": 0.92,
            "uncertain_low": 0.70,
            "not_receipt": 0.70
        },
    }

    with open(MODELS_DIR / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Save training metrics
    with open(MODELS_DIR / "training_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    print("✓ model_config.json and training_metrics.json saved.")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  FULL RECEIPT CLASSIFIER RETRAINING PIPELINE            ║")
    print("║  Using 37 new photos from PHOTOS-TRAIN                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    ingest_new_photos()
    generate_synthetic_negatives()
    augment_training_receipts()
    extract_features()
    train_and_select_model()

    print("\n" + "="*70)
    print("🎉 FULL RETRAINING COMPLETE!")
    print("="*70)
    print("Restart the backend server to load the new model:")
    print("  /opt/anaconda3/envs/tfenv/bin/uvicorn main:app --host 127.0.0.1 --port 8000")
