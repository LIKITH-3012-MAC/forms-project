import json
import numpy as np
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, confusion_matrix,
    classification_report, average_precision_score, brier_score_loss
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from sklearn.metrics import RocCurveDisplay, PrecisionRecallDisplay
import joblib

def load_features(features_dir, split_name):
    X = np.load(str(features_dir / f"X_{split_name}.npy"))
    y = np.load(str(features_dir / f"y_{split_name}.npy"))
    return X, y

def main():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    features_dir = models_dir / "features"
    
    # Load test data
    X_test, y_test = load_features(features_dir, "test")
    
    # Load scaler and classifier
    scaler = joblib.load(str(models_dir / "feature_scaler.pkl"))
    classifier = joblib.load(str(models_dir / "receipt_classifier.pkl"))
    
    X_test_scaled = scaler.transform(X_test)
    
    y_pred = classifier.predict(X_test_scaled)
    y_proba = classifier.predict_proba(X_test_scaled)[:, 1]
    
    # Compute metrics
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
        "precision_receipt": float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "recall_receipt": float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "f1_receipt": float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "precision_not_receipt": float(precision_score(y_test, y_pred, pos_label=0, zero_division=0)),
        "recall_not_receipt": float(recall_score(y_test, y_pred, pos_label=0, zero_division=0)),
        "f1_not_receipt": float(f1_score(y_test, y_pred, pos_label=0, zero_division=0)),
        "brier_score": float(brier_score_loss(y_test, y_proba)),
    }
    
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))
    except ValueError:
        metrics["roc_auc"] = None
        
    try:
        metrics["pr_auc"] = float(average_precision_score(y_test, y_proba))
    except ValueError:
        metrics["pr_auc"] = None
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    fp = int(cm[0][1]) if cm.shape[0] > 1 else 0
    tn = int(cm[0][0]) if cm.shape[0] > 1 else 0
    fn = int(cm[1][0]) if cm.shape[0] > 1 else 0
    tp = int(cm[1][1]) if cm.shape[0] > 1 else 0
    
    metrics["false_positive_rate"] = float(fp / max(fp + tn, 1))
    metrics["false_negative_rate"] = float(fn / max(fn + tp, 1))
    metrics["confusion_matrix"] = {"TP": tp, "TN": tn, "FP": fp, "FN": fn}
    
    print("=" * 60)
    print("FINAL MODEL EVALUATION ON TEST SET")
    print("=" * 60)
    for k, v in metrics.items():
        if k != "confusion_matrix":
            print(f"  {k}: {v}")
    print(f"\n  Confusion Matrix:")
    print(f"    TP={tp} FP={fp}")
    print(f"    FN={fn} TN={tn}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['not_receipt', 'receipt'])}")
    
    # Save metrics
    with open(models_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    # Plot confusion matrix
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=[0, 1], yticks=[0, 1],
           xticklabels=['not_receipt', 'receipt'],
           yticklabels=['not_receipt', 'receipt'],
           ylabel='True label', xlabel='Predicted label',
           title='Confusion Matrix')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=16)
    fig.tight_layout()
    fig.savefig(str(models_dir / "confusion_matrix.png"), dpi=150)
    plt.close(fig)
    print("✓ Saved confusion_matrix.png")
    
    # ROC curve
    try:
        fig, ax = plt.subplots(figsize=(6, 5))
        RocCurveDisplay.from_predictions(y_test, y_proba, ax=ax, name="Receipt Classifier")
        ax.set_title("ROC Curve")
        fig.tight_layout()
        fig.savefig(str(models_dir / "roc_curve.png"), dpi=150)
        plt.close(fig)
        print("✓ Saved roc_curve.png")
    except Exception as e:
        print(f"  Could not generate ROC curve: {e}")
    
    # Calibration curve
    try:
        fig, ax = plt.subplots(figsize=(6, 5))
        prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=10)
        ax.plot(prob_pred, prob_true, marker='o', label="Calibrated model")
        ax.plot([0, 1], [0, 1], '--', color='gray', label="Perfectly calibrated")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Fraction of positives")
        ax.set_title("Calibration Curve")
        ax.legend()
        fig.tight_layout()
        fig.savefig(str(models_dir / "calibration_curve.png"), dpi=150)
        plt.close(fig)
        print("✓ Saved calibration_curve.png")
    except Exception as e:
        print(f"  Could not generate calibration curve: {e}")
    
    # Warning
    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT DISCLAIMER")
    print("=" * 60)
    print("Current accuracy is NOT reliable for production because the")
    print("positive class is built from only five unique receipt images.")
    print("Add genuinely different receipt screenshots to improve reliability.")
    print("No model can guarantee 100% correctness on unknown uploaded images.")

if __name__ == "__main__":
    main()
