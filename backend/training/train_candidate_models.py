import json
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, classification_report
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import joblib

def load_features(features_dir, split_name):
    X = np.load(str(features_dir / f"X_{split_name}.npy"))
    y = np.load(str(features_dir / f"y_{split_name}.npy"))
    return X, y

def evaluate_model(name, model, X_val, y_val):
    """Evaluate a single model and return metrics dict."""
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else None
    
    metrics = {
        "name": name,
        "accuracy": float(accuracy_score(y_val, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, y_pred)),
        "precision_receipt": float(precision_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "recall_receipt": float(recall_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "f1_receipt": float(f1_score(y_val, y_pred, pos_label=1, zero_division=0)),
        "precision_not_receipt": float(precision_score(y_val, y_pred, pos_label=0, zero_division=0)),
        "recall_not_receipt": float(recall_score(y_val, y_pred, pos_label=0, zero_division=0)),
        "f1_not_receipt": float(f1_score(y_val, y_pred, pos_label=0, zero_division=0)),
    }
    
    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_val, y_proba))
        except ValueError:
            metrics["roc_auc"] = None
    
    # False positive rate: not_receipt images misclassified as receipt
    fp = np.sum((y_pred == 1) & (y_val == 0))
    tn = np.sum((y_pred == 0) & (y_val == 0))
    metrics["false_positive_rate"] = float(fp / max(fp + tn, 1))
    
    # False negative rate: receipt images misclassified as not_receipt
    fn = np.sum((y_pred == 0) & (y_val == 1))
    tp = np.sum((y_pred == 1) & (y_val == 1))
    metrics["false_negative_rate"] = float(fn / max(fn + tp, 1))
    
    return metrics

def main():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    features_dir = models_dir / "features"
    
    if not features_dir.exists():
        print("Error: Features directory not found. Run extract_fused_features.py first.")
        return
    
    X_train, y_train = load_features(features_dir, "train")
    X_val, y_val = load_features(features_dir, "val")
    
    print(f"Train: X={X_train.shape}, y={y_train.shape} (receipt={np.sum(y_train==1)}, not_receipt={np.sum(y_train==0)})")
    print(f"Val:   X={X_val.shape}, y={y_val.shape} (receipt={np.sum(y_val==1)}, not_receipt={np.sum(y_val==0)})")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Save scaler
    joblib.dump(scaler, str(models_dir / "feature_scaler.pkl"))
    print("✓ Feature scaler saved.")
    
    # Define candidate models
    candidates = {
        "LogisticRegression": LogisticRegression(
            class_weight="balanced", max_iter=3000, C=1.0, solver="lbfgs"
        ),
        "SVC_RBF": SVC(
            kernel="rbf", probability=True, class_weight="balanced", C=1.0, gamma="scale"
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.1, max_depth=5, min_samples_leaf=5
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=200, class_weight="balanced", max_depth=10, min_samples_leaf=3, n_jobs=-1
        ),
    }
    
    results = []
    trained_models = {}
    
    for name, model in candidates.items():
        print(f"\nTraining {name}...")
        model.fit(X_train_scaled, y_train)
        
        metrics = evaluate_model(name, model, X_val_scaled, y_val)
        results.append(metrics)
        trained_models[name] = model
        
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
        print(f"  Precision (receipt): {metrics['precision_receipt']:.4f}")
        print(f"  Recall (receipt): {metrics['recall_receipt']:.4f}")
        print(f"  F1 (receipt): {metrics['f1_receipt']:.4f}")
        print(f"  False Positive Rate: {metrics['false_positive_rate']:.4f}")
        print(f"  ROC-AUC: {metrics.get('roc_auc', 'N/A')}")
    
    # Save all results
    with open(models_dir / "candidate_model_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save all trained models for later selection
    for name, model in trained_models.items():
        joblib.dump(model, str(models_dir / f"candidate_{name}.pkl"))
    
    print("\n✓ All candidate models trained and saved.")
    print("Run calibrate_and_select_model.py to pick the best one.")

if __name__ == "__main__":
    main()
