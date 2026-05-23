#!/usr/bin/env python3
"""Receipt Validator — Model Training Script.

Trains an EfficientNetB0-based binary classifier to distinguish receipt images
from non-receipt images using a two-phase transfer-learning strategy:

    Phase 1 (Classifier Head):
        Freeze the EfficientNetB0 base (ImageNet weights) and train only the
        custom classification head for a configurable number of epochs.

    Phase 2 (Fine-Tuning):
        Unfreeze the top 20 layers of the base model and continue training at
        a much lower learning rate to adapt high-level features.

Usage:
    python train_model.py
    python train_model.py --epochs 30 --batch-size 16 --phase1-epochs 15

Outputs:
    models/receipt_validator_best.keras   — Best model checkpoint
    models/class_names.json              — Label-index mapping
    models/training_history.json         — Full training history
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
TRAIN_DIR = PROJECT_DIR / "dataset" / "generated" / "train"
VAL_DIR = PROJECT_DIR / "dataset" / "generated" / "val"
MODEL_DIR = PROJECT_DIR / "models"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "\n⚠️  DISCLAIMER: Current accuracy is not reliable for production because "
    "the positive class is built from only 5 unique receipt images.\n"
)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for training configuration."""
    parser = argparse.ArgumentParser(
        description="Train the EfficientNetB0-based receipt validator.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Total number of fine-tuning epochs (Phase 2).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Training and validation batch size.",
    )
    parser.add_argument(
        "--img-size",
        type=int,
        default=224,
        help="Input image size (height and width).",
    )
    parser.add_argument(
        "--phase1-epochs",
        type=int,
        default=10,
        help="Number of epochs for Phase 1 (frozen base).",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="Learning rate for Phase 1 (classifier head).",
    )
    parser.add_argument(
        "--fine-tune-lr",
        type=float,
        default=1e-5,
        help="Learning rate for Phase 2 (fine-tuning upper layers).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Dataset utilities
# ---------------------------------------------------------------------------
def validate_dataset_directories() -> list[str]:
    """Ensure both training and validation directories exist and contain data.

    Returns:
        A sorted list of class (subdirectory) names found in the training set.

    Raises:
        SystemExit: If directories are missing or any class has zero images.
    """
    for label, dir_path in [("Training", TRAIN_DIR), ("Validation", VAL_DIR)]:
        if not dir_path.is_dir():
            print(f"❌  {label} directory not found: {dir_path}")
            sys.exit(1)

    class_names = sorted(
        d.name for d in TRAIN_DIR.iterdir() if d.is_dir()
    )

    if len(class_names) < 2:
        print(
            f"❌  Expected at least 2 class subdirectories in {TRAIN_DIR}, "
            f"found {len(class_names)}: {class_names}"
        )
        sys.exit(1)

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    for class_name in class_names:
        train_class_dir = TRAIN_DIR / class_name
        image_count = sum(
            1
            for f in train_class_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        )
        if image_count == 0:
            print(
                f"❌  Class '{class_name}' in {train_class_dir} has no images. "
                "Cannot train with an empty class."
            )
            sys.exit(1)

    return class_names


def print_class_distribution(dataset_dir: Path, label: str) -> dict[str, int]:
    """Print the number of images per class in *dataset_dir*.

    Args:
        dataset_dir: Root directory containing one subdirectory per class.
        label: Human-readable label for the dataset split (e.g. "Training").

    Returns:
        Mapping from class name to image count.
    """
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    distribution: dict[str, int] = {}

    for class_dir in sorted(dataset_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        count = sum(
            1
            for f in class_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        )
        distribution[class_dir.name] = count

    print(f"\n📊  {label} class distribution:")
    total = 0
    for cls, count in distribution.items():
        print(f"    {cls}: {count} images")
        total += count
    print(f"    {'─' * 30}")
    print(f"    Total: {total} images\n")

    return distribution


def load_datasets(
    img_size: int,
    batch_size: int,
) -> tuple[tf.data.Dataset, tf.data.Dataset, list[str]]:
    """Load training and validation datasets using ``image_dataset_from_directory``.

    Applies ``cache()`` and ``prefetch()`` for optimal I/O performance.

    Args:
        img_size: Target height and width for all images.
        batch_size: Number of samples per batch.

    Returns:
        A tuple of (train_dataset, val_dataset, class_names).
    """
    train_ds = tf.keras.utils.image_dataset_from_directory(
        str(TRAIN_DIR),
        image_size=(img_size, img_size),
        batch_size=batch_size,
        label_mode="binary",
        shuffle=True,
        seed=42,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        str(VAL_DIR),
        image_size=(img_size, img_size),
        batch_size=batch_size,
        label_mode="binary",
        shuffle=False,
    )

    class_names = train_ds.class_names

    # Performance optimisation
    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().prefetch(buffer_size=autotune)
    val_ds = val_ds.cache().prefetch(buffer_size=autotune)

    return train_ds, val_ds, class_names


# ---------------------------------------------------------------------------
# Class weights
# ---------------------------------------------------------------------------
def compute_class_weights(train_ds: tf.data.Dataset) -> dict[int, float]:
    """Compute class weights to handle class imbalance.

    Iterates over the training dataset once to collect all labels, then
    delegates to ``sklearn.utils.class_weight.compute_class_weight``.

    Args:
        train_ds: The training ``tf.data.Dataset`` with binary labels.

    Returns:
        Dictionary mapping class index → weight.
    """
    all_labels: list[int] = []
    for _, labels in train_ds.unbatch():
        all_labels.append(int(labels.numpy()))

    labels_array = np.array(all_labels)
    unique_classes = np.unique(labels_array)

    weights = compute_class_weight(
        class_weight="balanced",
        classes=unique_classes,
        y=labels_array,
    )
    class_weights = {int(cls): float(w) for cls, w in zip(unique_classes, weights)}

    print(f"⚖️   Class weights: {class_weights}")
    return class_weights


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------
def build_model(img_size: int) -> tf.keras.Model:
    """Build an EfficientNetB0-based binary classifier.

    Architecture::

        Input (img_size × img_size × 3)
          → EfficientNetB0 (ImageNet, frozen)
          → GlobalAveragePooling2D
          → Dropout(0.3)
          → Dense(128, ReLU)
          → Dropout(0.2)
          → Dense(1, sigmoid)

    Args:
        img_size: Spatial dimension for input images.

    Returns:
        A compiled-ready ``tf.keras.Model`` (not yet compiled).
    """
    base_model = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(img_size, img_size, 3),
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(img_size, img_size, 3))
    x = base_model(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs, outputs)
    return model


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def get_callbacks(checkpoint_path: str) -> list[tf.keras.callbacks.Callback]:
    """Create the standard set of training callbacks.

    Args:
        checkpoint_path: File path for ``ModelCheckpoint``.

    Returns:
        List containing EarlyStopping, ReduceLROnPlateau, and ModelCheckpoint.
    """
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=7,
        restore_best_weights=True,
        verbose=1,
    )
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=3,
        verbose=1,
    )
    model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        verbose=1,
    )
    return [early_stopping, reduce_lr, model_checkpoint]


