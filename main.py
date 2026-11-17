
import sys

from PySide6.QtWidgets import QApplication

from ui import HeliosWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Helios")
    app.setOrganizationName("Helios")

    window = HeliosWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
