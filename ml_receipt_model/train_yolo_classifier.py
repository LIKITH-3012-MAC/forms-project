import argparse
import os
from ultralytics import YOLO

def train_classifier(data_dir, epochs=50, imgsz=224, batch=16):
    print(f"Starting YOLO classification training on dataset: {data_dir}")
    
    # Use YOLO11 classification pretrained model
    model = YOLO("yolo11n-cls.pt")
    
    # Ensure outputs directory exists
    os.makedirs("outputs", exist_ok=True)
    
    # Train the model
    results = model.train(
        data=data_dir,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=10,
        project="outputs",
        name="receipt_classifier"
    )
    
    print("Training complete. Models are saved in outputs/receipt_classifier/weights/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLO classifier for receipts.")
    parser.add_argument("--data", default="processed_dataset/binary", help="Path to the split dataset directory")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=224, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    args = parser.parse_args()
    
    if not os.path.exists(args.data):
        print(f"Error: Dataset directory {args.data} does not exist. Run build_binary_dataset.py first.")
        exit(1)
        
    train_classifier(args.data, args.epochs, args.imgsz, args.batch)
