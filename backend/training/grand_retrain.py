"""
GRAND RETRAINING PIPELINE — Maximum Accuracy Edition
=====================================================
1. Rebalance dataset splits (more receipts in val/test)  
2. Fine-tune EfficientNetB0 backbone with heavy augmentation
3. Export improved ONNX feature extractor
4. Extract features with the new backbone
5. Grid-search hyperparameters across 6 classifiers
6. Build a VotingClassifier ensemble
7. Calibrate with isotonic regression
8. Evaluate on held-out test set
"""

import os, sys, json, shutil, random, hashlib, io, warnings
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

warnings.filterwarnings("ignore")

# ─── Config ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "dataset"
MODELS_DIR = BASE_DIR / "backend" / "models"
FEATURES_DIR = MODELS_DIR / "features"
PHOTOS_DIR = Path("/Users/likithnaidu/Desktop/PHOTOS-TRAIN/photos")

TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR   = DATASET_DIR / "val"
TEST_DIR  = DATASET_DIR / "test"

IMG_SIZE = (224, 224)
random.seed(42)
np.random.seed(42)


# ═══════════════════════════════════════════════════════════════════
# STEP 0: Rebalance — move more receipts into val/test
# ═══════════════════════════════════════════════════════════════════

def rebalance_splits():
    """Ensure val and test have enough real receipt images."""
    print("\n" + "=" * 70)
    print("STEP 0: Rebalancing dataset splits")
    print("=" * 70)

    # First, copy ALL receipt originals to a temp staging area
    staging_dir = DATASET_DIR / "_receipt_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    # Collect ALL receipt images across all splits into staging
    count = 0
    seen_hashes = set()
    for split_dir in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
        rdir = split_dir / "receipt"
        if rdir.exists():
            for f in sorted(rdir.iterdir()):
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                    if not f.name.startswith('aug_'):
                        try:
                            img = Image.open(f).convert("RGB").resize((64, 64))
                            h = hashlib.md5(np.array(img).tobytes()).hexdigest()
                            if h not in seen_hashes:
                                seen_hashes.add(h)
                                dest = staging_dir / f"{count:04d}_{f.name}"
                                shutil.copy2(f, dest)
                                count += 1
                        except Exception:
                            pass

    staged_files = sorted(staging_dir.iterdir())
    print(f"Unique receipt images staged: {len(staged_files)}")

    if len(staged_files) < 10:
        print("Not enough receipt images to rebalance. Skipping.")
        shutil.rmtree(staging_dir)
        return

    # Target split: 60% train, 20% val, 20% test
    random.shuffle(staged_files)
    n = len(staged_files)
    n_train = max(1, int(n * 0.60))
    n_val = max(3, int(n * 0.20))
    n_test = n - n_train - n_val
    if n_test < 3:
        n_train -= (3 - n_test)
        n_test = 3

    train_set = staged_files[:n_train]
    val_set = staged_files[n_train:n_train + n_val]
    test_set = staged_files[n_train + n_val:]

    print(f"  New split: train={len(train_set)}, val={len(val_set)}, test={len(test_set)}")

    # Now clear existing receipt dirs and redistribute from staging
    for split_name, split_dir, images in [
        ("train", TRAIN_DIR, train_set),
        ("val", VAL_DIR, val_set),
        ("test", TEST_DIR, test_set),
    ]:
        rdir = split_dir / "receipt"
        # Remove all existing receipt images (originals + augmented)
        if rdir.exists():
            for f in rdir.iterdir():
                f.unlink()
        rdir.mkdir(parents=True, exist_ok=True)

        for img_path in images:
            dest = rdir / img_path.name
            shutil.copy2(img_path, dest)

        print(f"  {split_name}/receipt: {len(images)} images")

    # Cleanup staging
    shutil.rmtree(staging_dir)
    print("✓ Splits rebalanced.")


