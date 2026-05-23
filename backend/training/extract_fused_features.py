import os
import json
import numpy as np
from pathlib import Path
import onnxruntime as ort
from PIL import Image
import cv2

def compute_blur_score(img_array):
    """Compute Laplacian variance as blur metric."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def compute_brightness(img_array):
    """Compute mean brightness of image."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(np.mean(gray))

def extract_features_for_split(session, input_name, output_name, split_dir, class_name, label):
    """Extract feature embeddings + quality features for all images in a class folder."""
    class_dir = Path(split_dir) / class_name
    files = sorted([f for f in class_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')])
    
    features_list = []
    labels_list = []
    filenames_list = []
    
    for f in files:
        try:
            img = Image.open(f).convert("RGB")
            img_resized = img.resize((224, 224), Image.BILINEAR)
            img_array = np.array(img_resized, dtype=np.float32)
            
            # Batch dimension first: shape (1, 224, 224, 3)
            img_batch = np.expand_dims(img_array, axis=0)
            
            # Extract visual embedding (1280-dim from GlobalAveragePooling layer)
            outputs = session.run([output_name], {input_name: img_batch})
            visual_embedding = outputs[0].flatten()
            
            # Quality features (computed on original image size to match production image_validator.py)
            img_orig_array = np.array(img)
            blur_score = compute_blur_score(img_orig_array)
            brightness = compute_brightness(img_orig_array)
            orig_w, orig_h = img.size
            aspect_ratio = orig_w / max(orig_h, 1)
            
            # Combine: visual_embedding + quality features
            quality_features = np.array([blur_score, brightness, aspect_ratio, orig_w, orig_h], dtype=np.float32)
            combined = np.concatenate([visual_embedding, quality_features])
            
            features_list.append(combined)
            labels_list.append(label)
            filenames_list.append(str(f))
        except Exception as e:
            print(f"  Error processing {f.name}: {e}")
            
    return features_list, labels_list, filenames_list

def main():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    dataset_dir = base_dir / "dataset"
    
    # Load the trained feature extractor ONNX session
    onnx_path = models_dir / "receipt_feature_extractor.onnx"
    if not onnx_path.exists():
        print(f"Error: ONNX Feature extractor not found at {onnx_path}")
        return
        
    print(f"Loading ONNX feature extractor from {onnx_path}...")
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print(f"  Input name: {input_name}, Output name: {output_name}")
    
    # Extract features for each split
    for split_name in ["train", "val", "test"]:
        split_dir = dataset_dir / split_name
        if not split_dir.exists():
            print(f"Skipping {split_name}: directory not found")
            continue
            
        print(f"\nExtracting features for {split_name}...")
        
        all_features = []
        all_labels = []
        all_filenames = []
        
        # Class 0 = not_receipt, Class 1 = receipt
        for class_name, label in [("not_receipt", 0), ("receipt", 1)]:
            features, labels, filenames = extract_features_for_split(
                session, input_name, output_name, split_dir, class_name, label
            )
            all_features.extend(features)
            all_labels.extend(labels)
            all_filenames.extend(filenames)
            print(f"  {class_name}: {len(features)} samples extracted")
        
        # Save as numpy arrays
        features_dir = models_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)
        
        X = np.array(all_features, dtype=np.float32)
        y = np.array(all_labels, dtype=np.int32)
        
        np.save(str(features_dir / f"X_{split_name}.npy"), X)
        np.save(str(features_dir / f"y_{split_name}.npy"), y)
        
        # Save filenames for debugging
        with open(features_dir / f"filenames_{split_name}.json", "w") as f:
            json.dump(all_filenames, f, indent=2)
            
        print(f"  Saved {split_name}: X shape={X.shape}, y shape={y.shape}")
        print(f"  Class distribution: not_receipt={np.sum(y==0)}, receipt={np.sum(y==1)}")
    
    print("\n✓ Feature extraction complete. Saved to backend/models/features/")

if __name__ == "__main__":
    main()
