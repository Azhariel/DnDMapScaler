import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from main_window import MainWindow
from constants import PAPER_SIZES

@pytest.fixture(scope="session")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def window(app):
    win = MainWindow()
    yield win
    win.close()

def test_paper_sizes():
    assert "A4" in PAPER_SIZES
    assert PAPER_SIZES["A4"] == (21.0, 29.7)
    assert "A3" in PAPER_SIZES
    assert "US Letter" in PAPER_SIZES
    
def test_get_paper_size_cm_portrait(window):
    window.paper_combo.setCurrentText("A4")
    window.orient_combo.setCurrentText("Portrait")
    w, h = window.get_paper_size_cm()
    assert w == 21.0
    assert h == 29.7
    
def test_get_paper_size_cm_landscape(window):
    window.paper_combo.setCurrentText("A4")
    window.orient_combo.setCurrentText("Landscape")
    w, h = window.get_paper_size_cm()
    assert w == 29.7
    assert h == 21.0

def test_tiling_math_no_image(window):
    # Without an image loaded, get_tiling_math should return None
    assert window.get_tiling_math() is None

def test_change_tool(window):
    window.change_tool("Square")
    assert window.view.current_tool == "Square"
    
def test_grid_opacity_changed(window):
    window.on_grid_opacity_changed(75)
    assert window.grid_opacity_label.text() == "Grid Opacity: 75%"
    
def test_default_ui_state(window):
    assert window.skip_white_cb.isChecked() is True
    assert window.cut_marks_cb.isChecked() is True
    assert window.grid_cb.isChecked() is False
    assert window.size_input.value() == 2.5
    assert window.overlap_input.value() == 1.0