# ═══════════════════════════════════════════════════════════════════
# STEP 1: Generate MORE diverse negatives
# ═══════════════════════════════════════════════════════════════════

def _gen_gradient(sz=(224,224)):
    img = np.zeros((sz[1],sz[0],3), dtype=np.uint8)
    c1, c2 = np.random.randint(0,255,3), np.random.randint(0,255,3)
    for y in range(sz[1]):
        r = y / sz[1]
        img[y,:] = (c1*(1-r) + c2*r).astype(np.uint8)
    return Image.fromarray(img)

def _gen_noise(sz=(224,224)):
    return Image.fromarray(np.random.randint(0,255,(sz[1],sz[0],3),dtype=np.uint8))

def _gen_solid(sz=(224,224)):
    return Image.new("RGB", sz, tuple(np.random.randint(0,255,3).tolist()))

def _gen_text_screen(sz=(224,224)):
    bg = random.choice([(255,255,255),(240,240,240),(30,30,30),(245,245,220)])
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    tc = (0,0,0) if bg[0]>128 else (255,255,255)
    y = 10
    while y < sz[1]-20:
        d.rectangle([10, y, 10+random.randint(80, sz[0]-20), y+8], fill=tc)
        y += random.randint(14, 25)
    return img

def _gen_selfie(sz=(224,224)):
    bg = random.choice([(200,220,255),(180,255,200),(255,230,200),(60,60,80)])
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    skin = random.choice([(255,224,189),(241,194,125),(198,134,66),(141,85,36)])
    cx, cy = sz[0]//2, sz[1]//2-20
    rw, rh = random.randint(40,70), random.randint(50,80)
    d.ellipse([cx-rw,cy-rh,cx+rw,cy+rh], fill=skin)
    d.ellipse([cx-rw-5,cy-rh-15,cx+rw+5,cy-rh+20], fill=random.choice([(30,20,10),(60,40,20)]))
    d.ellipse([cx-20,cy-10,cx-10,cy], fill=(255,255,255))
    d.ellipse([cx+10,cy-10,cx+20,cy], fill=(255,255,255))
    return img

