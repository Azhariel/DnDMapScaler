import os
from PyQt6.QtWidgets import (QMainWindow, QGraphicsView, QFileDialog, QMessageBox, 
                             QLabel, QPushButton, QComboBox, QWidget, QVBoxLayout, 
                             QCheckBox, QDoubleSpinBox, QGroupBox, QFormLayout, QSplitter, QSlider, QApplication)
from PyQt6.QtCore import Qt
from map_view import MapGraphicsView
from constants import PAPER_SIZES
from pdf_exporter import calculate_tiling, export_to_pdf, ExportConfig

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
        paper_w_cm, paper_h_cm = self.get_paper_size_cm()
        overlap_cm = self.overlap_input.value()
        margin_cm = 1.0
        
        img_w = self.view.image_item.pixmap().width()
        img_h = self.view.image_item.pixmap().height()
        
        return calculate_tiling(
            img_w, img_h, self.view.reference_pixels, 
            real_size_cm, paper_w_cm, paper_h_cm, 
            margin_cm, overlap_cm
        )

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
            
        QApplication.processEvents()
        
        config = ExportConfig(
            save_path=save_path,
            image_path=self.current_image_path,
            real_size_cm=self.size_input.value(),
            skip_white=self.skip_white_cb.isChecked(),
            draw_cut_marks=self.cut_marks_cb.isChecked(),
            draw_grid=self.grid_cb.isChecked(),
            grid_type=self.grid_type_combo.currentText(),
            grid_opacity=self.grid_opacity_slider.value()
        )
        
        try:
            total_pages = export_to_pdf(
                config=config, 
                math_data=math_data, 
                status_callback=self.statusBar().showMessage
            )
            QMessageBox.information(self, "Success", f"PDF successfully created at:\n{save_path}\nTotal pages: {total_pages}.")
            self.statusBar().showMessage("PDF Export Complete")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred while generating PDF:\n{e}")
            self.statusBar().showMessage("Export Failed")
