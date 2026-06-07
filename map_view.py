import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QPixmap, QPen, QColor, QPolygonF, QPainter
from PyQt6.QtCore import Qt, QPointF, QRectF

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
                text.setScale(max(1, chunk_w_px / 300.0))
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
