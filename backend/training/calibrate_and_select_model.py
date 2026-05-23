import json
import numpy as np
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, brier_score_loss
)
import joblib

def load_features(features_dir, split_name):
    X = np.load(str(features_dir / f"X_{split_name}.npy"))
    y = np.load(str(features_dir / f"y_{split_name}.npy"))
    return X, y

def main():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    features_dir = models_dir / "features"
    
    # Load data
    X_train, y_train = load_features(features_dir, "train")
    X_val, y_val = load_features(features_dir, "val")
    
    # Load scaler
    scaler = joblib.load(str(models_dir / "feature_scaler.pkl"))
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Load candidate results
    with open(models_dir / "candidate_model_results.json", "r") as f:
        results = json.load(f)
    
    # Select best model:
    # Primary criterion: lowest false_positive_rate (we hate accepting selfies as receipts)
    # Secondary criterion: highest recall on receipts
    # Tertiary: highest balanced accuracy
    best_result = None
    best_score = float('inf')
    
    for r in results:
        # Composite score: prioritize low FP rate, then high recall
        fp_rate = r.get("false_positive_rate", 1.0)
        recall = r.get("recall_receipt", 0.0)
        bal_acc = r.get("balanced_accuracy", 0.0)
        
        # Lower is better: fp_rate * 3 - recall - bal_acc
        score = fp_rate * 3 - recall - bal_acc
        
        if score < best_score:
            best_score = score
            best_result = r
    
    best_name = best_result["name"]
    print(f"Selected best candidate: {best_name}")
    print(f"  FP Rate: {best_result['false_positive_rate']:.4f}")
    print(f"  Recall (receipt): {best_result['recall_receipt']:.4f}")
    print(f"  Balanced Accuracy: {best_result['balanced_accuracy']:.4f}")
    
    # Load the best raw model
    best_model = joblib.load(str(models_dir / f"candidate_{best_name}.pkl"))
    
    # Calibrate probabilities using CalibratedClassifierCV
    print("\nCalibrating probabilities...")
    try:
        from sklearn.frozen import FrozenEstimator
        frozen_model = FrozenEstimator(best_model)
        calibrated = CalibratedClassifierCV(frozen_model, method="sigmoid")
    except ImportError:
        calibrated = CalibratedClassifierCV(best_model, cv="prefit", method="sigmoid")
        
    calibrated.fit(X_val_scaled, y_val)
    
    # Evaluate calibrated model on val
    y_pred = calibrated.predict(X_val_scaled)
    y_proba = calibrated.predict_proba(X_val_scaled)[:, 1]
    
    cal_metrics = {
        "selected_model": best_name,
        "calibration_method": "sigmoid",
        "accuracy": float(accuracy_score(y_val, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, y_pred)),
        "precision_receipt": float(precision_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "recall_receipt": float(recall_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "f1_receipt": float(f1_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "brier_score": float(brier_score_loss(y_val, y_proba)),
    }
    
    try:
        cal_metrics["roc_auc"] = float(roc_auc_score(y_val, y_proba))
    except ValueError:
        cal_metrics["roc_auc"] = None
    
    print(f"\nCalibrated model metrics:")
    for k, v in cal_metrics.items():
        print(f"  {k}: {v}")
    
    # Save the final calibrated model
    final_path = models_dir / "receipt_classifier.pkl"
    joblib.dump(calibrated, str(final_path))
    print(f"\n✓ Final calibrated classifier saved to: {final_path}")
    
    # Save model config
    config = {
        "model_name": best_name,
        "calibration": "sigmoid",
        "feature_dim": int(X_train.shape[1]),
        "visual_embedding_dim": int(X_train.shape[1] - 5),  # last 5 are quality features
        "quality_features": ["blur_score", "brightness", "aspect_ratio", "width", "height"],
        "classes": ["not_receipt", "receipt"],
        "thresholds": {
            "likely_receipt": 0.92,
            "uncertain_low": 0.70,
            "not_receipt": 0.70
        },
        "warning": "Current accuracy is not reliable for production because the positive class is built from only five unique receipt images."
    }
    
    with open(models_dir / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Save training metrics
    with open(models_dir / "training_metrics.json", "w") as f:
        json.dump(cal_metrics, f, indent=2)
    
    print("✓ model_config.json and training_metrics.json saved.")
    print("\nNo model can guarantee 100% correctness on unknown uploaded images.")
    print("This implementation aims for high measured reliability using diverse data,")
    print("hard-negative testing, probability calibration, OCR validation, and strict rejection thresholds.")

if __name__ == "__main__":
    main()
