import cv2
import argparse
from pathlib import Path

def redact_image(filepath, out_dir):
    img = cv2.imread(filepath)
    if img is None:
        print(f"Could not read {filepath}")
        return

    clone = img.copy()
    rects = []
    
    # Interactive selection loop
    while True:
        roi = cv2.selectROI("Select sensitive area to blur (Press Enter/Space to confirm, C to cancel, Esc to finish)", img, showCrosshair=True, fromCenter=False)
        if roi == (0, 0, 0, 0):
            break
        rects.append(roi)
        # Apply temporary blur to show what's selected
        x, y, w, h = roi
        roi_img = img[y:y+h, x:x+w]
        blurred = cv2.GaussianBlur(roi_img, (51, 51), 0)
        img[y:y+h, x:x+w] = blurred

    cv2.destroyAllWindows()
    
    # Apply final blur on clone
    for (x, y, w, h) in rects:
        roi_img = clone[y:y+h, x:x+w]
        blurred = cv2.GaussianBlur(roi_img, (51, 51), 0)
        clone[y:y+h, x:x+w] = blurred
        
    out_path = Path(out_dir) / Path(filepath).name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), clone)
    print(f"Saved redacted image to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactively blur sensitive info in images.")
    parser.add_argument("images", nargs="+", help="Paths to images")
    parser.add_argument("--out", required=True, help="Output directory for redacted images")
    args = parser.parse_args()
    
    for filepath in args.images:
        print(f"Redacting {filepath}")
        redact_image(filepath, args.out)
