import argparse
import os
from ultralytics import YOLO

def export_onnx(model_path):
    print(f"Exporting YOLO model {model_path} to ONNX format...")
    if not os.path.exists(model_path):
        print("Model file not found!")
        return
        
    model = YOLO(model_path)
    
    # Export the model
    # imgsz=224 creates a static size ONNX model (faster).
    success = model.export(format="onnx", imgsz=224, simplify=True)
    
    print(f"Export complete: {success}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export trained YOLO model to ONNX.")
    parser.add_argument("--model", default="outputs/receipt_classifier/weights/best.pt", help="Path to best.pt")
    args = parser.parse_args()
    
    export_onnx(args.model)
