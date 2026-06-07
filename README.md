# D&D Map Scaler & Tiler 🗺️⚔️

A powerful, standalone desktop application built with Python and PyQt6 specifically designed for Dungeon Masters and Tabletop RPG players. This tool allows you to effortlessly load digital battle maps, scale them to exact real-world printed dimensions (e.g., exactly 2.5cm per square), and automatically slice them into a multi-page PDF ready for your home printer.

## ✨ Features

* **Intelligent Scaling:** Draw a line, square, or hexagon directly over your map's grid to tell the app the scale. Set your desired real-world size (e.g., 2.5cm or 1 inch), and the app calculates the rest.
* **Smart PDF Tiling:** Automatically slices large, high-resolution maps across multiple pages of A4, A3, or US Letter paper.
* **Paper-Saving Logic (Skip Empty Pages):** Automatically detects and drops tiles that are completely blank or white to save you expensive printer ink.
* **Taping Overlap (Bleed Area):** Generates a configurable overlap margin (e.g., 1.0 cm) between pages so you can seamlessly glue or tape your map together without gaps.
* **Scissor Cut Marks:** Automatically draws faint crosshairs on the corners of the printed map chunks so you know exactly where to trim the printer margins.
* **Grid Generator:** Have a map without a grid? The app can bake a perfect Square or Hexagon grid overlay directly onto the PDF before exporting, complete with a live-preview opacity slider.
* **High-Quality Export:** Uses Lanczos resampling and outputs at crisp 300 DPI.
* **Live Tiling Preview:** Visually see exactly where the page breaks will occur on your map before you ever hit export.

## 🚀 Installation & Running

The easiest way to run the application is to use the provided Windows batch script which handles virtual environment activation automatically:

1. Clone or download this repository.
2. Ensure you have Python installed on your system.
3. Simply double-click `run.bat` on Windows! 

If you prefer to run it manually via the terminal:

```bash
# Create a virtual environment
python -m venv .venv

# Activate it (Windows)
.\.venv\Scripts\activate
# Activate it (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

## 📖 How to Use

1. **Load Map:** Click `Open Map Image` and select your digital map (PNG, JPG, WEBP, etc.).
2. **Set Scale:** 
   - Select a `Shape Tool` (like Square) from the left panel.
   - Click and drag over exactly ONE grid square on the loaded map image.
   - Ensure the `Target Size (cm)` is set to your preferred printed size (default is 2.5 cm).
3. **Configure Layout:** Select your paper size, orientation, and adjust the overlap if desired.
4. **Export Settings:** Toggle features like "Skip White Pages", "Cut Marks", or "Bake Grid Overlay".
5. **Preview:** Click `Toggle Preview Tiles` to see exactly how your map will print.
6. **Export:** Click `Export to Tiled PDF` and save your printable masterpiece!

## 🧩 Architecture

The codebase has been highly modularized for maintainability and testing:
- `main.py`: Application entry point.
- `main_window.py`: Controls the UI layout, state, and interaction bindings.
- `map_view.py`: Custom `QGraphicsView` managing the canvas, zoom/pan interactions, and shape rendering.
- `pdf_exporter.py`: A pure export engine utilizing Pillow and ReportLab to calculate coordinates and generate the PDF independent of the UI.
- `constants.py`: Application-wide configuration and magic numbers.

## 🧪 Testing

The project includes a robust test suite covering logic, math, and UI states. To run the tests, ensure your virtual environment is active and execute:

```bash
pytest test_main.py
```

## 💖 Support

This tool is entirely free and open-source. However, if it saved your campaign, saved you printer ink, or just made your DM prep a little easier, consider supporting my work!

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Azhariel)
