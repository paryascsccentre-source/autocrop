from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from autocrop_studio.ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('PARYAS AutoCrop Studio')
    app.setOrganizationName('PARYAS CSC Centre')
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
