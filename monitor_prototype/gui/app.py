import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir, QFile
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())