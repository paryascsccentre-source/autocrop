from pathlib import Path

from PIL import Image

from autocrop_studio.processor import ProcessOptions, process_image, save_jpeg


def test_process_image_outputs_requested_dimensions(tmp_path: Path):
    source = tmp_path / "source.png"
    Image.new("RGB", (1200, 1600), (125, 145, 165)).save(source)

    result = process_image(
        source,
        ProcessOptions(width=413, height=531, face_aware=False, white_background=False),
    )

    assert result.image.size == (413, 531)
    assert result.face_found is False


def test_white_background_skips_cleanly_without_detected_face(tmp_path: Path):
    source = tmp_path / "plain.png"
    Image.new("RGB", (600, 800), (128, 128, 128)).save(source)

    result = process_image(
        source,
        ProcessOptions(width=120, height=160, face_aware=False, white_background=True),
    )

    assert result.image.size == (120, 160)
    assert "no face was detected" in result.note.lower()


def test_save_jpeg_writes_readable_file(tmp_path: Path):
    target = tmp_path / "output.jpg"
    image = Image.new("RGB", (120, 160), (220, 210, 200))

    reported_size = save_jpeg(image, target, quality=90, max_kb=0)

    assert target.exists()
    assert reported_size == target.stat().st_size
    with Image.open(target) as saved:
        assert saved.format == "JPEG"
        assert saved.size == (120, 160)
