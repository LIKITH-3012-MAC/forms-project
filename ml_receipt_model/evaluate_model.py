import argparse
import os
from ultralytics import YOLO

def evaluate(model_path, data_dir):
    print(f"Evaluating YOLO model: {model_path} on {data_dir}")
    if not os.path.exists(model_path):
        print("Model file not found!")
        return
        
    model = YOLO(model_path)
    
    # Run evaluation on the test split
    metrics = model.val(data=data_dir, split="test")
    print("\n--- Evaluation Results ---")
    print(f"Top1 Accuracy: {metrics.top1}")
    print(f"Top5 Accuracy: {metrics.top5}")
    # YOLO automatically generates confusion matrices in the runs/ folder

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate trained YOLO classifier.")
    parser.add_argument("--model", default="outputs/receipt_classifier/weights/best.pt", help="Path to best.pt")
    parser.add_argument("--data", default="processed_dataset/binary", help="Path to the split dataset directory")
    args = parser.parse_args()
    
    evaluate(args.model, args.data)