# ---------------------------------------------------------------------------
# Training phases
# ---------------------------------------------------------------------------
def train_phase1(
    model: tf.keras.Model,
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    class_weights: dict[int, float],
    callbacks: list[tf.keras.callbacks.Callback],
    learning_rate: float,
    epochs: int,
) -> tf.keras.callbacks.History:
    """Phase 1 — Train only the classifier head with the base frozen.

    Args:
        model: The EfficientNetB0 model (base frozen).
        train_ds: Training dataset.
        val_ds: Validation dataset.
        class_weights: Computed class weights.
        callbacks: List of Keras callbacks.
        learning_rate: Learning rate for the Adam optimiser.
        epochs: Number of epochs to train.

    Returns:
        Keras ``History`` object.
    """
    print("\n" + "=" * 70)
    print("🚀  PHASE 1 — Training classifier head (base frozen)")
    print("=" * 70)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1,
    )
    return history


def train_phase2(
    model: tf.keras.Model,
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    class_weights: dict[int, float],
    callbacks: list[tf.keras.callbacks.Callback],
    fine_tune_lr: float,
    epochs: int,
    initial_epoch: int,
) -> tf.keras.callbacks.History:
    """Phase 2 — Fine-tune the top 20 layers of the base model.

    Args:
        model: The model after Phase 1 training.
        train_ds: Training dataset.
        val_ds: Validation dataset.
        class_weights: Computed class weights.
        callbacks: List of Keras callbacks.
        fine_tune_lr: Learning rate for fine-tuning.
        epochs: Total epoch count (Phase 1 + Phase 2).
        initial_epoch: Starting epoch (= number of Phase 1 epochs completed).

    Returns:
        Keras ``History`` object.
    """
    print("\n" + "=" * 70)
    print("🔧  PHASE 2 — Fine-tuning top 20 layers of the base model")
    print("=" * 70)

    # Locate the EfficientNetB0 base model inside the functional model.
    base_model = None
    for layer in model.layers:
        if isinstance(layer, tf.keras.Model):
            base_model = layer
            break

    if base_model is None:
        print("❌  Could not locate the base model layer for fine-tuning.")
        sys.exit(1)

    # Unfreeze the top 20 layers.
    base_model.trainable = True
    num_layers = len(base_model.layers)
    for layer in base_model.layers[: num_layers - 20]:
        layer.trainable = False

    trainable_count = sum(1 for l in base_model.layers if l.trainable)
    print(
        f"    Base model layers: {num_layers} total, "
        f"{trainable_count} trainable (top 20 unfrozen)"
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=fine_tune_lr),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        initial_epoch=initial_epoch,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1,
    )
    return history


