import json
import numpy as np
from pathlib import Path
import tensorflow as tf
from PIL import Image
import cv2
import joblib

def compute_blur_score(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def compute_brightness(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(np.mean(gray))

def predict_single(img_path, feature_model, classifier, scaler):
    """Predict receipt probability for a single image file."""
    img = Image.open(img_path).convert("RGB")
    img_resized = img.resize((224, 224), Image.BILINEAR)
    img_array = np.array(img_resized, dtype=np.float32)
    
    img_batch = np.expand_dims(img_array, axis=0)
    img_batch = tf.keras.applications.efficientnet.preprocess_input(img_batch)
    
    visual_embedding = feature_model.predict(img_batch, verbose=0).flatten()
    
    blur_score = compute_blur_score(np.array(img_resized))
    brightness = compute_brightness(np.array(img_resized))
    orig_w, orig_h = img.size
    aspect_ratio = orig_w / max(orig_h, 1)
    
    quality_features = np.array([blur_score, brightness, aspect_ratio, orig_w, orig_h], dtype=np.float32)
    combined = np.concatenate([visual_embedding, quality_features]).reshape(1, -1)
    
    combined_scaled = scaler.transform(combined)
    proba = classifier.predict_proba(combined_scaled)[0]
    
    return {
        "not_receipt_prob": float(proba[0]),
        "receipt_prob": float(proba[1]),
        "prediction": "receipt" if proba[1] >= 0.5 else "not_receipt"
    }

def main():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    dataset_dir = base_dir / "dataset"
    
    # Load models
    extractor_path = models_dir / "receipt_feature_extractor.keras"
    classifier_path = models_dir / "receipt_classifier.pkl"
    scaler_path = models_dir / "feature_scaler.pkl"
    
    for p in [extractor_path, classifier_path, scaler_path]:
        if not p.exists():
            print(f"Error: {p} not found. Complete training pipeline first.")
            return
    
    print("Loading models...")
    full_model = tf.keras.models.load_model(
        str(extractor_path),
        custom_objects={'preprocess_input': tf.keras.applications.efficientnet.preprocess_input}
    )
    
    feature_layer = None
    for layer in full_model.layers:
        if layer.name == "feature_output":
            feature_layer = layer
            break
    if feature_layer is None:
        feature_layer = full_model.layers[-3]
    
    feature_model = tf.keras.Model(inputs=full_model.input, outputs=feature_layer.output)
    classifier = joblib.load(str(classifier_path))
    scaler = joblib.load(str(scaler_path))
    
    # Generate hard negatives for testing
    hard_neg_dir = dataset_dir / "hard_negatives"
    
    test_cases = []
    
    # Test with actual test set images
    test_dir = dataset_dir / "test"
    if test_dir.exists():
        for class_name in ["receipt", "not_receipt"]:
            class_dir = test_dir / class_name
            if class_dir.exists():
                for f in sorted(class_dir.iterdir())[:5]:
                    if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                        test_cases.append((f, class_name))
    
    # Test with hard negatives
    if hard_neg_dir.exists():
        for subdir in hard_neg_dir.iterdir():
            if subdir.is_dir():
                for f in sorted(subdir.iterdir())[:3]:
                    if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                        test_cases.append((f, "not_receipt"))
    
    if not test_cases:
        print("No test images found. Skipping hard negative tests.")
        return
    
    false_positives = []
    false_negatives = []
    results = []
    
    print(f"\nRunning hard negative test on {len(test_cases)} images...\n")
    
    for img_path, expected_class in test_cases:
        result = predict_single(img_path, feature_model, classifier, scaler)
        predicted = result["prediction"]
        receipt_prob = result["receipt_prob"]
        
        status = "✅ PASS" if predicted == expected_class else "❌ FAIL"
        
        entry = {
            "file": str(img_path.name),
            "expected": expected_class,
            "predicted": predicted,
            "receipt_probability": round(receipt_prob * 100, 2),
            "pass": predicted == expected_class
        }
        results.append(entry)
        
        if predicted != expected_class:
            if expected_class == "not_receipt" and predicted == "receipt":
                false_positives.append(entry)
            elif expected_class == "receipt" and predicted == "not_receipt":
                false_negatives.append(entry)
        
        print(f"  {status} | {img_path.name} | Expected={expected_class} | Got={predicted} | Receipt%={receipt_prob*100:.1f}")
    
    # Save reports
    with open(models_dir / "false_positive_report.json", "w") as f:
        json.dump(false_positives, f, indent=2)
    
    with open(models_dir / "false_negative_report.json", "w") as f:
        json.dump(false_negatives, f, indent=2)
    
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    
    print(f"\n{'='*60}")
    print(f"HARD NEGATIVE TEST RESULTS")
    print(f"{'='*60}")
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"False Positives (non-receipt accepted as receipt): {len(false_positives)}")
    print(f"False Negatives (receipt rejected): {len(false_negatives)}")
    
    if false_positives:
        print(f"\n⚠️  DEPLOYMENT BLOCKED: {len(false_positives)} non-receipt images were accepted as receipts!")
        for fp in false_positives:
            print(f"    - {fp['file']} (receipt_prob={fp['receipt_probability']}%)")
    else:
        print("\n✓ No false positives detected in hard negative test.")
    
    print(f"\n✓ Reports saved to {models_dir}")

if __name__ == "__main__":
    main()
