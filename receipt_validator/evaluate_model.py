#!/usr/bin/env python3
"""
evaluate_model.py — Receipt Validator Model Evaluation Script
=============================================================

Loads a trained receipt validation model and evaluates it on test data,
generating comprehensive metrics and visualizations including:

- Confusion matrix heatmap
- Per-class precision, recall, and F1-score
- ROC curve with AUC
- Training history (loss & accuracy curves)
- Full text evaluation report

Usage:
    python evaluate_model.py
    python evaluate_model.py --external
    python evaluate_model.py --model models/receipt_validator_best.keras --test-dir dataset/generated/test
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — safe for headless / CI environments

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

# TensorFlow / Keras imports (heavy — loaded after lightweight ones)
import tensorflow as tf
from tensorflow import keras

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_DIR / "reports"

# Defaults
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "receipt_validator_best.keras"
DEFAULT_TEST_DIR = PROJECT_DIR / "dataset" / "generated" / "test"
EXTERNAL_TEST_DIR = PROJECT_DIR / "dataset" / "external_test"
CLASS_NAMES_PATH = PROJECT_DIR / "models" / "class_names.json"
TRAINING_HISTORY_PATH = PROJECT_DIR / "models" / "training_history.json"
IMAGE_SIZE = (224, 224)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
DISCLAIMER = """
⚠️  IMPORTANT DISCLAIMER:
Current accuracy is not reliable for production because the positive class
is built from only 5 unique receipt images. All augmentations derive from the
same originals. Add diverse, genuine receipt images before trusting these metrics.
"""


# ===================================================================
# Helper functions
# ===================================================================

def load_class_names(path: Path) -> list[str]:
    """Load class names from a JSON file.

    Parameters
    ----------
    path : Path
        Path to the JSON file containing a list of class name strings.

    Returns
    -------
    list[str]
        Ordered list of class names (index corresponds to label index).
    """
    if not path.exists():
        logger.warning("Class names file not found at %s — falling back to directory names.", path)
        return []
    with open(path, "r", encoding="utf-8") as fh:
        names = json.load(fh)
    logger.info("Loaded %d class names from %s", len(names), path)
    return names


def load_training_history(path: Path) -> dict[str, list[float]] | None:
    """Load training history from a JSON file.

    Parameters
    ----------
    path : Path
        Path to the JSON file saved during training.

    Returns
    -------
    dict or None
        Dictionary with keys like ``loss``, ``accuracy``, ``val_loss``,
        ``val_accuracy``, each mapping to a list of per-epoch values.
        Returns ``None`` if the file does not exist.
    """
    if not path.exists():
        logger.warning("Training history file not found at %s — skipping history plot.", path)
        return None
    with open(path, "r", encoding="utf-8") as fh:
        history = json.load(fh)
    logger.info("Loaded training history (%d epochs) from %s", len(next(iter(history.values()))), path)
    return history


def build_test_dataset(
    test_dir: Path,
    image_size: tuple[int, int],
    batch_size: int,
    class_names: list[str] | None = None,
) -> tf.data.Dataset | None:
    """Create a ``tf.data.Dataset`` from the test directory.

    The directory is expected to follow the Keras ``image_dataset_from_directory``
    layout::

        test_dir/
            class_a/
                img1.jpg
                img2.jpg
            class_b/
                ...

    Parameters
    ----------
    test_dir : Path
        Root directory containing class sub-folders.
    image_size : tuple[int, int]
        Target (height, width) for resizing.
    batch_size : int
        Batch size for the dataset.
    class_names : list[str] | None
        If provided, enforces this class ordering.

    Returns
    -------
    tf.data.Dataset or None
        The test dataset, or ``None`` if the directory is empty / missing.
    """
    if not test_dir.exists():
        logger.error("Test directory does not exist: %s", test_dir)
        return None

    # Quick check: are there any image files at all?
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    has_images = any(
        p.suffix.lower() in image_extensions
        for p in test_dir.rglob("*")
        if p.is_file()
    )
    if not has_images:
        logger.error("No image files found in %s — cannot evaluate.", test_dir)
        return None

    kwargs: dict[str, Any] = dict(
        directory=str(test_dir),
        labels="inferred",
        label_mode="int",
        image_size=image_size,
        batch_size=batch_size,
        shuffle=False,
    )
    if class_names:
        kwargs["class_names"] = class_names

    dataset = keras.utils.image_dataset_from_directory(**kwargs)
    logger.info(
        "Loaded test dataset from %s — %d batches, classes: %s",
        test_dir,
        len(dataset),
        dataset.class_names,
    )
    return dataset


# ===================================================================
# Visualization helpers
# ===================================================================

def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
    save_path: Path,
    title: str = "Confusion Matrix",
) -> None:
    """Generate and save a seaborn confusion-matrix heatmap.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth integer labels.
    y_pred : np.ndarray
        Predicted integer labels.
    class_names : list[str]
        Human-readable class names.
    save_path : Path
        Destination file path (PNG).
    title : str
        Plot title.
    """
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        linewidths=0.8,
        linecolor="white",
        square=True,
        cbar_kws={"shrink": 0.75},
        ax=ax,
    )
    ax.set_xlabel("Predicted Label", fontsize=12, labelpad=10)
    ax.set_ylabel("True Label", fontsize=12, labelpad=10)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    logger.info("Confusion matrix saved to %s", save_path)


def plot_roc_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    class_names: list[str],
    save_path: Path,
) -> dict[str, float]:
    """Plot ROC curves (one per class for multi-class, or a single curve for binary).

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth integer labels.
    y_prob : np.ndarray
        Predicted probabilities, shape ``(n_samples, n_classes)``.
    class_names : list[str]
        Human-readable class names.
    save_path : Path
        Destination file path (PNG).

    Returns
    -------
    dict[str, float]
        Per-class AUC values keyed by class name.
    """
    n_classes = len(class_names)
    fig, ax = plt.subplots(figsize=(8, 6))
    auc_scores: dict[str, float] = {}

    if n_classes == 2:
        # Binary classification — use positive-class probability
        fpr, tpr, _ = roc_curve(y_true, y_prob[:, 1])
        auc_val = roc_auc_score(y_true, y_prob[:, 1])
        auc_scores[class_names[1]] = float(auc_val)
        ax.plot(fpr, tpr, lw=2, label=f"{class_names[1]} (AUC = {auc_val:.4f})")
    else:
        # One-vs-rest for each class
        y_true_bin = np.eye(n_classes)[y_true]
        for idx, name in enumerate(class_names):
            fpr, tpr, _ = roc_curve(y_true_bin[:, idx], y_prob[:, idx])
            auc_val = roc_auc_score(y_true_bin[:, idx], y_prob[:, idx])
            auc_scores[name] = float(auc_val)
            ax.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {auc_val:.4f})")

    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Random baseline")
    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title("ROC Curve", fontsize=14, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    logger.info("ROC curve saved to %s", save_path)
    return auc_scores


def plot_training_history(history: dict[str, list[float]], save_path: Path) -> None:
    """Plot training & validation loss and accuracy curves.

    Parameters
    ----------
    history : dict
        Training history dictionary with keys such as ``loss``, ``accuracy``,
        ``val_loss``, ``val_accuracy``.
    save_path : Path
        Destination file path (PNG).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # --- Loss subplot ---
    ax = axes[0]
    if "loss" in history:
        epochs = range(1, len(history["loss"]) + 1)
        ax.plot(epochs, history["loss"], "o-", markersize=3, label="Train Loss")
    if "val_loss" in history:
        epochs = range(1, len(history["val_loss"]) + 1)
        ax.plot(epochs, history["val_loss"], "s-", markersize=3, label="Val Loss")
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Loss", fontsize=12)
    ax.set_title("Loss over Epochs", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # --- Accuracy subplot ---
    ax = axes[1]
    if "accuracy" in history:
        epochs = range(1, len(history["accuracy"]) + 1)
        ax.plot(epochs, history["accuracy"], "o-", markersize=3, label="Train Accuracy")
    if "val_accuracy" in history:
        epochs = range(1, len(history["val_accuracy"]) + 1)
        ax.plot(epochs, history["val_accuracy"], "s-", markersize=3, label="Val Accuracy")
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Accuracy", fontsize=12)
    ax.set_title("Accuracy over Epochs", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0.0, 1.05])

    plt.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    logger.info("Training history plot saved to %s", save_path)


