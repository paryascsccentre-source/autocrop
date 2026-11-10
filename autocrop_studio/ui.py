from __future__ import annotations

from pathlib import Path

from PIL import ImageQt
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QStatusBar, QVBoxLayout,
    QWidget, QListWidget, QListWidgetItem
)

from .processor import ProcessOptions, process_image, save_jpeg


PRESETS = {
    "Passport 35 x 45 mm (413 x 531 px @ 300 DPI)": (413, 531),
    "480 x 672 px": (480, 672),
    "86 x 54 mm (1016 x 638 px @ 300 DPI)": (1016, 638),
    "Custom dimensions": (480, 672),
}


class Worker(QThread):
    progress = Signal(int, int, str)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, files, output, options, max_kb):
        super().__init__()
        self.files, self.output = files, output
        self.options, self.max_kb = options, max_kb

    def run(self):
        try:
            results = []
            for index, filename in enumerate(self.files, 1):
                result = process_image(filename, self.options)
                target = Path(self.output) / (Path(filename).stem + "_autocrop.jpg")
                size = save_jpeg(
                    result.image, target, self.options.quality,
                    self.max_kb, self.options.dpi
                )
                results.append((str(target), result.note, size))
                self.progress.emit(index, len(self.files), Path(filename).name)
            self.completed.emit(results)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PARYAS AutoCrop Studio")
        self.resize(1180, 760)
        self.setMinimumSize(920, 620)
        self.files = []
        self.current_preview = None
        self.worker = None
        self.output_dir = str(Path.home() / "Pictures" / "PARYAS AutoCrop")
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("PARYAS <span style='color:#58d6c0'>AutoCrop</span> Studio")
        title.setTextFormat(Qt.RichText)
        title.setObjectName("title")
        subtitle = QLabel("LOCAL PHOTO CROPPING  •  NATURAL ENHANCEMENT  •  BATCH EXPORT")
        subtitle.setObjectName("subtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.add_button = QPushButton("＋  Add Photos")
        self.add_button.clicked.connect(self.add_files)
        header.addWidget(self.add_button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        files_group = QGroupBox("PHOTO QUEUE")
        files_layout = QVBoxLayout(files_group)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.currentRowChanged.connect(self.preview_selected)
        files_layout.addWidget(self.file_list, 1)
        buttons = QHBoxLayout()
        remove = QPushButton("Remove selected")
        remove.clicked.connect(self.remove_selected)
        clear = QPushButton("Clear all")
        clear.clicked.connect(self.clear_files)
        buttons.addWidget(remove)
        buttons.addWidget(clear)
        files_layout.addLayout(buttons)
        left_layout.addWidget(files_group, 1)

        settings = QGroupBox("CROP & EXPORT SETTINGS")
        form = QFormLayout(settings)
        self.preset = QComboBox()
        self.preset.addItems(PRESETS.keys())
        self.preset.currentTextChanged.connect(self.preset_changed)
        form.addRow("Photo preset", self.preset)

        dimensions = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 6000)
        self.width_spin.setValue(413)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 6000)
        self.height_spin.setValue(531)
        dimensions.addWidget(self.width_spin)
        dimensions.addWidget(QLabel("×"))
        dimensions.addWidget(self.height_spin)
        form.addRow("Pixels (W × H)", dimensions)

        self.face_check = QCheckBox("Face-aware automatic crop")
        self.face_check.setChecked(True)
        form.addRow(self.face_check)
        self.white_check = QCheckBox("Try white background removal (review result)")
        self.white_check.setChecked(False)
        self.white_check.setToolTip(
            "Experimental single-person GrabCut cut-out. Best with a clear, "
            "well-lit head-and-shoulders photo and a contrasting background."
        )
        form.addRow(self.white_check)

        self.brightness = self._double(1.0, 0.5, 1.8)
        self.contrast = self._double(1.04, 0.5, 1.8)
        self.sharpness = self._double(1.25, 0.0, 3.0)
        form.addRow("Brightness", self.brightness)
        form.addRow("Contrast", self.contrast)
        form.addRow("Sharpness", self.sharpness)

        self.max_kb = QSpinBox()
        self.max_kb.setRange(0, 5000)
        self.max_kb.setSpecialValueText("No limit")
        self.max_kb.setValue(300)
        form.addRow("Maximum file size (KB)", self.max_kb)

        self.output_label = QLabel(self.output_dir)
        self.output_label.setWordWrap(True)
        choose = QPushButton("Choose output folder…")
        choose.clicked.connect(self.choose_output)
        form.addRow("Save to", self.output_label)
        form.addRow(choose)
        left_layout.addWidget(settings)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        preview_group = QGroupBox("CROP PREVIEW")
        preview_layout = QVBoxLayout(preview_group)
        self.preview = QLabel("Add a photo to see the automatic crop preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(320, 390)
        self.preview.setObjectName("preview")
        preview_layout.addWidget(self.preview, 1)
        self.preview_note = QLabel("No image selected")
        self.preview_note.setObjectName("muted")
        preview_layout.addWidget(self.preview_note)
        right_layout.addWidget(preview_group, 1)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right_layout.addWidget(self.progress)
        self.status = QLabel("Ready — photos remain on this computer.")
        self.status.setObjectName("muted")
        right_layout.addWidget(self.status)
        self.process_button = QPushButton("Process & Export Photos  →")
        self.process_button.setObjectName("primary")
        self.process_button.clicked.connect(self.start_processing)
        right_layout.addWidget(self.process_button)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([540, 560])
        root.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("PARYAS CSC Centre  |  Offline desktop photo utility")

        menu = self.menuBar().addMenu("File")
        add = QAction("Add Photos…", self)
        add.triggered.connect(self.add_files)
        menu.addAction(add)
        menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    @staticmethod
    def _double(value, low, high):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setSingleStep(0.05)
        spin.setDecimals(2)
        spin.setValue(value)
        return spin

    def _apply_style(self):
        self.setStyleSheet('''
            QMainWindow, QWidget { background:#101820; color:#eaf1f5; font-size:13px; }
            QMenuBar { background:#16232d; color:#eaf1f5; padding:6px; }
            QMenuBar::item:selected, QMenu { background:#20313d; }
            #title { font-size:28px; font-weight:700; color:#fff; }
            #subtitle, #muted { color:#9aabb7; font-size:11px; }
            QGroupBox { border:1px solid #2a3b47; border-radius:12px; margin-top:12px; padding:12px; font-weight:700; color:#8ee3d3; }
            QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; }
            QListWidget, QComboBox, QSpinBox, QDoubleSpinBox { background:#172630; border:1px solid #324653; border-radius:7px; padding:7px; }
            QListWidget::item { padding:8px; border-radius:5px; } QListWidget::item:selected { background:#245b5a; }
            QPushButton { background:#243641; border:1px solid #3b5360; border-radius:8px; padding:9px 12px; color:#eff7fa; }
            QPushButton:hover { background:#31505d; }
            QPushButton#primary { background:#1b8f81; border:0; font-weight:700; padding:14px; font-size:14px; }
            QPushButton#primary:hover { background:#25a898; }
            QLabel#preview { background:#172630; border:1px dashed #47616f; border-radius:10px; }
            QProgressBar { border:1px solid #324653; border-radius:6px; text-align:center; background:#172630; padding:2px; }
            QProgressBar::chunk { background:#1b8f81; border-radius:5px; }
        ''')

    def preset_changed(self, name):
        if name in PRESETS:
            self.width_spin.setValue(PRESETS[name][0])
            self.height_spin.setValue(PRESETS[name][1])

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select photos", str(Path.home()),
            "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)"
        )
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.file_list.addItem(QListWidgetItem(Path(path).name))
        if paths and self.file_list.count():
            self.file_list.setCurrentRow(0)
        self.status.setText(f"{len(self.files)} photo(s) in queue")

    def remove_selected(self):
        rows = sorted(
            {self.file_list.row(item) for item in self.file_list.selectedItems()},
            reverse=True
        )
        for row in rows:
            self.file_list.takeItem(row)
            self.files.pop(row)
        self.status.setText(f"{len(self.files)} photo(s) in queue")

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.current_preview = None
        self.preview.clear()
        self.preview.setText("Add a photo to see the automatic crop preview")
        self.preview_note.setText("No image selected")
        self.status.setText("Queue cleared")

    def _options(self):
        return ProcessOptions(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            face_aware=self.face_check.isChecked(),
            white_background=self.white_check.isChecked(),
            brightness=self.brightness.value(),
            contrast=self.contrast.value(),
            sharpness=self.sharpness.value()
        )

    def preview_selected(self, row):
        if row < 0 or row >= len(self.files):
            return
        try:
            result = process_image(self.files[row], self._options())
            self.current_preview = result.image
            pixmap = QPixmap.fromImage(ImageQt.ImageQt(result.image))
            self.preview.setPixmap(pixmap.scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.preview_note.setText(result.note)
        except Exception as exc:
            self.preview_note.setText(f"Preview error: {exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_preview is not None:
            pixmap = QPixmap.fromImage(ImageQt.ImageQt(self.current_preview))
            self.preview.setPixmap(pixmap.scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choose output folder", self.output_dir
        )
        if path:
            self.output_dir = path
            self.output_label.setText(path)

    def start_processing(self):
        if not self.files:
            QMessageBox.information(
                self, "No photos", "Please add at least one photo first."
            )
            return
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.process_button.setEnabled(False)
        self.add_button.setEnabled(False)
        self.progress.setValue(0)
        self.worker = Worker(
            self.files.copy(), self.output_dir, self._options(), self.max_kb.value()
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, done, total, filename):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status.setText(f"Processing {done}/{total}: {filename}")

    def _finish_worker(self):
        self.process_button.setEnabled(True)
        self.add_button.setEnabled(True)

    def on_completed(self, results):
        self._finish_worker()
        self.status.setText(f"Finished — exported {len(results)} photo(s).")
        self.statusBar().showMessage(f"Saved to {self.output_dir}")
        lines = "\n".join(
            f"{Path(path).name} — {note} — {size / 1024:.0f} KB"
            for path, note, size in results[:12]
        )
        if len(results) > 12:
            lines += f"\n… and {len(results) - 12} more"
        QMessageBox.information(
            self, "Export complete",
            f"Exported {len(results)} photo(s) to:\n{self.output_dir}\n\n{lines}"
        )

    def on_failed(self, message):
        self._finish_worker()
        QMessageBox.critical(self, "Processing error", message)
        self.status.setText("Processing stopped because of an error.")
