import argparse
import os
import sys
from PIL import Image
import matplotlib.pyplot as plt

def inspect_image(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
        
    try:
        img = Image.open(filepath)
        print("-" * 40)
        print(f"File: {os.path.basename(filepath)}")
        print(f"Path: {filepath}")
        print(f"Format: {img.format}")
        print(f"Size: {img.size[0]}x{img.size[1]}")
        print(f"Mode: {img.mode}")
        print(f"File size: {os.path.getsize(filepath) / 1024:.2f} KB")
        print("-" * 40)
        
        # Display interactively
        plt.figure(figsize=(8, 8))
        plt.imshow(img)
        plt.title(f"{os.path.basename(filepath)} - Close window to continue")
        plt.axis('off')
        plt.show()
        
        return True
    except Exception as e:
        print(f"Error reading image {filepath}: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visually inspect local images to assign them correct AI dataset labels.")
    parser.add_argument("images", nargs="+", help="Paths to local image files")
    args = parser.parse_args()
    
    print("Opening images for visual inspection. Please note the correct class for each (e.g. payment_receipt, non_receipt).")
    
    for filepath in args.images:
        inspect_image(filepath)
        
    print("\nInspection complete. Update copy_local_seed_images.py with the confirmed labels.")