# ===================================================================
# Core evaluation
# ===================================================================

def evaluate(
    model: keras.Model,
    dataset: tf.data.Dataset,
    class_names: list[str],
    dataset_label: str = "test",
) -> dict[str, Any]:
    """Run model evaluation and produce all metrics / plots.

    Parameters
    ----------
    model : keras.Model
        The trained Keras model.
    dataset : tf.data.Dataset
        Test dataset yielding ``(images, labels)`` batches.
    class_names : list[str]
        Ordered class names.
    dataset_label : str
        A human-readable label for this evaluation run (used in file names
        and report headers).

    Returns
    -------
    dict[str, Any]
        Dictionary containing ``accuracy``, ``loss``, ``classification_report``,
        ``auc_scores``, and ``num_samples``.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Built-in Keras evaluation (loss + compiled metrics) ---
    logger.info("Running model.evaluate on '%s' set …", dataset_label)
    loss, accuracy = model.evaluate(dataset, verbose=1)
    logger.info("Loss: %.4f | Accuracy: %.4f", loss, accuracy)

    # --- Collect predictions ---
    y_true_list: list[int] = []
    y_prob_list: list[np.ndarray] = []

    for images, labels in dataset:
        preds = model.predict(images, verbose=0)
        y_prob_list.append(preds)
        y_true_list.extend(labels.numpy().tolist())

    y_true = np.array(y_true_list, dtype=int)
    y_prob = np.concatenate(y_prob_list, axis=0)
    y_pred = np.argmax(y_prob, axis=1)

    num_samples = len(y_true)
    logger.info("Total samples evaluated: %d", num_samples)

    # --- Classification report ---
    cls_report_str = classification_report(
        y_true, y_pred, target_names=class_names, digits=4,
    )
    print(f"\n{'=' * 60}")
    print(f"  Classification Report — {dataset_label}")
    print(f"{'=' * 60}")
    print(cls_report_str)

    # --- Confusion matrix ---
    cm_path = REPORTS_DIR / f"confusion_matrix{'_' + dataset_label if dataset_label != 'test' else ''}.png"
    plot_confusion_matrix(
        y_true, y_pred, class_names, cm_path,
        title=f"Confusion Matrix — {dataset_label}",
    )

    # --- ROC curve ---
    roc_path = REPORTS_DIR / f"roc_curve{'_' + dataset_label if dataset_label != 'test' else ''}.png"
    try:
        auc_scores = plot_roc_curve(y_true, y_prob, class_names, roc_path)
    except ValueError as exc:
        logger.warning("Could not compute ROC/AUC: %s", exc)
        auc_scores = {}

    return {
        "accuracy": float(accuracy),
        "loss": float(loss),
        "classification_report": cls_report_str,
        "auc_scores": auc_scores,
        "num_samples": num_samples,
    }


def save_text_report(
    results: dict[str, Any],
    class_names: list[str],
    args: argparse.Namespace,
    save_path: Path,
) -> None:
    """Write a comprehensive plain-text evaluation report.

    Parameters
    ----------
    results : dict
        Output from :func:`evaluate`.
    class_names : list[str]
        Ordered class names.
    args : argparse.Namespace
        Parsed CLI arguments (for recording run configuration).
    save_path : Path
        Destination file path.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "=" * 70,
        "  Receipt Validator — Evaluation Report",
        f"  Generated: {timestamp}",
        "=" * 70,
        "",
        "Configuration",
        "-" * 40,
        f"  Model path  : {args.model}",
        f"  Test dir    : {args.test_dir}",
        f"  External    : {args.external}",
        f"  Batch size  : {args.batch_size}",
        f"  Image size  : {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]}",
        f"  Classes     : {', '.join(class_names)}",
        "",
        "Overall Metrics",
        "-" * 40,
        f"  Loss        : {results['loss']:.6f}",
        f"  Accuracy    : {results['accuracy']:.6f}  ({results['accuracy'] * 100:.2f}%)",
        f"  Samples     : {results['num_samples']}",
        "",
    ]

    if results["auc_scores"]:
        lines.append("AUC Scores (per class)")
        lines.append("-" * 40)
        for name, auc in results["auc_scores"].items():
            lines.append(f"  {name:<20s}: {auc:.6f}")
        lines.append("")

    lines.append("Classification Report")
    lines.append("-" * 40)
    lines.append(results["classification_report"])
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    logger.info("Text report saved to %s", save_path)