def _gen_nature(sz=(224,224)):
    img = Image.new("RGB", sz, (135,206,235))
    d = ImageDraw.Draw(img)
    h_line = random.randint(sz[1]//3, 2*sz[1]//3)
    d.rectangle([0,h_line,sz[0],sz[1]], fill=random.choice([(34,139,34),(0,128,0),(85,107,47)]))
    sx, sy = random.randint(20,sz[0]-20), random.randint(10,h_line-20)
    sr = random.randint(15,30)
    d.ellipse([sx-sr,sy-sr,sx+sr,sy+sr], fill=(255,255,0))
    return img

def _gen_ui(sz=(224,224)):
    bg = random.choice([(255,255,255),(245,245,245),(18,18,18)])
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,sz[0],30], fill=random.choice([(33,150,243),(76,175,80),(244,67,54)]))
    cc = (200,200,200) if bg[0]>128 else (50,50,50)
    for _ in range(random.randint(2,6)):
        x1 = random.randint(10,sz[0]//2)
        y1 = random.randint(40,sz[1]-60)
        d.rectangle([x1,y1,x1+random.randint(60,sz[0]-x1-10),y1+random.randint(20,50)], fill=cc, outline=(100,100,100))
    return img

def _gen_meme(sz=(224,224)):
    bg = random.choice([(0,0,0),(255,255,255),(255,255,0)])
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    tb = (0,0,0) if bg[0]>128 else (255,255,255)
    d.rectangle([0,0,sz[0],40], fill=tb)
    d.rectangle([0,sz[1]-40,sz[0],sz[1]], fill=tb)
    d.rectangle([10,50,sz[0]-10,sz[1]-50], fill=tuple(np.random.randint(50,200,3).tolist()))
    return img

def _gen_document(sz=(224,224)):
    """Fake document/form — visually similar but NOT a payment receipt."""
    img = Image.new("RGB", sz, (255,255,255))
    d = ImageDraw.Draw(img)
    # Header bar
    d.rectangle([0,0,sz[0],40], fill=(0,51,102))
    # Lines of "text"
    y = 55
    while y < sz[1]-30:
        line_w = random.randint(100, sz[0]-30)
        d.rectangle([15, y, 15+line_w, y+6], fill=(60,60,60))
        y += random.randint(12, 22)
    # Some boxes (form fields)
    for _ in range(random.randint(1,3)):
        bx = random.randint(15, sz[0]//2)
        by = random.randint(60, sz[1]-40)
        d.rectangle([bx, by, bx+random.randint(80,150), by+25], outline=(180,180,180), width=2)
    return img

def _gen_social_post(sz=(224,224)):
    """Fake social media post."""
    bg = random.choice([(255,255,255),(0,0,0),(29,29,29)])
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    # Profile circle
    d.ellipse([10,10,40,40], fill=tuple(np.random.randint(50,200,3).tolist()))
    # Username line
    tc = (0,0,0) if bg[0]>128 else (255,255,255)
    d.rectangle([50,18,160,28], fill=tc)
    # Image area
    img_color = tuple(np.random.randint(30,220,3).tolist())
    d.rectangle([0,55,sz[0],sz[1]-50], fill=img_color)
    # Like bar
    d.rectangle([10,sz[1]-40,80,sz[1]-30], fill=(200,50,50))
    return img

def _gen_game_screen(sz=(224,224)):
    """Fake game screenshot."""
    bg = tuple(np.random.randint(0,50,3).tolist())
    img = Image.new("RGB", sz, bg)
    d = ImageDraw.Draw(img)
    # HUD bar
    d.rectangle([0,0,sz[0],20], fill=(0,0,0))
    d.rectangle([5,5,60,15], fill=(255,0,0))  # health bar
    d.rectangle([70,5,120,15], fill=(0,100,255))  # mana bar
    # Random colored shapes
    for _ in range(random.randint(5,15)):
        x = random.randint(0,sz[0]-20)
        y = random.randint(30,sz[1]-20)
        c = tuple(np.random.randint(0,255,3).tolist())
        shape = random.choice(['rect','circle'])
        if shape == 'rect':
            d.rectangle([x,y,x+random.randint(10,40),y+random.randint(10,40)], fill=c)
        else:
            r = random.randint(5,20)
            d.ellipse([x,y,x+r*2,y+r*2], fill=c)
    return img


def generate_negatives():
    """Generate diverse negative images."""
    print("\n" + "=" * 70)
    print("STEP 1: Generating diverse negative samples")
    print("=" * 70)

    generators = [
        _gen_gradient, _gen_noise, _gen_solid, _gen_text_screen,
        _gen_selfie, _gen_nature, _gen_ui, _gen_meme,
        _gen_document, _gen_social_post, _gen_game_screen,
    ]

    for split_name, count, split_dir in [
        ("train", 600, TRAIN_DIR),
        ("val", 80, VAL_DIR),
        ("test", 80, TEST_DIR),
    ]:
        neg_dir = split_dir / "not_receipt"
        # Remove old synthetics
        if neg_dir.exists():
            for f in neg_dir.iterdir():
                if f.name.startswith("synth_"):
                    f.unlink()

        neg_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            gen = random.choice(generators)
            img = gen()
            if random.random() < 0.3:
                img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 2.0)))
            if random.random() < 0.3:
                img = ImageEnhance.Brightness(img).enhance(random.uniform(0.5, 1.5))
            img.save(neg_dir / f"synth_v2_{i:04d}.jpg", "JPEG", quality=85)

        existing = len([f for f in neg_dir.iterdir() if f.suffix.lower() in ('.jpg','.jpeg','.png','.webp')])
        print(f"  {split_name}: {existing} total negatives")

    print("✓ Negatives generated.")


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Fine-tune EfficientNetB0 backbone with heavy augmentation
# ═══════════════════════════════════════════════════════════════════

