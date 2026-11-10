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
    white_background: bool = False
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
    """Return the largest face as x, y, width, height in source coordinates."""
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        raise RuntimeError("OpenCV face detector could not be loaded.")
    min_side = max(32, min(image.size) // 12)
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(min_side, min_side), flags=cv2.CASCADE_SCALE_IMAGE
    )
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))
    return int(x), int(y), int(w), int(h)


def _replace_background_white(image: Image.Image,
                              face: tuple[int, int, int, int]) -> tuple[Image.Image, bool]:
    """Attempt single-person foreground extraction using OpenCV GrabCut."""
    width, height = image.size
    x, y, face_w, face_h = face

    # Approximate a head-and-shoulders region around the detected face.
    left = max(0, int(x - 1.8 * face_w))
    right = min(width, int(x + 2.8 * face_w))
    top = max(0, int(y - 0.55 * face_h))
    bottom = min(height, int(y + 8.0 * face_h))
    rect_w, rect_h = right - left, bottom - top

    # Very tight portraits leave too little known background for reliable GrabCut.
    if rect_w < 40 or rect_h < 40 or rect_w >= width * 0.96:
        return image, False

    rgb = np.asarray(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.zeros((height, width), dtype=np.uint8)
    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)

    try:
        cv2.grabCut(
            bgr, mask, (left, top, rect_w, rect_h),
            background_model, foreground_model, 5, cv2.GC_INIT_WITH_RECT
        )
        foreground = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        foreground = cv2.morphologyEx(
            foreground, cv2.MORPH_CLOSE,
            np.ones((5, 5), dtype=np.uint8), iterations=1
        )
        foreground = cv2.GaussianBlur(foreground, (5, 5), 0)
        alpha = foreground.astype(np.float32)[..., None] / 255.0
        white = np.full_like(rgb, 255, dtype=np.uint8)
        composite = (rgb.astype(np.float32) * alpha +
                     white.astype(np.float32) * (1.0 - alpha))
        return Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)), True
    except cv2.error:
        return image, False


def _crop_portrait(image: Image.Image, width: int, height: int,
                   face: Optional[tuple[int, int, int, int]]) -> Image.Image:
    """Crop to target aspect ratio, positioning a detected face toward the upper area."""
    source_w, source_h = image.size
    ratio = width / height
    if source_w / source_h > ratio:
        crop_h, crop_w = source_h, int(round(source_h * ratio))
    else:
        crop_w, crop_h = source_w, int(round(source_w / ratio))

    if face:
        x, y, face_w, face_h = face
        center_x = x + face_w / 2
        center_y = y + face_h * 0.58 + crop_h * 0.12
    else:
        center_x, center_y = source_w / 2, source_h / 2

    left = max(0, min(int(round(center_x - crop_w / 2)), source_w - crop_w))
    top = max(0, min(int(round(center_y - crop_h / 2)), source_h - crop_h))
    return image.crop((left, top, left + crop_w, top + crop_h))


def process_image(source: str | Path, options: ProcessOptions) -> ProcessResult:
    with Image.open(source) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")

    face = detect_face(image) if options.face_aware or options.white_background else None
    background_note = ""
    if options.white_background:
        if face:
            image, applied = _replace_background_white(image, face)
            background_note = (
                "White background attempted — review hair and shoulder edges."
                if applied else
                "White background skipped — the portrait was too tightly framed."
            )
        else:
            background_note = "White background skipped — no face was detected."

    crop_face = face if options.face_aware else None
    cropped = _crop_portrait(image, options.width, options.height, crop_face)
    output = cropped.resize((options.width, options.height), Image.Resampling.LANCZOS)
    output = ImageEnhance.Brightness(output).enhance(options.brightness)
    output = ImageEnhance.Contrast(output).enhance(options.contrast)
    output = ImageEnhance.Sharpness(output).enhance(options.sharpness)

    if face and options.face_aware:
        crop_note = "Face detected — face-aware crop."
    elif options.face_aware:
        crop_note = "No face detected — centered crop used; please review."
    else:
        crop_note = "Centered crop used."
    note = crop_note if not background_note else crop_note + " " + background_note
    return ProcessResult(output, face is not None, note)


def save_jpeg(image: Image.Image, path: str | Path, quality: int = 94,
              max_kb: int = 0, dpi: int = 300) -> int:
    """Save JPEG and lower quality to approach an optional KB ceiling."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    working = image.convert("RGB")
    current_quality = max(35, min(100, int(quality)))
    target_bytes = int(max_kb * 1024) if max_kb > 0 else 0

    for _ in range(12):
        working.save(path, "JPEG", quality=current_quality, optimize=True,
                     progressive=True, dpi=(dpi, dpi))
        size = path.stat().st_size
        if not target_bytes or size <= target_bytes or current_quality <= 35:
            return size
        current_quality = max(35, current_quality - 6)
    return path.stat().st_size
