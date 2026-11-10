from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps


@dataclass
class ProcessOptions:
    width: int = 480
    height: int = 672
    dpi: int = 300
    face_aware: bool = True
    brightness: float = 1.0
    contrast: float = 1.04
    sharpness: float = 1.25
    quality: int = 94


@dataclass
class ProcessResult:
    image: Image.Image
    face_found: bool
    note: str


def detect_face(image: Image.Image) -> Optional[tuple[int, int, int, int]]:
    rgb = np.asarray(image.convert('RGB'))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    path = Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml'
    cascade = cv2.CascadeClassifier(str(path))
    if cascade.empty():
        raise RuntimeError('OpenCV face detector could not be loaded.')
    min_side = max(32, min(image.size) // 12)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                     minSize=(min_side, min_side),
                                     flags=cv2.CASCADE_SCALE_IMAGE)
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))
    return int(x), int(y), int(w), int(h)


def _crop_portrait(image: Image.Image, width: int, height: int,
                   face: Optional[tuple[int, int, int, int]]) -> Image.Image:
    sw, sh = image.size
    ratio = width / height
    if sw / sh > ratio:
        crop_h, crop_w = sh, int(round(sh * ratio))
    else:
        crop_w, crop_h = sw, int(round(sw / ratio))
    if face:
        x, y, fw, fh = face
        cx = x + fw / 2
        cy = y + fh * 0.58 + crop_h * 0.12
    else:
        cx, cy = sw / 2, sh / 2
    left = max(0, min(int(round(cx - crop_w / 2)), sw - crop_w))
    top = max(0, min(int(round(cy - crop_h / 2)), sh - crop_h))
    return image.crop((left, top, left + crop_w, top + crop_h))


def process_image(source: str | Path, options: ProcessOptions) -> ProcessResult:
    with Image.open(source) as raw:
        image = ImageOps.exif_transpose(raw).convert('RGB')
    face = detect_face(image) if options.face_aware else None
    cropped = _crop_portrait(image, options.width, options.height, face)
    output = cropped.resize((options.width, options.height), Image.Resampling.LANCZOS)
    output = ImageEnhance.Brightness(output).enhance(options.brightness)
    output = ImageEnhance.Contrast(output).enhance(options.contrast)
    output = ImageEnhance.Sharpness(output).enhance(options.sharpness)
    note = 'Face detected — face-aware crop.' if face else ('No face detected — centered crop used; please review.' if options.face_aware else 'Centered crop used.')
    return ProcessResult(output, face is not None, note)


def save_jpeg(image: Image.Image, path: str | Path, quality: int = 94,
              max_kb: int = 0, dpi: int = 300) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    working = image.convert('RGB')
    q = max(35, min(100, int(quality)))
    target = int(max_kb * 1024) if max_kb > 0 else 0
    for _ in range(12):
        working.save(path, 'JPEG', quality=q, optimize=True, progressive=True, dpi=(dpi, dpi))
        size = path.stat().st_size
        if not target or size <= target or q <= 35:
            return size
        q = max(35, q - 6)
    return path.stat().st_size
