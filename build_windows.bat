@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name PARYAS-AutoCrop --collect-all cv2 --collect-all PySide6 main.py
echo Build finished. Check the dist\PARYAS-AutoCrop folder.
pause