# ===================================================================
# CLI
# ===================================================================

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv : list[str] | None
        Argument list (defaults to ``sys.argv[1:]``).

    Returns
    -------
    argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Evaluate the receipt validation model on test data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=DISCLAIMER,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_MODEL_PATH),
        help="Path to the trained Keras model (default: %(default)s).",
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        default=str(DEFAULT_TEST_DIR),
        help="Path to the test dataset directory (default: %(default)s).",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        default=False,
        help="Also evaluate on the external test set at dataset/external_test/.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for evaluation (default: %(default)s).",
    )
    return parser.parse_args(argv)


# ===================================================================
# Main
# ===================================================================

def main(argv: list[str] | None = None) -> None:
    """Entry point for the evaluation script."""
    args = parse_args(argv)
    logger.info("Starting evaluation …")

    # --- Load class names ------------------------------------------------
    class_names = load_class_names(CLASS_NAMES_PATH)

    # --- Load model ------------------------------------------------------
    model_path = Path(args.model)
    if not model_path.exists():
        logger.error("Model file not found: %s", model_path)
        sys.exit(1)

    logger.info("Loading model from %s …", model_path)
    model = keras.models.load_model(str(model_path))
    model.summary(print_fn=logger.info)

    # --- Build primary test dataset --------------------------------------
    test_dir = Path(args.test_dir)
    dataset = build_test_dataset(
        test_dir, IMAGE_SIZE, args.batch_size, class_names or None,
    )
    if dataset is None:
        logger.error("Cannot proceed without a valid test dataset. Exiting.")
        sys.exit(1)

    # Sync class names from dataset if not loaded from file
    if not class_names:
        class_names = dataset.class_names
        logger.info("Using class names from dataset: %s", class_names)

    # --- Evaluate on primary test set ------------------------------------
    results = evaluate(model, dataset, class_names, dataset_label="test")

    # --- Training history plot -------------------------------------------
    history = load_training_history(TRAINING_HISTORY_PATH)
    if history is not None:
        plot_training_history(history, REPORTS_DIR / "training_history.png")

    # --- Save text report ------------------------------------------------
    report_path = REPORTS_DIR / "evaluation_report.txt"
    save_text_report(results, class_names, args, report_path)

    # --- Optional: external test set -------------------------------------
    if args.external:
        logger.info("Evaluating on external test set at %s …", EXTERNAL_TEST_DIR)
        ext_dataset = build_test_dataset(
            EXTERNAL_TEST_DIR, IMAGE_SIZE, args.batch_size, class_names,
        )
        if ext_dataset is not None:
            ext_results = evaluate(
                model, ext_dataset, class_names, dataset_label="external",
            )
            ext_report_path = REPORTS_DIR / "evaluation_report_external.txt"
            save_text_report(ext_results, class_names, args, ext_report_path)
        else:
            logger.warning("External test directory is empty or missing — skipped.")

    # --- Disclaimer ------------------------------------------------------
    print(DISCLAIMER)
    logger.info("Evaluation complete. Reports saved to %s", REPORTS_DIR)


if __name__ == "__main__":
    main()
