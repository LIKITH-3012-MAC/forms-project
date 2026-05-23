import json
import numpy as np
from pathlib import Path
import joblib

def main():
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "backend/models"
    features_dir = models_dir / "features"
    
    # Load scaler and classifier
    scaler = joblib.load(str(models_dir / "feature_scaler.pkl"))
    classifier = joblib.load(str(models_dir / "receipt_classifier.pkl"))
    
    for split in ["val", "test"]:
        print(f"\n==================== {split.upper()} SPLIT ====================")
        X = np.load(str(features_dir / f"X_{split}.npy"))
        y = np.load(str(features_dir / f"y_{split}.npy"))
        
        with open(features_dir / f"filenames_{split}.json", "r") as f:
            filenames = json.load(f)
            
        X_scaled = scaler.transform(X)
        probas = classifier.predict_proba(X_scaled)[:, 1]
        preds = classifier.predict(X_scaled)
        
        for idx, (fname, true_label, prob, pred) in enumerate(zip(filenames, y, probas, preds)):
            basename = Path(fname).name
            status = "CORRECT" if true_label == pred else "MISCLASSIFIED"
            print(f"{basename} | True: {true_label} | Pred: {pred} | Prob: {prob:.4f} | {status}")

if __name__ == "__main__":
    main()
