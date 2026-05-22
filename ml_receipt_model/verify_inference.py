import os
import numpy as np
from PIL import Image
import onnxruntime as ort

def predict(image_path, session):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224), Image.Resampling.BILINEAR)
    
    # Preprocess
    img_data = np.array(img).astype(np.float32) / 255.0
    img_data = np.transpose(img_data, (2, 0, 1))
    img_data = np.expand_dims(img_data, axis=0)
    
    # Run
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: img_data})
    
    probs = outputs[0][0]
    
    # Class mapping: index 0 = non_receipt, index 1 = receipt
    non_receipt_prob = probs[0]
    receipt_prob = probs[1]
    
    return receipt_prob * 100, non_receipt_prob * 100

def main():
    model_path = "../backend/models/payment_receipt_classifier.onnx"
    print(f"Loading ONNX model from: {model_path}")
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    
    # Get model classes (can be read from model metadata)
    meta = session.get_modelmeta()
    print(f"Model metadata: {meta.custom_metadata_map}")
    
    # Test paths
    dataset_dir = "processed_dataset/binary/test"
    
    paytm_sample = None
    thread_sample = None
    image1_sample = None
    
    for root, dirs, files in os.walk(dataset_dir):
        for f in files:
            path = os.path.join(root, f)
            if "paytm" in f and paytm_sample is None:
                paytm_sample = path
            elif "thread" in f and thread_sample is None:
                thread_sample = path
            elif "image1" in f and image1_sample is None:
                image1_sample = path
                
    tests = {
        "Paytm Receipt (Expected: Receipt)": paytm_sample,
        "PhonePe Receipt (Expected: Receipt)": thread_sample,
        "Non-Receipt Image (Expected: Non-Receipt)": image1_sample
    }
    
    print("\n--- Running Verification ---")
    for name, img_path in tests.items():
        if img_path is None or not os.path.exists(img_path):
            print(f"⚠️ Sample file for {name} not found!")
            continue
            
        receipt_pct, non_receipt_pct = predict(img_path, session)
        print(f"\nTarget: {name}")
        print(f"  File: {os.path.basename(img_path)}")
        print(f"  Receipt Match Confidence: {receipt_pct:.2f}%")
        print(f"  Non-Receipt Confidence: {non_receipt_pct:.2f}%")
        
        # Advisory Check
        if "Expected: Receipt" in name:
            if receipt_pct >= 75:
                print("  ✅ Status: PASS (Correctly identified receipt)")
            else:
                print("  ❌ Status: FAIL (Failed to identify receipt)")
        else:
            if receipt_pct < 40:
                print("  ✅ Status: PASS (Correctly rejected non-receipt)")
            else:
                print("  ❌ Status: FAIL (Failed to reject non-receipt)")

if __name__ == "__main__":
    main()