def finetune_backbone():
    """Fine-tune EfficientNetB0 with aggressive augmentation."""
    print("\n" + "=" * 70)
    print("STEP 2: Fine-tuning EfficientNetB0 backbone")
    print("=" * 70)

    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')  # Force CPU on M2

    from tensorflow.keras import layers, models, optimizers
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    # Heavy augmentation for training
    train_datagen = ImageDataGenerator(
        rotation_range=20,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.1,
        zoom_range=0.2,
        brightness_range=(0.6, 1.4),
        horizontal_flip=True,
        fill_mode='nearest',
        channel_shift_range=30.0,
    )
    val_datagen = ImageDataGenerator()

    train_gen = train_datagen.flow_from_directory(
        TRAIN_DIR, target_size=IMG_SIZE, batch_size=16,
        class_mode='binary', shuffle=True
    )
    val_gen = val_datagen.flow_from_directory(
        VAL_DIR, target_size=IMG_SIZE, batch_size=16,
        class_mode='binary', shuffle=False
    )

    print(f"Classes: {train_gen.class_indices}")
    print(f"Train samples: {train_gen.samples}, Val samples: {val_gen.samples}")

    # Build model
    base_model = tf.keras.applications.EfficientNetB0(
        input_shape=(224, 224, 3), include_top=False, weights='imagenet'
    )

    inputs = layers.Input(shape=(224, 224, 3))
    x = layers.Lambda(tf.keras.applications.efficientnet.preprocess_input)(inputs)
    x = base_model(x, training=False)
    features = layers.GlobalAveragePooling2D(name="feature_output")(x)
    x = layers.Dropout(0.4)(features)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(1, activation='sigmoid', name="classifier_output")(x)

    model = models.Model(inputs, outputs)

    # ── Phase 1: Train head (backbone frozen) ──
    base_model.trainable = False
    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-3),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    print("\n── Phase 1: Training classifier head (backbone frozen) ──")
    model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=8,
        verbose=1
    )

    # ── Phase 2: Unfreeze top 50 layers and fine-tune ──
    base_model.trainable = True
    for layer in base_model.layers[:-50]:
        layer.trainable = False

    model.compile(
        optimizer=optimizers.Adam(learning_rate=5e-6),  # Very low LR
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=4, verbose=1, min_lr=1e-7),
    ]

    print("\n── Phase 2: Fine-tuning backbone (top 50 layers) ──")
    model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=25,
        callbacks=callbacks,
        verbose=1
    )

    # ── Phase 3: Unfreeze everything, ultra-low LR ──
    base_model.trainable = True
    for layer in base_model.layers:
        layer.trainable = True

    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-6),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    callbacks_p3 = [
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=3, verbose=1, min_lr=1e-8),
    ]

    print("\n── Phase 3: Full fine-tune (all layers, ultra-low LR) ──")
    model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=15,
        callbacks=callbacks_p3,
        verbose=1
    )

    # Save Keras model
    keras_path = MODELS_DIR / "receipt_feature_extractor.keras"
    model.save(str(keras_path))
    print(f"\n✓ Full model saved: {keras_path}")

    # ── Export feature extractor to ONNX ──
    # Build feature-only model (up to GlobalAveragePooling2D)
    feature_model = models.Model(inputs=model.input, outputs=model.get_layer("feature_output").output)

    print("Converting feature extractor to ONNX...")
    import tf2onnx
    onnx_path = MODELS_DIR / "receipt_feature_extractor.onnx"
    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input_1"),)
    
    try:
        tf2onnx.convert.from_keras(
            feature_model,
            input_signature=spec,
            opset=13,
            output_path=str(onnx_path)
        )
        print(f"✓ ONNX feature extractor exported: {onnx_path}")
    except Exception as e:
        print(f"ONNX export error: {e}")
        print("WARNING: ONNX export failed. Using existing ONNX model.")

    return model


