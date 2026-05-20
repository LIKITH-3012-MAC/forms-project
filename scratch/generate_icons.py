import os
from PIL import Image, ImageDraw

def draw_logo(size):
    # Base canvas with dark theme color
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale coordinates proportionally to the target size
    scale = size / 512.0
    
    # Draw rounded square base
    bg_margin = int(16 * scale)
    bg_radius = int(108 * scale)
    bg_box = [bg_margin, bg_margin, size - bg_margin, size - bg_margin]
    
    # Draw dark rounded square base
    # Draw outer glow/border by drawing a slightly larger gradient-colored rounded square
    border_width = int(8 * scale)
    
    # PIL draw rounded_rectangle requires radius
    # We will fill it with radial gradient approximation or deep space grey
    draw.rounded_rectangle(bg_box, radius=bg_radius, fill=(15, 23, 42, 255), outline=(99, 102, 241, 255), width=border_width)
    
    # Draw subtle background glow core
    core_radius = int(140 * scale)
    cx, cy = size // 2, size // 2
    draw.ellipse([cx - core_radius, cy - core_radius, cx + core_radius, cy + core_radius], fill=(6, 182, 212, 20))
    
    # Draw minimal form document outline
    doc_points = [
        (int(190*scale), int(140*scale)),
        (int(290*scale), int(140*scale)),
        (int(372*scale), int(222*scale)),
        (int(372*scale), int(372*scale)),
        (int(190*scale), int(372*scale))
    ]
    # Draw polygon border
    draw.polygon(doc_points, outline=(99, 102, 241, 255), fill=None)
    # Re-draw lines for thickness
    for i in range(len(doc_points)):
        p1 = doc_points[i]
        p2 = doc_points[(i+1)%len(doc_points)]
        # Skip top right fold line which we'll draw folded
        if i == 1:
            continue
        draw.line([p1, p2], fill=(99, 102, 241, 255), width=int(12*scale))
        
    # Draw folded corner lines
    draw.line([(int(290*scale), int(140*scale)), (int(290*scale), int(222*scale))], fill=(99, 102, 241, 255), width=int(12*scale))
    draw.line([(int(290*scale), int(222*scale)), (int(372*scale), int(222*scale))], fill=(99, 102, 241, 255), width=int(12*scale))
    
    # Draw document content lines
    draw.line([(int(200*scale), int(200*scale)), (int(250*scale), int(200*scale))], fill=(6, 182, 212, 100), width=int(10*scale))
    draw.line([(int(200*scale), int(260*scale)), (int(312*scale), int(260*scale))], fill=(6, 182, 212, 100), width=int(10*scale))
    
    # Draw Glowing Cyan Checkmark
    # Checkmark coords: M205 320l35 35 68-68
    chk_p1 = (int(205*scale), int(320*scale))
    chk_p2 = (int(240*scale), int(355*scale))
    chk_p3 = (int(308*scale), int(287*scale))
    
    draw.line([chk_p1, chk_p2], fill=(6, 182, 212, 255), width=int(16*scale))
    draw.line([chk_p2, chk_p3], fill=(6, 182, 212, 255), width=int(16*scale))
    
    # Draw Purple Spark Rect (x=330, y=325, w=22, h=22)
    sp_margin = int(330*scale)
    sp_size = int(22*scale)
    draw.rounded_rectangle([sp_margin, int(325*scale), sp_margin+sp_size, int(325*scale)+sp_size], radius=int(6*scale), fill=(139, 92, 246, 255))
    
    # Draw Cyan Dot
    dot_radius = int(8*scale)
    draw.ellipse([int(341*scale)-dot_radius, int(365*scale)-dot_radius, int(341*scale)+dot_radius, int(365*scale)+dot_radius], fill=(6, 182, 212, 255))
    
    return img

def main():
    assets_dir = "/Users/likithnaidu/Desktop/forms-project/frontend/assets"
    
    print("Generating apple-touch-icon.png (180x180)...")
    img_180 = draw_logo(180)
    img_180.save(os.path.join(assets_dir, "apple-touch-icon.png"), "PNG")
    
    print("Generating icon-192.png (192x192)...")
    img_192 = draw_logo(192)
    img_192.save(os.path.join(assets_dir, "icon-192.png"), "PNG")
    
    print("Generating icon-512.png (512x512)...")
    img_512 = draw_logo(512)
    img_512.save(os.path.join(assets_dir, "icon-512.png"), "PNG")
    
    print("Generating favicon.ico fallback...")
    # Convert sizes 16x16, 32x32, 48x48
    ico_img = draw_logo(256)
    ico_img.save(os.path.join(assets_dir, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    
    print("Successfully generated all favicon assets!")

if __name__ == "__main__":
    main()
