import math
import os
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from dataclasses import dataclass

@dataclass
class ExportConfig:
    save_path: str
    image_path: str
    real_size_cm: float
    skip_white: bool
    draw_cut_marks: bool
    draw_grid: bool
    grid_type: str
    grid_opacity: int
    scaler_method: str = "Lanczos (Smooth)"

def calculate_tiling(image_width, image_height, reference_pixels, real_size_cm, paper_w_cm, paper_h_cm, margin_cm, overlap_cm):
    if reference_pixels <= 0 or real_size_cm <= 0:
        return None
        
    pixels_per_cm = reference_pixels / real_size_cm
    
    printable_w_cm = paper_w_cm - 2 * margin_cm
    printable_h_cm = paper_h_cm - 2 * margin_cm
    
    if printable_w_cm <= overlap_cm or printable_h_cm <= overlap_cm:
        return None
        
    chunk_w_px = int(printable_w_cm * pixels_per_cm)
    chunk_h_px = int(printable_h_cm * pixels_per_cm)
    overlap_px = int(overlap_cm * pixels_per_cm)
    
    step_w_px = chunk_w_px - overlap_px
    step_h_px = chunk_h_px - overlap_px
    
    if step_w_px <= 0 or step_h_px <= 0:
        return None
        
    cols = math.ceil((image_width - overlap_px) / step_w_px) if image_width > chunk_w_px else 1
    rows = math.ceil((image_height - overlap_px) / step_h_px) if image_height > chunk_h_px else 1
    
    cols = max(1, cols)
    rows = max(1, rows)
    
    return {
        'chunk_w_px': chunk_w_px, 'chunk_h_px': chunk_h_px,
        'step_w_px': step_w_px, 'step_h_px': step_h_px,
        'rows': rows, 'cols': cols,
        'img_w': image_width, 'img_h': image_height,
        'pixels_per_cm': pixels_per_cm,
        'paper_w_cm': paper_w_cm, 'paper_h_cm': paper_h_cm,
        'margin_cm': margin_cm
    }

def export_to_pdf(config: ExportConfig, math_data: dict, status_callback=None):
    if status_callback:
        status_callback(f"Generating PDF with {math_data['rows']}x{math_data['cols']} pages...")
        
    img = Image.open(config.image_path)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.convert('RGBA').split()[3])
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
        
    paper_size_pt = (math_data['paper_w_cm'] * cm, math_data['paper_h_cm'] * cm)
    c = canvas.Canvas(config.save_path, pagesize=paper_size_pt)
    
    rows = math_data['rows']
    cols = math_data['cols']
    chunk_w_px = math_data['chunk_w_px']
    chunk_h_px = math_data['chunk_h_px']
    step_w_px = math_data['step_w_px']
    step_h_px = math_data['step_h_px']
    pixels_per_cm = math_data['pixels_per_cm']
    margin_cm = math_data['margin_cm']
    
    for r in range(rows):
        for col in range(cols):
            left = col * step_w_px
            upper = r * step_h_px
            right = min(left + chunk_w_px, math_data['img_w'])
            lower = min(upper + chunk_h_px, math_data['img_h'])
            
            chunk = img.crop((left, upper, right, lower))
            
            if config.skip_white:
                gray = chunk.convert("L")
                hist = gray.histogram()
                white_pixels = sum(hist[230:])
                total_pixels = gray.width * gray.height
                if (white_pixels / total_pixels) >= 0.98:
                    continue
                    
            chunk_real_w_cm = (right - left) / pixels_per_cm
            chunk_real_h_cm = (lower - upper) / pixels_per_cm
            
            dpi = 300
            target_w_px = int(chunk_real_w_cm * dpi / 2.54)
            target_h_px = int(chunk_real_h_cm * dpi / 2.54)
            target_w_px = max(1, target_w_px)
            target_h_px = max(1, target_h_px)
            
            if config.scaler_method == "Nearest (Pixel Art)":
                resampling_method = Image.Resampling.NEAREST
            else:
                resampling_method = Image.Resampling.LANCZOS
                
            chunk = chunk.resize((target_w_px, target_h_px), resampling_method)
            
            if config.draw_grid:
                overlay = Image.new("RGBA", chunk.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                cell_size_px = config.real_size_cm * (dpi / 2.54)
                
                offset_x_px = -( (left / pixels_per_cm) % config.real_size_cm ) * (dpi / 2.54)
                offset_y_px = -( (upper / pixels_per_cm) % config.real_size_cm ) * (dpi / 2.54)
                
                grid_color = (0, 0, 0, int(2.55 * config.grid_opacity))
                
                if config.grid_type == "Square":
                    x = offset_x_px
                    while x < target_w_px:
                        if x >= 0:
                            draw.line([(x, 0), (x, target_h_px)], fill=grid_color, width=3)
                        x += cell_size_px
                    y = offset_y_px
                    while y < target_h_px:
                        if y >= 0:
                            draw.line([(0, y), (target_w_px, y)], fill=grid_color, width=3)
                        y += cell_size_px
                elif config.grid_type == "Hexagon":
                    hex_r = cell_size_px / math.sqrt(3)
                    hex_w = cell_size_px
                    hex_h = 2 * hex_r
                    x_step = hex_w
                    y_step = hex_h * 0.75
                    
                    start_col = int(offset_x_px / x_step) - 2
                    start_row = int(offset_y_px / y_step) - 2
                    end_col = int(target_w_px / x_step) + 2
                    end_row = int(target_h_px / y_step) + 2
                    
                    for row_idx in range(start_row, end_row):
                        for col_idx in range(start_col, end_col):
                            cx = offset_x_px + col_idx * hex_w
                            if row_idx % 2 != 0:
                                cx += hex_w / 2
                            cy = offset_y_px + row_idx * y_step
                            
                            if cx > -hex_w and cx < target_w_px + hex_w and cy > -hex_h and cy < target_h_px + hex_h:
                                poly = []
                                for i in range(6):
                                    angle = math.pi / 180 * (60 * i - 30)
                                    poly.append((cx + hex_r * math.cos(angle), cy + hex_r * math.sin(angle)))
                                for i in range(6):
                                    draw.line([poly[i], poly[(i+1)%6]], fill=grid_color, width=3)
                    
                chunk = Image.alpha_composite(chunk.convert("RGBA"), overlay).convert("RGB")
                    
            temp_chunk_path = f"temp_chunk_export_{r}_{col}.jpg"
            chunk.save(temp_chunk_path, "JPEG", quality=95)
            
            draw_x = margin_cm * cm
            draw_y = math_data['paper_h_cm'] * cm - (margin_cm * cm) - (chunk_real_h_cm * cm)
            
            c.drawImage(temp_chunk_path, draw_x, draw_y, width=chunk_real_w_cm*cm, height=chunk_real_h_cm*cm)
            
            if config.draw_cut_marks:
                c.setStrokeColorRGB(0, 0, 0)
                c.setLineWidth(0.5)
                mark_len = 0.5 * cm
                corners = [
                    (draw_x, draw_y),
                    (draw_x + chunk_real_w_cm*cm, draw_y),
                    (draw_x, draw_y + chunk_real_h_cm*cm),
                    (draw_x + chunk_real_w_cm*cm, draw_y + chunk_real_h_cm*cm)
                ]
                for cx, cy in corners:
                    c.line(cx - mark_len, cy, cx + mark_len, cy)
                    c.line(cx, cy - mark_len, cx, cy + mark_len)
            
            c.showPage()
            if os.path.exists(temp_chunk_path):
                os.remove(temp_chunk_path)
                
    c.save()
    return rows * cols