# ═══════════════════════════════════════════════════════════════════
# STEP 3: Generate augmented receipt images for classifier training
# ═══════════════════════════════════════════════════════════════════

def augment_image(img):
    """Apply random augmentation."""
    aug = img.copy()

    if random.random() < 0.4:
        aug = aug.rotate(random.uniform(-15, 15), fillcolor=(0,0,0), expand=False)
    if random.random() < 0.5:
        w, h = aug.size
        p = random.uniform(0.05, 0.15)
        l = int(w*p*random.random())
        t = int(h*p*random.random())
        r = w - int(w*p*random.random())
        b = h - int(h*p*random.random())
        aug = aug.crop((l,t,r,b)).resize((w,h), Image.BILINEAR)
    if random.random() < 0.5:
        aug = ImageEnhance.Brightness(aug).enhance(random.uniform(0.5, 1.5))
    if random.random() < 0.4:
        aug = ImageEnhance.Contrast(aug).enhance(random.uniform(0.6, 1.4))
    if random.random() < 0.3:
        aug = ImageEnhance.Color(aug).enhance(random.uniform(0.4, 1.6))
    if random.random() < 0.3:
        aug = ImageEnhance.Sharpness(aug).enhance(random.uniform(0.3, 2.0))
    if random.random() < 0.25:
        aug = aug.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 2.0)))
    if random.random() < 0.3:
        aug = aug.transpose(Image.FLIP_LEFT_RIGHT)
    if random.random() < 0.3:
        arr = np.array(aug, dtype=np.float32)
        arr = np.clip(arr + np.random.normal(0, random.uniform(3, 20), arr.shape), 0, 255).astype(np.uint8)
        aug = Image.fromarray(arr)
    if random.random() < 0.35:
        buf = io.BytesIO()
        aug.save(buf, "JPEG", quality=random.randint(15, 55))
        buf.seek(0)
        aug = Image.open(buf).copy()
    # Perspective-like distortion via slight affine
    if random.random() < 0.2:
        w, h = aug.size
        coeffs = [1 + random.uniform(-0.05, 0.05) for _ in range(6)] + [0, 0]
        aug = aug.transform((w, h), Image.AFFINE, coeffs[:6], resample=Image.BILINEAR)

    return aug


def augment_receipts():
    """Create augmented receipt copies in training set."""
    print("\n" + "=" * 70)
    print("STEP 3: Augmenting training receipts (×12 per image)")
    print("=" * 70)

    rdir = TRAIN_DIR / "receipt"
    originals = [f for f in rdir.iterdir()
                 if f.suffix.lower() in ('.jpg','.jpeg','.png','.webp')
                 and not f.name.startswith('aug_')]

    print(f"Original receipt images in train: {len(originals)}")

    count = 0
    for f in originals:
        try:
            img = Image.open(f).convert("RGB")
            for i in range(12):
                aug = augment_image(img)
                aug.save(rdir / f"aug_{f.stem}_{i:02d}.jpg", "JPEG", quality=90)
                count += 1
        except Exception as e:
            print(f"  Error: {f.name}: {e}")

    total = len(list(rdir.glob("*")))
    print(f"✓ Created {count} augmented images. Total in train/receipt: {total}")


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Extract features with the new ONNX model
# ═══════════════════════════════════════════════════════════════════

