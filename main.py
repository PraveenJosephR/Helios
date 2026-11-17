
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from ui import HeliosWindow


def resource_path(filename):
    """Find bundled resources in both Python and PyInstaller."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, filename)


def main():
    app = QApplication(sys.argv)

    icon = QIcon(resource_path("app.ico"))

    app.setWindowIcon(icon)
    app.setApplicationName("Helios")
    app.setOrganizationName("Helios")

    window = HeliosWindow()
    window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()


# python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name Helios --icon=app.ico --add-data "app.ico;." main.py