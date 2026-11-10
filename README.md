# PARYAS AutoCrop Studio

A local-first Windows desktop photo utility for automatic portrait cropping, enhancement, batch processing, and export.

## Features

- Import one or many images (JPG, JPEG, PNG, BMP, TIFF, WebP).
- Automatic face-aware portrait crop using OpenCV's bundled Haar cascade, with a centered fallback when no face is found.
- Presets for 35 x 45 mm, 480 x 672 px, 86 x 54 mm, and custom pixel dimensions.
- Natural enhancement, sharpening, brightness/contrast, and JPEG size targeting.
- Before/after preview and batch export.
- All image processing happens locally; no photo uploads.

## Run on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/.
2. Open this folder in PowerShell.
3. Create and activate a virtual environment:

   `py -m venv .venv`

   `.\\.venv\\Scripts\\Activate.ps1`

4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `python main.py`

## Build a Windows EXE

Run `build_windows.bat`. The standalone folder will be produced under `dist\\PARYAS-AutoCrop\\`.

## Notes

- Face detection is a crop aid, not identity verification. Check every crop before using it for official documents.
- Face detection uses OpenCV's local Haar cascade, so first run does not need an online model download.
- Enhancement improves visible sharpness and tone but cannot recreate information that was never captured.
- JPEG size targeting is approximate. The application keeps the requested pixel dimensions rather than silently downscaling official photos.