def extract_features():
    """Extract fused features via ONNX."""
    print("\n" + "=" * 70)
    print("STEP 4: Extracting fused features via ONNX")
    print("=" * 70)

    import onnxruntime as ort
    import cv2

    onnx_path = MODELS_DIR / "receipt_feature_extractor.onnx"
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp = session.get_inputs()[0]
    out = session.get_outputs()[0]
    print(f"  ONNX loaded. Input: {inp.name} {inp.shape}, Output: {out.name}")

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val", "test"]:
        sdir = DATASET_DIR / split
        if not sdir.exists():
            continue

        print(f"\n  Extracting {split}...")
        all_X, all_y, all_fn = [], [], []

        for cls, lbl in [("not_receipt", 0), ("receipt", 1)]:
            cdir = sdir / cls
            if not cdir.exists():
                continue
            files = sorted([f for f in cdir.iterdir() if f.suffix.lower() in ('.jpg','.jpeg','.png','.webp')])

            n = 0
            for f in files:
                try:
                    img = Image.open(f).convert("RGB")
                    arr = np.array(img.resize(IMG_SIZE, Image.BILINEAR), dtype=np.float32)
                    batch = np.expand_dims(arr, 0)

                    emb = session.run([out.name], {inp.name: batch})[0].flatten()

                    # Quality features
                    orig = np.array(img)
                    gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)
                    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                    bright = float(np.mean(gray))
                    w, h = img.size
                    ar = w / max(h, 1)

                    combined = np.concatenate([emb, np.array([blur, bright, ar, w, h], dtype=np.float32)])
                    all_X.append(combined)
                    all_y.append(lbl)
                    all_fn.append(str(f))
                    n += 1
                except Exception as e:
                    print(f"    Error {f.name}: {e}")

            print(f"    {cls}: {n} samples")

        X = np.array(all_X, dtype=np.float32)
        y = np.array(all_y, dtype=np.int32)
        np.save(str(FEATURES_DIR / f"X_{split}.npy"), X)
        np.save(str(FEATURES_DIR / f"y_{split}.npy"), y)
        with open(FEATURES_DIR / f"filenames_{split}.json", "w") as fp:
            json.dump(all_fn, fp, indent=2)
        print(f"    Saved: X={X.shape}, receipt={np.sum(y==1)}, not_receipt={np.sum(y==0)}")

    print("\n✓ Feature extraction complete.")


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Train with grid search + ensemble + calibration
# ═══════════════════════════════════════════════════════════════════