# ---------------------------------------------------------------------------
# Saving utilities
# ---------------------------------------------------------------------------
def merge_histories(
    h1: tf.keras.callbacks.History,
    h2: tf.keras.callbacks.History,
) -> dict[str, list[float]]:
    """Merge two Keras History objects into a single dictionary.

    Args:
        h1: History from Phase 1.
        h2: History from Phase 2.

    Returns:
        Combined history dictionary with all metric lists concatenated.
    """
    combined: dict[str, list[float]] = {}
    for key in h1.history:
        combined[key] = h1.history[key] + h2.history.get(key, [])
    # Include any keys unique to h2.
    for key in h2.history:
        if key not in combined:
            combined[key] = h2.history[key]
    return combined


def save_outputs(
    class_names: list[str],
    history: dict[str, list[float]],
) -> None:
    """Persist class-name mapping and training history to JSON files.

    Args:
        class_names: Ordered list of class names (index = label).
        history: Combined training history dictionary.
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Class names
    class_names_path = MODEL_DIR / "class_names.json"
    class_map = {str(i): name for i, name in enumerate(class_names)}
    with open(class_names_path, "w", encoding="utf-8") as f:
        json.dump(class_map, f, indent=2)
    print(f"💾  Class names saved to {class_names_path}")

    # Training history (convert numpy types to native Python for JSON)
    history_path = MODEL_DIR / "training_history.json"
    serialisable_history = {
        k: [float(v) for v in vals] for k, vals in history.items()
    }
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(serialisable_history, f, indent=2)
    print(f"💾  Training history saved to {history_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point — orchestrates the full two-phase training pipeline."""
    args = parse_args()

    print(DISCLAIMER)
    print("=" * 70)
    print("  Receipt Validator — EfficientNetB0 Training Pipeline")
    print("=" * 70)
    print(f"  TensorFlow version : {tf.__version__}")
    print(f"  GPU available      : {len(tf.config.list_physical_devices('GPU')) > 0}")
    print(f"  Image size         : {args.img_size}×{args.img_size}")
    print(f"  Batch size         : {args.batch_size}")
    print(f"  Phase 1 epochs     : {args.phase1_epochs}")
    print(f"  Phase 2 epochs     : {args.epochs}")
    print(f"  Phase 1 LR         : {args.learning_rate}")
    print(f"  Phase 2 LR (fine)  : {args.fine_tune_lr}")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Validate directories & print distributions
    # ------------------------------------------------------------------
    class_names = validate_dataset_directories()
    print(f"\n✅  Detected classes: {class_names}")

    print_class_distribution(TRAIN_DIR, "Training")
    print_class_distribution(VAL_DIR, "Validation")

    # ------------------------------------------------------------------
    # 2. Load datasets
    # ------------------------------------------------------------------
    print("📂  Loading datasets …")
    train_ds, val_ds, class_names = load_datasets(
        img_size=args.img_size,
        batch_size=args.batch_size,
    )

    # ------------------------------------------------------------------
    # 3. Compute class weights
    # ------------------------------------------------------------------
    print("\n⚖️   Computing class weights …")
    class_weights = compute_class_weights(train_ds)

    # ------------------------------------------------------------------
    # 4. Build model
    # ------------------------------------------------------------------
    print("\n🏗️   Building EfficientNetB0 model …")
    model = build_model(img_size=args.img_size)
    model.summary()

    # ------------------------------------------------------------------
    # 5. Prepare outputs directory & callbacks
    # ------------------------------------------------------------------
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = str(MODEL_DIR / "receipt_validator_best.keras")
    callbacks = get_callbacks(checkpoint_path)

    # ------------------------------------------------------------------
    # 6. Phase 1 — classifier head
    # ------------------------------------------------------------------
    history_p1 = train_phase1(
        model=model,
        train_ds=train_ds,
        val_ds=val_ds,
        class_weights=class_weights,
        callbacks=callbacks,
        learning_rate=args.learning_rate,
        epochs=args.phase1_epochs,
    )

    # ------------------------------------------------------------------
    # 7. Phase 2 — fine-tune upper layers
    # ------------------------------------------------------------------
    total_epochs = args.phase1_epochs + args.epochs
    history_p2 = train_phase2(
        model=model,
        train_ds=train_ds,
        val_ds=val_ds,
        class_weights=class_weights,
        callbacks=callbacks,
        fine_tune_lr=args.fine_tune_lr,
        epochs=total_epochs,
        initial_epoch=args.phase1_epochs,
    )

    # ------------------------------------------------------------------
    # 8. Save outputs
    # ------------------------------------------------------------------
    combined_history = merge_histories(history_p1, history_p2)
    save_outputs(class_names=class_names, history=combined_history)

    # ------------------------------------------------------------------
    # 9. Final summary
    # ------------------------------------------------------------------
    best_val_loss = min(combined_history.get("val_loss", [float("inf")]))
    best_val_acc = max(combined_history.get("val_accuracy", [0.0]))

    print("\n" + "=" * 70)
    print("  ✅  Training Complete!")
    print("=" * 70)
    print(f"  Best val_loss     : {best_val_loss:.4f}")
    print(f"  Best val_accuracy : {best_val_acc:.4f}")
    print(f"  Model saved to    : {checkpoint_path}")
    print("=" * 70)
    print(DISCLAIMER)


if __name__ == "__main__":
    main()
