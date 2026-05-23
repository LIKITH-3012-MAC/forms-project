import os
import json
import numpy as np
from pathlib import Path
import tensorflow as tf
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

def extract_features_for_split(model, split_dir, class_name, label):
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
            
            # Preprocess for EfficientNet
            img_batch = np.expand_dims(img_array, axis=0)
            img_batch = tf.keras.applications.efficientnet.preprocess_input(img_batch)
            
            # Extract visual embedding (1280-dim from GlobalAveragePooling)
            visual_embedding = model.predict(img_batch, verbose=0).flatten()
            
            # Quality features
            blur_score = compute_blur_score(np.array(img_resized))
            brightness = compute_brightness(np.array(img_resized))
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
    
    # Load the trained feature extractor
    extractor_path = models_dir / "receipt_feature_extractor.keras"
    if not extractor_path.exists():
        print(f"Error: Feature extractor not found at {extractor_path}")
        print("Run train_visual_extractor.py first.")
        return
        
    print(f"Loading feature extractor from {extractor_path}...")
    full_model = tf.keras.models.load_model(
        str(extractor_path),
        custom_objects={'preprocess_input': tf.keras.applications.efficientnet.preprocess_input}
    )
    
    # Build a sub-model that outputs at the feature_output layer (before dropout/classifier)
    feature_layer = None
    for layer in full_model.layers:
        if layer.name == "feature_output":
            feature_layer = layer
            break
    
    if feature_layer is None:
        # Fallback: use the layer before dropout
        # The GlobalAveragePooling2D layer should be the 4th-to-last layer
        feature_layer = full_model.layers[-3]
        print(f"  Using fallback feature layer: {feature_layer.name}")
    else:
        print(f"  Using feature layer: {feature_layer.name}")
    
    feature_model = tf.keras.Model(inputs=full_model.input, outputs=feature_layer.output)
    
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
                feature_model, split_dir, class_name, label
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