def train_ensemble():
    """Train multiple classifiers, grid-search, ensemble, calibrate."""
    print("\n" + "=" * 70)
    print("STEP 5: Grid-search + Ensemble Training")
    print("=" * 70)

    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.ensemble import (
        ExtraTreesClassifier, RandomForestClassifier,
        GradientBoostingClassifier, HistGradientBoostingClassifier,
        VotingClassifier
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold, GridSearchCV
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, precision_score,
        recall_score, f1_score, roc_auc_score, brier_score_loss,
        classification_report
    )
    from sklearn.calibration import CalibratedClassifierCV
    import joblib

    X_train = np.load(str(FEATURES_DIR / "X_train.npy"))
    y_train = np.load(str(FEATURES_DIR / "y_train.npy"))
    X_val = np.load(str(FEATURES_DIR / "X_val.npy"))
    y_val = np.load(str(FEATURES_DIR / "y_val.npy"))
    X_test = np.load(str(FEATURES_DIR / "X_test.npy"))
    y_test = np.load(str(FEATURES_DIR / "y_test.npy"))

    print(f"Train: {X_train.shape}, receipt={np.sum(y_train==1)}, neg={np.sum(y_train==0)}")
    print(f"Val:   {X_val.shape}, receipt={np.sum(y_val==1)}, neg={np.sum(y_val==0)}")
    print(f"Test:  {X_test.shape}, receipt={np.sum(y_test==1)}, neg={np.sum(y_test==0)}")

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_v = scaler.transform(X_val)
    X_te = scaler.transform(X_test)

    joblib.dump(scaler, str(MODELS_DIR / "feature_scaler.pkl"))
    print("✓ Scaler saved.")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # ── Grid-search best SVM ──
    print("\n── Grid-searching SVM ──")
    svm_grid = GridSearchCV(
        SVC(kernel="rbf", probability=True, class_weight="balanced"),
        param_grid={"C": [1, 5, 10, 50], "gamma": ["scale", "auto", 0.001, 0.01]},
        cv=skf, scoring="balanced_accuracy", n_jobs=-1, verbose=0
    )
    svm_grid.fit(X_tr, y_train)
    best_svm = svm_grid.best_estimator_
    print(f"  Best SVM: C={svm_grid.best_params_['C']}, gamma={svm_grid.best_params_['gamma']}, "
          f"CV={svm_grid.best_score_:.4f}")

    # ── Grid-search best ExtraTrees ──
    print("\n── Grid-searching ExtraTrees ──")
    et_grid = GridSearchCV(
        ExtraTreesClassifier(class_weight="balanced", n_jobs=-1, random_state=42),
        param_grid={
            "n_estimators": [300, 500, 800],
            "max_depth": [10, 15, 20, None],
            "min_samples_leaf": [1, 2, 3],
        },
        cv=skf, scoring="balanced_accuracy", n_jobs=-1, verbose=0
    )
    et_grid.fit(X_tr, y_train)
    best_et = et_grid.best_estimator_
    print(f"  Best ExtraTrees: {et_grid.best_params_}, CV={et_grid.best_score_:.4f}")

    # ── Grid-search best GradientBoosting ──
    print("\n── Grid-searching GradientBoosting ──")
    gb_grid = GridSearchCV(
        GradientBoostingClassifier(random_state=42, subsample=0.8),
        param_grid={
            "n_estimators": [200, 400],
            "learning_rate": [0.03, 0.05, 0.1],
            "max_depth": [4, 5, 6],
        },
        cv=skf, scoring="balanced_accuracy", n_jobs=-1, verbose=0
    )
    gb_grid.fit(X_tr, y_train)
    best_gb = gb_grid.best_estimator_
    print(f"  Best GB: {gb_grid.best_params_}, CV={gb_grid.best_score_:.4f}")

    # ── Best Logistic Regression ──
    print("\n── Grid-searching LogisticRegression ──")
    lr_grid = GridSearchCV(
        LogisticRegression(class_weight="balanced", max_iter=5000, solver="lbfgs"),
        param_grid={"C": [0.01, 0.1, 0.5, 1.0, 5.0, 10.0]},
        cv=skf, scoring="balanced_accuracy", n_jobs=-1, verbose=0
    )
    lr_grid.fit(X_tr, y_train)
    best_lr = lr_grid.best_estimator_
    print(f"  Best LR: C={lr_grid.best_params_['C']}, CV={lr_grid.best_score_:.4f}")

    # ── Build Voting Ensemble ──
    print("\n── Building VotingClassifier Ensemble ──")
    ensemble = VotingClassifier(
        estimators=[
            ("svm", best_svm),
            ("et", best_et),
            ("gb", best_gb),
            ("lr", best_lr),
        ],
        voting="soft",
        n_jobs=-1
    )
    ensemble.fit(X_tr, y_train)

    # Also train individual best models for comparison
    all_models = {
        "SVM_RBF": best_svm,
        "ExtraTrees": best_et,
        "GradientBoosting": best_gb,
        "LogisticRegression": best_lr,
        "Ensemble_Voting": ensemble,
    }

    # ── Evaluate all on val ──
    print("\n── Validation Results ──")
    results = []
    for name, mdl in all_models.items():
        yp = mdl.predict(X_v)
        ypr = mdl.predict_proba(X_v)[:, 1]
        fp = np.sum((yp == 1) & (y_val == 0))
        tn = np.sum((yp == 0) & (y_val == 0))

        m = {
            "name": name,
            "val_acc": float(accuracy_score(y_val, yp)),
            "val_bal_acc": float(balanced_accuracy_score(y_val, yp)),
            "val_recall": float(recall_score(y_val, yp, pos_label=1, zero_division=0)),
            "val_precision": float(precision_score(y_val, yp, pos_label=1, zero_division=0)),
            "val_f1": float(f1_score(y_val, yp, pos_label=1, zero_division=0)),
            "val_fpr": float(fp / max(fp + tn, 1)),
        }
        try:
            m["val_auc"] = float(roc_auc_score(y_val, ypr))
        except:
            m["val_auc"] = None
        results.append(m)
        print(f"  {name:25s}  Acc={m['val_acc']:.4f}  BalAcc={m['val_bal_acc']:.4f}  "
              f"Recall={m['val_recall']:.4f}  FPR={m['val_fpr']:.4f}")

    # ── Select best model ──
    best_result = max(results, key=lambda r: r["val_recall"] + r["val_bal_acc"] - 3 * r["val_fpr"])
    best_name = best_result["name"]
    best_model = all_models[best_name]
    print(f"\n✓ Selected: {best_name}")

    # ── Calibrate ──
    try:
        from sklearn.calibration import FrozenEstimator
        calibrated = CalibratedClassifierCV(estimator=FrozenEstimator(best_model), method="isotonic")
    except ImportError:
        calibrated = CalibratedClassifierCV(estimator=best_model, cv="prefit", method="isotonic")

    calibrated.fit(X_v, y_val)
    print("✓ Calibrated with isotonic regression.")

    # ── Final test evaluation ──
    yp_test = calibrated.predict(X_te)
    ypr_test = calibrated.predict_proba(X_te)[:, 1]

    print(f"\n{'=' * 60}")
    print(f"FINAL TEST RESULTS — {best_name} + isotonic")
    print(f"{'=' * 60}")
    print(classification_report(y_test, yp_test, target_names=["not_receipt", "receipt"]))

    fp_t = np.sum((yp_test == 1) & (y_test == 0))
    tn_t = np.sum((yp_test == 0) & (y_test == 0))

    test_metrics = {
        "selected_model": best_name,
        "calibration": "isotonic",
        "test_accuracy": float(accuracy_score(y_test, yp_test)),
        "test_balanced_accuracy": float(balanced_accuracy_score(y_test, yp_test)),
        "test_precision_receipt": float(precision_score(y_test, yp_test, pos_label=1, zero_division=0)),
        "test_recall_receipt": float(recall_score(y_test, yp_test, pos_label=1, zero_division=0)),
        "test_f1_receipt": float(f1_score(y_test, yp_test, pos_label=1, zero_division=0)),
        "test_brier_score": float(brier_score_loss(y_test, ypr_test)),
        "test_false_positive_rate": float(fp_t / max(fp_t + tn_t, 1)),
    }
    try:
        test_metrics["test_roc_auc"] = float(roc_auc_score(y_test, ypr_test))
    except:
        test_metrics["test_roc_auc"] = None

    for k, v in test_metrics.items():
        print(f"  {k}: {v}")

    # ── Save everything ──
    joblib.dump(calibrated, str(MODELS_DIR / "receipt_classifier.pkl"))
    print(f"\n✓ Final classifier saved: {MODELS_DIR / 'receipt_classifier.pkl'}")

    with open(MODELS_DIR / "candidate_model_results.json", "w") as f:
        json.dump(results, f, indent=2)

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
    }
    with open(MODELS_DIR / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)
    with open(MODELS_DIR / "training_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    print("✓ All configs and metrics saved.")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  GRAND RETRAINING — Maximum Accuracy Edition             ║")
    print("║  Fine-tune backbone + Grid Search + Ensemble Voting      ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    rebalance_splits()
    generate_negatives()
    finetune_backbone()
    augment_receipts()
    extract_features()
    train_ensemble()

    print("\n" + "=" * 70)
    print("🎉 GRAND RETRAINING COMPLETE!")
    print("=" * 70)
    print("Restart the backend to load the new model.")
