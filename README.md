# PARYAS AutoCrop Studio

A local-first Windows desktop photo utility for automatic portrait cropping, natural enhancement, batch processing, and export.

## Features

- Import JPG, JPEG, PNG, BMP, TIFF, and WebP photos.
- Face-aware crop using OpenCV's bundled Haar cascade, with a centered fallback when no face is found.
- Presets for 35 x 45 mm (413 x 531 px at 300 DPI), 480 x 672 px, 86 x 54 mm (1016 x 638 px at 300 DPI), and custom pixel dimensions.
- Adjustable brightness, contrast, and sharpening.
- Optional experimental white-background cut-out using OpenCV GrabCut. Results depend on the image and must be checked around hair and shoulders.
- Before/after crop preview and batch JPEG export.
- Optional maximum JPEG size target. The app reduces JPEG quality first and does not silently resize official-photo dimensions; check the reported file size if the target cannot be reached.
- All image processing happens locally; photos are not uploaded.

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

- Face detection is a crop aid, not identity verification. Check every crop before submitting an official document.
- Haar-cascade face detection uses a local OpenCV model; first launch does not need an online model download.
- Background cut-out is an experimental classical segmentation method, not a perfect AI portrait matting model. If it damages hair or clothing edges, turn the option off and use a clean-background original photo.
- Enhancement improves visible sharpness and tone but cannot recreate detail that was never captured.
