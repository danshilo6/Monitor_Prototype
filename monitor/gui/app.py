import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir, QFile
from PySide6.QtGui import QIcon
from monitor.gui.main_window import MainWindow
from pathlib import Path


def set_app_icon(app: QApplication) -> None:
    icon_path = Path(__file__).parent / "icons" / "ecg-monitor.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))



if __name__ == "__main__":
    app = QApplication(sys.argv)

    set_app_icon(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

