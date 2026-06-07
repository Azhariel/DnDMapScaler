import sys
import math
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QFileDialog, QMessageBox, QLabel, 
                             QPushButton, QComboBox, QWidget, QVBoxLayout, 
                             QCheckBox, QDoubleSpinBox, QGroupBox, QFormLayout, QSplitter, QSlider)
from PyQt6.QtGui import QPixmap, QPen, QColor, QPolygonF, QPainter, QMouseEvent
from PyQt6.QtCore import Qt, QPointF, QRectF
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

PAPER_SIZES = {
    "A4": (21.0, 29.7),
    "A3": (29.7, 42.0),
    "US Letter": (21.59, 27.94)
}

class MapGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.image_item = None
        self.last_pan_point = None
        self.current_tool = "None"
        self.start_point = None
        self.temp_shape = None
        self.preview_items = []
        
        self.reference_pixels = 0
        self.main_window = parent

    def wheelEvent(self, event):
        if not self.image_item:
            super().wheelEvent(event)
            return
            
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)

    def clear_tiling_preview(self):
        for item in self.preview_items:
            self.scene.removeItem(item)
        self.preview_items.clear()

    def update_tiling_preview(self, chunk_w_px, chunk_h_px, step_w_px, step_h_px, rows, cols, img_w, img_h, 
                              draw_grid=False, grid_type="Square", grid_opacity=50, reference_px=0):
        self.clear_tiling_preview()
        
        pen = QPen(QColor(0, 150, 255, 200), 5, Qt.PenStyle.DashLine)
        
        if draw_grid and reference_px > 0:
            grid_pen = QPen(QColor(0, 0, 0, int(2.55 * grid_opacity)), max(1, int(reference_px / 50)))
            
            if grid_type == "Square":
                x = 0
                while x < img_w:
                    line = self.scene.addLine(x, 0, x, img_h, grid_pen)
                    self.preview_items.append(line)
                    x += reference_px
                y = 0
                while y < img_h:
                    line = self.scene.addLine(0, y, img_w, y, grid_pen)
                    self.preview_items.append(line)
                    y += reference_px
                    
            elif grid_type == "Hexagon":
                hex_r = reference_px / math.sqrt(3)
                hex_w = reference_px
                hex_h = 2 * hex_r
                x_step = hex_w
                y_step = hex_h * 0.75
                
                cols_hex = int(img_w / x_step) + 2
                rows_hex = int(img_h / y_step) + 2
                
                for row in range(rows_hex):
                    for col in range(cols_hex):
                        cx = col * hex_w
                        if row % 2 != 0:
                            cx += hex_w / 2
                        cy = row * y_step
                        
                        if cx > -hex_w and cx < img_w + hex_w and cy > -hex_h and cy < img_h + hex_h:
                            poly = QPolygonF()
                            for i in range(6):
                                angle = math.pi / 180 * (60 * i - 30)
                                poly.append(QPointF(cx + hex_r * math.cos(angle), cy + hex_r * math.sin(angle)))
                            polygon_item = self.scene.addPolygon(poly, grid_pen)
                            self.preview_items.append(polygon_item)
                            
        
        for r in range(rows):
            for c in range(cols):
                left = c * step_w_px
                upper = r * step_h_px
                w = min(chunk_w_px, img_w - left)
                h = min(chunk_h_px, img_h - upper)
                
                rect = self.scene.addRect(left, upper, w, h, pen)
                
                text = self.scene.addText(f"Page {r*cols + c + 1}")
                text.setDefaultTextColor(QColor(0, 150, 255, 255))
                text.setPos(left + 20, upper + 20)
                text_scale = max(1, chunk_w_px / 300.0)
                text.setScale(text_scale)
                
                self.preview_items.extend([rect, text])

    def set_image(self, filepath):
        self.scene.clear()
        self.preview_items.clear()
        pixmap = QPixmap(filepath)
        self.image_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.reference_pixels = 0
        self.temp_shape = None
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_pan_point = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if self.current_tool == "None" or not self.image_item:
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = self.mapToScene(event.pos())
            if self.temp_shape:
                self.scene.removeItem(self.temp_shape)
                self.temp_shape = None

    def mouseMoveEvent(self, event):
        if self.last_pan_point is not None:
            delta = event.pos() - self.last_pan_point
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pan_point = event.pos()
            return

        if self.current_tool == "None" or not self.start_point or not self.image_item:
            super().mouseMoveEvent(event)
            return
            
        end_point = self.mapToScene(event.pos())
        self.update_shape(end_point)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_pan_point = None
            if self.current_tool == "None":
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.current_tool == "None" or not self.start_point or not self.image_item:
            super().mouseReleaseEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            end_point = self.mapToScene(event.pos())
            self.update_shape(end_point)
            
            if self.current_tool == "Line":
                dx = end_point.x() - self.start_point.x()
                dy = end_point.y() - self.start_point.y()
                self.reference_pixels = math.sqrt(dx*dx + dy*dy)
            elif self.current_tool == "Square":
                dx = abs(end_point.x() - self.start_point.x())
                dy = abs(end_point.y() - self.start_point.y())
                self.reference_pixels = max(dx, dy)
            elif self.current_tool == "Hexagon":
                dx = abs(end_point.x() - self.start_point.x())
                dy = abs(end_point.y() - self.start_point.y())
                self.reference_pixels = max(dx, dy)
                
            self.start_point = None
            if self.main_window:
                self.main_window.statusBar().showMessage(f"Reference shape size: {self.reference_pixels:.2f} pixels")
                if self.main_window.btn_preview.isChecked():
                    self.main_window.preview_tiling()

    def update_shape(self, end_point):
        if self.temp_shape:
            self.scene.removeItem(self.temp_shape)
            
        pen = QPen(QColor(255, 0, 0, 200), 1)
        
        if self.current_tool == "Line":
            self.temp_shape = self.scene.addLine(self.start_point.x(), self.start_point.y(), 
                                                 end_point.x(), end_point.y(), pen)
        elif self.current_tool == "Square":
            side = max(abs(end_point.x() - self.start_point.x()), abs(end_point.y() - self.start_point.y()))
            rect = QRectF(self.start_point.x(), self.start_point.y(), side, side)
            if end_point.x() < self.start_point.x():
                rect.moveLeft(self.start_point.x() - side)
            if end_point.y() < self.start_point.y():
                rect.moveTop(self.start_point.y() - side)
            self.temp_shape = self.scene.addRect(rect, pen)
        elif self.current_tool == "Hexagon":
            w = abs(end_point.x() - self.start_point.x())
            h = abs(end_point.y() - self.start_point.y())
            size = max(w, h)
            
            cx = self.start_point.x() + (size/2 if end_point.x() > self.start_point.x() else -size/2)
            cy = self.start_point.y() + (size/2 if end_point.y() > self.start_point.y() else -size/2)
            
            r = size / math.sqrt(3)
            
            poly = QPolygonF()
            for i in range(6):
                angle_deg = 60 * i - 30
                angle_rad = math.pi / 180 * angle_deg
                poly.append(QPointF(cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)))
            self.temp_shape = self.scene.addPolygon(poly, pen)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("D&D Map Scaler & Tiler")
        self.resize(1200, 800)
        
        self.view = MapGraphicsView(self)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        
        btn_open = QPushButton("Open Map Image")
        btn_open.clicked.connect(self.open_image)
        btn_open.setMinimumHeight(40)
        left_layout.addWidget(btn_open)
        
        tool_group = QGroupBox("Reference Tool")
        tool_layout = QFormLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["None (Pan)", "Line", "Square", "Hexagon"])
        self.tool_combo.currentTextChanged.connect(self.change_tool)
        self.size_input = QDoubleSpinBox()
        self.size_input.setValue(2.5)
        self.size_input.setDecimals(2)
        self.size_input.setSingleStep(0.5)
        self.size_input.valueChanged.connect(self.on_setting_changed)
        tool_layout.addRow("Shape Tool:", self.tool_combo)
        tool_layout.addRow("Target Size (cm):", self.size_input)
        tool_group.setLayout(tool_layout)
        left_layout.addWidget(tool_group)
        
        paper_group = QGroupBox("Paper & Layout")
        paper_layout = QFormLayout()
        self.paper_combo = QComboBox()
        self.paper_combo.addItems(["A4", "A3", "US Letter"])
        self.paper_combo.currentTextChanged.connect(self.on_setting_changed)
        self.orient_combo = QComboBox()
        self.orient_combo.addItems(["Portrait", "Landscape"])
        self.orient_combo.currentTextChanged.connect(self.on_setting_changed)
        self.overlap_input = QDoubleSpinBox()
        self.overlap_input.setValue(1.0)
        self.overlap_input.setSingleStep(0.5)
        self.overlap_input.valueChanged.connect(self.on_setting_changed)
        paper_layout.addRow("Size:", self.paper_combo)
        paper_layout.addRow("Orientation:", self.orient_combo)
        paper_layout.addRow("Overlap (cm):", self.overlap_input)
        paper_group.setLayout(paper_layout)
        left_layout.addWidget(paper_group)
        
        export_group = QGroupBox("Export Features")
        export_layout = QVBoxLayout()
        self.skip_white_cb = QCheckBox("Skip Empty/White Pages")
        self.skip_white_cb.setChecked(True)
        self.cut_marks_cb = QCheckBox("Draw Cut Marks")
        self.cut_marks_cb.setChecked(True)
        self.grid_cb = QCheckBox("Bake Grid Overlay")
        self.grid_cb.toggled.connect(self.on_setting_changed)
        self.grid_type_combo = QComboBox()
        self.grid_type_combo.addItems(["Square", "Hexagon"])
        self.grid_type_combo.currentTextChanged.connect(self.on_setting_changed)
        
        self.grid_opacity_label = QLabel("Grid Opacity: 50%")
        self.grid_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity_slider.setRange(0, 100)
        self.grid_opacity_slider.setValue(50)
        self.grid_opacity_slider.valueChanged.connect(self.on_grid_opacity_changed)
        
        export_layout.addWidget(self.skip_white_cb)
        export_layout.addWidget(self.cut_marks_cb)
        export_layout.addWidget(self.grid_cb)
        export_layout.addWidget(self.grid_type_combo)
        export_layout.addWidget(self.grid_opacity_label)
        export_layout.addWidget(self.grid_opacity_slider)
        export_group.setLayout(export_layout)
        left_layout.addWidget(export_group)
        
        left_layout.addStretch()
        
        self.btn_preview = QPushButton("Toggle Preview Tiles")
        self.btn_preview.setCheckable(True)
        self.btn_preview.clicked.connect(self.toggle_preview_tiling)
        self.btn_preview.setMinimumHeight(40)
        left_layout.addWidget(self.btn_preview)
        
        btn_export = QPushButton("Export to Tiled PDF")
        btn_export.clicked.connect(self.export_pdf)
        btn_export.setMinimumHeight(50)
        btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px;")
        left_layout.addWidget(btn_export)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.view)
        splitter.setSizes([250, 950])
        
        self.setCentralWidget(splitter)
        self.current_image_path = None
        self.statusBar().showMessage("Ready. Open an image to start.")

    def get_paper_size_cm(self):
        w, h = PAPER_SIZES[self.paper_combo.currentText()]
        if self.orient_combo.currentText() == "Landscape":
            return h, w
        return w, h

    def on_setting_changed(self):
        if self.btn_preview.isChecked():
            self.preview_tiling()

    def on_grid_opacity_changed(self, value):
        self.grid_opacity_label.setText(f"Grid Opacity: {value}%")
        if self.btn_preview.isChecked():
            self.preview_tiling()

    def open_image(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Map Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if filepath:
            self.current_image_path = filepath
            self.view.set_image(filepath)
            self.statusBar().showMessage(f"Loaded: {os.path.basename(filepath)}. Select a Reference Shape tool and draw over a grid cell.")
            self.tool_combo.setCurrentText("Square")
            self.btn_preview.setChecked(False)

    def change_tool(self, tool_name):
        if "None" in tool_name:
            self.view.current_tool = "None"
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.view.current_tool = tool_name
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def toggle_preview_tiling(self, checked):
        if checked:
            success = self.preview_tiling()
            if not success:
                self.btn_preview.setChecked(False)
        else:
            self.view.clear_tiling_preview()
            self.statusBar().showMessage("Preview hidden.")

    def get_tiling_math(self):
        if not self.current_image_path or self.view.reference_pixels <= 0:
            return None
            
        real_size_cm = self.size_input.value()
        if real_size_cm <= 0:
            return None
            
        pixels_per_cm = self.view.reference_pixels / real_size_cm
        
        paper_w_cm, paper_h_cm = self.get_paper_size_cm()
        margin_cm = 1.0
        overlap_cm = self.overlap_input.value()
        
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
            
        img_w = self.view.image_item.pixmap().width()
        img_h = self.view.image_item.pixmap().height()
        
        cols = math.ceil((img_w - overlap_px) / step_w_px) if img_w > chunk_w_px else 1
        rows = math.ceil((img_h - overlap_px) / step_h_px) if img_h > chunk_h_px else 1
        
        cols = max(1, cols)
        rows = max(1, rows)
        
        return {
            'chunk_w_px': chunk_w_px, 'chunk_h_px': chunk_h_px,
            'step_w_px': step_w_px, 'step_h_px': step_h_px,
            'rows': rows, 'cols': cols,
            'img_w': img_w, 'img_h': img_h,
            'pixels_per_cm': pixels_per_cm,
            'paper_w_cm': paper_w_cm, 'paper_h_cm': paper_h_cm,
            'margin_cm': margin_cm
        }

    def preview_tiling(self):
        math_data = self.get_tiling_math()
        if not math_data:
            QMessageBox.warning(self, "Preview Error", "Invalid scale or overlap settings.")
            return False
            
        self.view.update_tiling_preview(
            math_data['chunk_w_px'], math_data['chunk_h_px'],
            math_data['step_w_px'], math_data['step_h_px'],
            math_data['rows'], math_data['cols'],
            math_data['img_w'], math_data['img_h'],
            draw_grid=self.grid_cb.isChecked(),
            grid_type=self.grid_type_combo.currentText(),
            grid_opacity=self.grid_opacity_slider.value(),
            reference_px=self.view.reference_pixels
        )
        self.statusBar().showMessage(f"Preview generated: {math_data['rows']} rows by {math_data['cols']} columns.")
        return True

    def export_pdf(self):
        math_data = self.get_tiling_math()
        if not math_data:
            QMessageBox.warning(self, "Error", "Invalid scale or overlap settings. Draw a shape first.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if not save_path:
            return
            
        self.statusBar().showMessage(f"Generating PDF with {math_data['rows']}x{math_data['cols']} pages...")
        QApplication.processEvents()
        
        try:
            img = Image.open(self.current_image_path)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.convert('RGBA').split()[3])
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load image:\n{e}")
            return
            
        try:
            paper_size_pt = (math_data['paper_w_cm'] * cm, math_data['paper_h_cm'] * cm)
            c = canvas.Canvas(save_path, pagesize=paper_size_pt)
            
            rows = math_data['rows']
            cols = math_data['cols']
            chunk_w_px = math_data['chunk_w_px']
            chunk_h_px = math_data['chunk_h_px']
            step_w_px = math_data['step_w_px']
            step_h_px = math_data['step_h_px']
            pixels_per_cm = math_data['pixels_per_cm']
            margin_cm = math_data['margin_cm']
            real_size_cm = self.size_input.value()
            
            for r in range(rows):
                for col in range(cols):
                    left = col * step_w_px
                    upper = r * step_h_px
                    right = min(left + chunk_w_px, math_data['img_w'])
                    lower = min(upper + chunk_h_px, math_data['img_h'])
                    
                    chunk = img.crop((left, upper, right, lower))
                    
                    if self.skip_white_cb.isChecked():
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
                    
                    chunk = chunk.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
                    
                    if self.grid_cb.isChecked():
                        overlay = Image.new("RGBA", chunk.size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(overlay)
                        grid_type = self.grid_type_combo.currentText()
                        grid_opacity = self.grid_opacity_slider.value()
                        cell_size_px = real_size_cm * (dpi / 2.54)
                        
                        offset_x_px = -( (left / pixels_per_cm) % real_size_cm ) * (dpi / 2.54)
                        offset_y_px = -( (upper / pixels_per_cm) % real_size_cm ) * (dpi / 2.54)
                        
                        grid_color = (0, 0, 0, int(2.55 * grid_opacity))
                        
                        if grid_type == "Square":
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
                        elif grid_type == "Hexagon":
                            hex_r = cell_size_px / math.sqrt(3)
                            hex_w = cell_size_px
                            hex_h = 2 * hex_r
                            x_step = hex_w
                            y_step = hex_h * 0.75
                            
                            start_col = int(offset_x_px / x_step) - 2
                            start_row = int(offset_y_px / y_step) - 2
                            end_col = int(target_w_px / x_step) + 2
                            end_row = int(target_h_px / y_step) + 2
                            
                            for row in range(start_row, end_row):
                                for col in range(start_col, end_col):
                                    cx = offset_x_px + col * hex_w
                                    if row % 2 != 0:
                                        cx += hex_w / 2
                                    cy = offset_y_px + row * y_step
                                    
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
                    
                    if self.cut_marks_cb.isChecked():
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
            QMessageBox.information(self, "Success", f"PDF successfully created at:\n{save_path}\nTotal pages: {rows*cols}.")
            self.statusBar().showMessage("PDF Export Complete")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred while generating PDF:\n{e}")
            self.statusBar().showMessage("Export Failed")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
