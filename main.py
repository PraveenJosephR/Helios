
import sys
import json
import re
import urllib.request
import urllib.error
import threading
import psutil
import keyboard

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QKeySequenceEdit, QMessageBox, QProgressBar, QScrollArea
)


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "Helios"
API_URL = "http://localhost:8085/data.json"

UPDATE_INTERVAL = 2000
DEFAULT_SHORTCUT = "F11"

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #111827;
    color: #e5e7eb;
    font-family: "Segoe UI";
    font-size: 14px;
}

QFrame#card {
    background-color: #1f2937;
    border: 1px solid #374151;
    border-radius: 12px;
}

QFrame#driveCard {
    background-color: #1f2937;
    border: 1px solid #374151;
    border-radius: 9px;
}

QLabel#heading {
    color: #9ca3af;
    font-size: 13px;
}

QLabel#value {
    color: #ffffff;
    font-size: 29px;
    font-weight: bold;
}

QLabel#sectionTitle {
    font-size: 19px;
    font-weight: bold;
}

QLabel#subtitle {
    color: #9ca3af;
    font-size: 13px;
}

QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 9px 15px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton#secondary {
    background-color: #374151;
}

QPushButton#secondary:hover {
    background-color: #4b5563;
}

QKeySequenceEdit {
    background-color: #374151;
    color: white;
    border: 1px solid #4b5563;
    border-radius: 6px;
    padding: 7px;
}

QProgressBar {
    background-color: #374151;
    border: none;
    border-radius: 4px;
    height: 7px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 4px;
}

QScrollArea {
    border: none;
}

QScrollBar:vertical {
    background: #1f2937;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #4b5563;
    border-radius: 4px;
}
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f3f4f6;
    color: #111827;
    font-family: "Segoe UI";
    font-size: 14px;
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 12px;
}

QFrame#driveCard {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 9px;
}

QLabel#heading {
    color: #6b7280;
    font-size: 13px;
}

QLabel#value {
    color: #111827;
    font-size: 29px;
    font-weight: bold;
}

QLabel#sectionTitle {
    font-size: 19px;
    font-weight: bold;
}

QLabel#subtitle {
    color: #6b7280;
    font-size: 13px;
}

QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 9px 15px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton#secondary {
    background-color: #e5e7eb;
    color: #111827;
}

QPushButton#secondary:hover {
    background-color: #d1d5db;
}

QKeySequenceEdit {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 7px;
}

QProgressBar {
    background-color: #e5e7eb;
    border: none;
    border-radius: 4px;
    height: 7px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

QScrollArea {
    border: none;
}

QScrollBar:vertical {
    background: #f3f4f6;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #9ca3af;
    border-radius: 4px;
}
"""


# ============================================================
# HARDWARE MONITOR
# ============================================================

class HardwareMonitor:

    def __init__(self):
        self.previous_data = None

    @staticmethod
    def number(value):

        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            pass

        match = re.search(
            r"-?\d+(?:\.\d+)?",
            str(value).replace(",", "")
        )

        if match:
            try:
                return float(match.group())
            except ValueError:
                pass

        return None

    def fetch_data(self):

        request = urllib.request.Request(
            API_URL,
            headers={"Cache-Control": "no-cache"}
        )

        with urllib.request.urlopen(
            request, timeout=3
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    @staticmethod
    def infer_sensor_type(node):

        sensor_type = node.get("Type")

        if sensor_type:
            return str(sensor_type)

        sensor_id = str(node.get("id", "")).lower()

        types = [
            "temperature",
            "load",
            "clock",
            "fan",
            "voltage",
            "power",
            "data",
            "smallData",
            "factor",
            "level",
            "flow"
        ]

        for sensor in types:

            if re.search(
                r"/" + re.escape(sensor.lower()) + r"/",
                sensor_id
            ):
                return sensor

        return None

    @staticmethod
    def collect_sensors(node, hardware=None, output=None):

        if output is None:
            output = []

        if hardware is None:
            hardware = "Unknown"

        children = node.get("Children", [])
        sensor_type = HardwareMonitor.infer_sensor_type(node)

        if sensor_type:

            value = HardwareMonitor.number(
                node.get("RawValue")
            )

            if value is None:
                value = HardwareMonitor.number(
                    node.get("Value")
                )

            if value is not None:

                output.append({
                    "hardware": hardware,
                    "name": str(node.get("Text", "Unknown")),
                    "type": sensor_type,
                    "value": value,
                    "id": str(node.get("id", ""))
                })

        else:

            node_id = str(node.get("id", "")).lower()

            category_node = any(
                f"/{category}" in node_id
                for category in [
                    "/temperature",
                    "/load",
                    "/clock",
                    "/fan",
                    "/voltage",
                    "/power",
                    "/data",
                    "/smalldata",
                    "/factor",
                    "/level"
                ]
            )

            if children and not category_node:
                hardware = str(
                    node.get("Text", hardware)
                )

        for child in children:

            HardwareMonitor.collect_sensors(
                child,
                hardware,
                output
            )

        return output

    @staticmethod
    def matches_hardware(sensor, keywords):

        combined = (
            sensor["hardware"] + " " + sensor["id"]
        ).lower()

        return any(
            keyword.lower() in combined
            for keyword in keywords
        )

    @staticmethod
    def find_sensors(sensors, hardware_keywords, sensor_type):

        return [
            sensor for sensor in sensors
            if sensor["type"].lower() == sensor_type.lower()
            and HardwareMonitor.matches_hardware(
                sensor, hardware_keywords
            )
        ]

    def get_cpu_temperature(self, sensors):

        matches = self.find_sensors(
            sensors,
            ["ryzen", "amdcpu", "amd cpu", "cpu"],
            "Temperature"
        )

        priorities = [
            "tctl/tdie",
            "tdie",
            "cpu package",
            "cpu die",
            "cpu"
        ]

        for preferred in priorities:

            for sensor in matches:

                if preferred in sensor["name"].lower():
                    return sensor["value"]

        return matches[0]["value"] if matches else None

    def get_gpu_temperature(self, sensors):

        matches = self.find_sensors(
            sensors,
            ["nvidia", "geforce", "gpu-nvidia"],
            "Temperature"
        )

        for sensor in matches:

            if "gpu core" in sensor["name"].lower():
                return sensor["value"]

        return matches[0]["value"] if matches else None

    def get_gpu_usage(self, sensors):

        matches = self.find_sensors(
            sensors,
            ["nvidia", "geforce", "gpu-nvidia"],
            "Load"
        )

        for sensor in matches:

            if "gpu core" in sensor["name"].lower():
                return sensor["value"]

        return matches[0]["value"] if matches else None

    def get_drive_temperatures(self, sensors):

        results = []

        storage_keywords = [
            "nvme",
            "ssd",
            "hdd",
            "storage",
            "drive",
            "samsung",
            "western digital",
            "seagate",
            "kingston",
            "crucial",
            "solidigm",
            "toshiba",
            "sandisk",
            "wdc"
        ]

        for sensor in sensors:

            if sensor["type"].lower() != "temperature":
                continue

            if self.matches_hardware(
                sensor, storage_keywords
            ):

                results.append({
                    "hardware": sensor["hardware"],
                    "name": sensor["name"],
                    "temperature": sensor["value"]
                })

        return results

    def get_data(self):

        try:
            raw_data = self.fetch_data()

        except Exception as error:

            raise RuntimeError(
                "Cannot connect to LibreHardwareMonitor.\n\n"
                "Make sure LibreHardwareMonitor is running "
                "and Remote Web Server is enabled on port 8085.\n\n"
                f"Details: {error}"
            ) from error

        sensors = self.collect_sensors(raw_data)

        cpu_usage = psutil.cpu_percent(interval=None)

        ram = psutil.virtual_memory()

        drives = []

        for partition in psutil.disk_partitions(all=False):

            try:

                usage = psutil.disk_usage(
                    partition.mountpoint
                )

                drives.append({
                    "name": partition.device,
                    "mount": partition.mountpoint,
                    "used": usage.percent,
                    "total": usage.total / (1024 ** 3),
                    "free": usage.free / (1024 ** 3)
                })

            except (PermissionError, OSError):
                continue

        result = {
            "cpu_usage": cpu_usage,
            "cpu_temp": self.get_cpu_temperature(sensors),

            "gpu_usage": self.get_gpu_usage(sensors),
            "gpu_temp": self.get_gpu_temperature(sensors),

            "ram_usage": ram.percent,
            "ram_used": ram.used / (1024 ** 3),
            "ram_total": ram.total / (1024 ** 3),

            "drives": drives,
            "drive_temps": self.get_drive_temperatures(
                sensors
            )
        }

        self.previous_data = result

        return result


# ============================================================
# BACKGROUND HARDWARE WORKER
# ============================================================

class HardwareWorker(QThread):

    data_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()

        self.monitor = HardwareMonitor()
        self.stop_event = threading.Event()

    def run(self):

        while not self.stop_event.is_set():

            try:

                data = self.monitor.get_data()
                self.data_ready.emit(data)

            except Exception as error:

                self.error_occurred.emit(str(error))

            self.stop_event.wait(
                UPDATE_INTERVAL / 1000
            )

    def stop(self):

        self.stop_event.set()
        self.wait(5000)


# ============================================================
# GAMING OVERLAY
# ============================================================

class Overlay(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self.setFixedWidth(330)

        self.setStyleSheet("""
            QFrame#overlayPanel {
                background-color: rgba(12, 16, 25, 225);
                border: 1px solid rgba(255,255,255,45);
                border-radius: 12px;
            }

            QLabel {
                color: white;
                background: transparent;
                border: none;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#overlayTitle {
                font-size: 11px;
                color: #9ca3af;
                font-weight: bold;
            }

            QLabel#overlayValue {
                font-size: 16px;
                font-weight: bold;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.panel = QFrame()
        self.panel.setObjectName("overlayPanel")

        self.layout_panel = QVBoxLayout(self.panel)
        self.layout_panel.setContentsMargins(15, 12, 15, 12)
        self.layout_panel.setSpacing(8)

        title = QLabel("HELIOS  |  SYSTEM TEMPERATURES")
        title.setObjectName("overlayTitle")

        self.layout_panel.addWidget(title)

        self.cpu_label = QLabel("CPU       -- °C")
        self.gpu_label = QLabel("GPU       -- °C")
        self.drive_label = QLabel("DRIVES    --")

        for label in [
            self.cpu_label,
            self.gpu_label,
            self.drive_label
        ]:

            label.setObjectName("overlayValue")
            self.layout_panel.addWidget(label)

        outer.addWidget(self.panel)

        self.position_overlay()

    def position_overlay(self):

        screen = QApplication.primaryScreen()

        if screen is None:
            return

        geometry = screen.availableGeometry()

        self.adjustSize()

        self.move(
            geometry.right() - self.width() - 15,
            geometry.top() + 15
        )

    def update_data(self, data):

        cpu = data.get("cpu_temp")
        gpu = data.get("gpu_temp")

        cpu_text = (
            f"{cpu:.1f} °C" if cpu is not None else "N/A"
        )

        gpu_text = (
            f"{gpu:.1f} °C" if gpu is not None else "N/A"
        )

        self.cpu_label.setText(
            f"CPU       {cpu_text}"
        )

        self.gpu_label.setText(
            f"GPU       {gpu_text}"
        )

        drive_temps = data.get("drive_temps", [])

        if drive_temps:

            lines = []

            for drive in drive_temps:

                name = drive["hardware"]

                if name == "Unknown":
                    name = drive["name"]

                lines.append(
                    f"{name}: {drive['temperature']:.1f} °C"
                )

            self.drive_label.setText(
                "DRIVES\n" + "\n".join(lines)
            )

        else:

            self.drive_label.setText(
                "DRIVES    N/A"
            )

        self.adjustSize()
        self.position_overlay()


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    hotkey_signal = Signal()

    def __init__(self):

        super().__init__()

        self.settings = QSettings(
            "Helios",
            "HardwareMonitor"
        )

        self.dark_mode = self.settings.value(
            "dark_mode", True, type=bool
        )

        self.shortcut = self.settings.value(
            "shortcut", DEFAULT_SHORTCUT
        )

        self.hotkey_registered = False

        self.overlay = Overlay()

        self.cards = {}
        self.drive_widgets = []

        self.setWindowTitle("Helios - Hardware Monitor")
        self.setMinimumSize(850, 700)
        self.resize(950, 800)

        self.create_ui()
        self.apply_theme()

        self.hotkey_signal.connect(
            self.toggle_overlay
        )

        self.register_hotkey(self.shortcut)

        self.worker = HardwareWorker()
        self.worker.data_ready.connect(
            self.refresh_ui
        )
        self.worker.error_occurred.connect(
            self.show_error
        )

        self.worker.start()

    # --------------------------------------------------------
    # UI CREATION
    # --------------------------------------------------------

    def create_card(self, title, key):

        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 17, 18, 17)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setObjectName("heading")

        value = QLabel("--")
        value.setObjectName("value")

        details = QLabel("Waiting for readings...")
        details.setObjectName("subtitle")

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)

        layout.addWidget(heading)
        layout.addWidget(value)
        layout.addWidget(details)
        layout.addWidget(progress)

        self.cards[key] = {
            "value": value,
            "details": details,
            "progress": progress
        }

        return card

    def create_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)
        main.setContentsMargins(25, 22, 25, 22)
        main.setSpacing(17)

        # HEADER

        header = QHBoxLayout()

        title = QLabel("Helios")
        title.setStyleSheet(
            "font-size: 29px; font-weight: bold;"
        )

        self.theme_button = QPushButton()
        self.theme_button.setFixedWidth(125)
        self.theme_button.clicked.connect(
            self.toggle_theme
        )

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.theme_button)

        main.addLayout(header)

        subtitle = QLabel(
            "Real-time hardware monitoring"
        )
        subtitle.setObjectName("subtitle")

        main.addWidget(subtitle)

        # HARDWARE CARDS

        grid = QGridLayout()
        grid.setSpacing(14)

        grid.addWidget(
            self.create_card("PROCESSOR", "cpu"),
            0, 0
        )

        grid.addWidget(
            self.create_card("GRAPHICS CARD", "gpu"),
            0, 1
        )

        grid.addWidget(
            self.create_card("MEMORY", "ram"),
            1, 0, 1, 2
        )

        main.addLayout(grid)

        # STORAGE SECTION

        storage_title = QLabel("Storage Drives")
        storage_title.setObjectName("sectionTitle")

        main.addWidget(storage_title)

        self.drive_layout = QVBoxLayout()
        self.drive_layout.setSpacing(9)

        main.addLayout(self.drive_layout)

        # OVERLAY SECTION

        overlay_title = QLabel("Gaming Overlay")
        overlay_title.setObjectName("sectionTitle")

        main.addWidget(overlay_title)

        overlay_controls = QHBoxLayout()

        self.overlay_button = QPushButton(
            "Show Overlay"
        )

        self.overlay_button.clicked.connect(
            self.toggle_overlay
        )

        overlay_controls.addWidget(self.overlay_button)
        overlay_controls.addStretch()

        main.addLayout(overlay_controls)

        # SHORTCUT

        shortcut_frame = QFrame()
        shortcut_frame.setObjectName("card")

        shortcut_layout = QVBoxLayout(shortcut_frame)
        shortcut_layout.setContentsMargins(15, 13, 15, 13)

        shortcut_title = QLabel("Overlay Shortcut")
        shortcut_title.setObjectName("heading")

        shortcut_row = QHBoxLayout()

        self.shortcut_input = QKeySequenceEdit()
        self.shortcut_input.setKeySequence(
            QKeySequence(self.shortcut)
        )

        save_button = QPushButton("Save Shortcut")
        save_button.clicked.connect(
            self.save_shortcut
        )

        shortcut_row.addWidget(self.shortcut_input)
        shortcut_row.addWidget(save_button)

        shortcut_layout.addWidget(shortcut_title)
        shortcut_layout.addLayout(shortcut_row)

        main.addWidget(shortcut_frame)

        self.status_label = QLabel(
            "Connecting to LibreHardwareMonitor..."
        )
        self.status_label.setObjectName("subtitle")

        main.addWidget(self.status_label)

        main.addStretch()

    # --------------------------------------------------------
    # THEME
    # --------------------------------------------------------

    def apply_theme(self):

        if self.dark_mode:

            self.setStyleSheet(DARK_STYLE)
            self.theme_button.setText("☀  Light Mode")

        else:

            self.setStyleSheet(LIGHT_STYLE)
            self.theme_button.setText("☾  Dark Mode")

        self.settings.setValue(
            "dark_mode", self.dark_mode
        )

    def toggle_theme(self):

        self.dark_mode = not self.dark_mode
        self.apply_theme()

    # --------------------------------------------------------
    # GLOBAL SHORTCUT
    # --------------------------------------------------------

    @staticmethod
    def normalize_shortcut(shortcut):

        return (
            shortcut.lower()
            .replace("control+", "ctrl+")
            .replace(" ", "")
        )

    def register_hotkey(self, shortcut):

        normalized = self.normalize_shortcut(shortcut)

        try:

            keyboard.add_hotkey(
                normalized,
                self.hotkey_signal.emit,
                suppress=False
            )

            self.hotkey_registered = True
            self.shortcut = shortcut

            self.settings.setValue(
                "shortcut", shortcut
            )

            return True

        except Exception as error:

            QMessageBox.warning(
                self,
                "Shortcut Error",
                f"Could not register shortcut:\n\n{error}"
            )

            return False

    def save_shortcut(self):

        sequence = self.shortcut_input.keySequence()

        shortcut = sequence.toString(
            QKeySequence.SequenceFormat.PortableText
        )

        if not shortcut:

            QMessageBox.warning(
                self,
                "Invalid Shortcut",
                "Please enter a valid keyboard shortcut."
            )

            return

        old_shortcut = self.shortcut

        if self.hotkey_registered:

            try:
                keyboard.remove_hotkey(
                    self.normalize_shortcut(old_shortcut)
                )
                self.hotkey_registered = False

            except Exception:
                pass

        if self.register_hotkey(shortcut):

            self.status_label.setText(
                f"Overlay shortcut: {shortcut}"
            )

        else:

            self.register_hotkey(old_shortcut)

            self.shortcut_input.setKeySequence(
                QKeySequence(old_shortcut)
            )

    # --------------------------------------------------------
    # OVERLAY
    # --------------------------------------------------------

    def toggle_overlay(self):

        if self.overlay.isVisible():

            self.overlay.hide()
            self.overlay_button.setText("Show Overlay")

        else:

            self.overlay.show()
            self.overlay_button.setText("Hide Overlay")

    # --------------------------------------------------------
    # STORAGE UI
    # --------------------------------------------------------

    def clear_drives(self):

        while self.drive_layout.count():

            item = self.drive_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    def update_drives(self, data):

        self.clear_drives()

        drive_temps = data.get("drive_temps", [])

        for drive in data.get("drives", []):

            name = drive["name"]
            mount = drive["mount"]

            card = QFrame()
            card.setObjectName("driveCard")

            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 11, 14, 11)
            layout.setSpacing(6)

            top = QHBoxLayout()

            drive_name = QLabel(
                f"{name}  ({mount})"
            )

            drive_name.setStyleSheet(
                "font-weight: bold;"
            )

            usage = QLabel(
                f"{drive['used']:.1f}% used"
            )

            top.addWidget(drive_name)
            top.addStretch()
            top.addWidget(usage)

            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(
                int(drive["used"])
            )
            progress.setTextVisible(False)

            details = QLabel(
                f"{drive['free']:.1f} GB free  /  "
                f"{drive['total']:.1f} GB total"
            )
            details.setObjectName("subtitle")

            layout.addLayout(top)
            layout.addWidget(progress)
            layout.addWidget(details)

            self.drive_layout.addWidget(card)

        # Physical drive SMART temperatures

        for drive in drive_temps:

            card = QFrame()
            card.setObjectName("driveCard")

            layout = QHBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)

            name = QLabel(
                f"{drive['hardware']} - {drive['name']}"
            )

            name.setStyleSheet(
                "font-weight: bold;"
            )

            temperature = QLabel(
                f"{drive['temperature']:.1f} °C"
            )

            temperature.setStyleSheet(
                "font-size: 16px; font-weight: bold;"
            )

            layout.addWidget(name)
            layout.addStretch()
            layout.addWidget(temperature)

            self.drive_layout.addWidget(card)

    # --------------------------------------------------------
    # DATA REFRESH
    # --------------------------------------------------------

    @staticmethod
    def display(value, suffix=""):

        if value is None:
            return "N/A"

        return f"{value:.1f}{suffix}"

    def update_card(
        self, key, value, details, progress=None
    ):

        card = self.cards[key]

        card["value"].setText(value)
        card["details"].setText(details)

        if progress is not None:

            card["progress"].setValue(
                max(0, min(100, int(progress)))
            )

    def refresh_ui(self, data):

        self.update_card(
            "cpu",
            self.display(data["cpu_temp"], " °C"),
            f"Usage: {self.display(data['cpu_usage'], '%')}",
            data["cpu_usage"]
        )

        self.update_card(
            "gpu",
            self.display(data["gpu_temp"], " °C"),
            f"Usage: {self.display(data['gpu_usage'], '%')}",
            data["gpu_usage"]
        )

        self.update_card(
            "ram",
            self.display(data["ram_usage"], "%"),
            (
                f"{data['ram_used']:.1f} GB used / "
                f"{data['ram_total']:.1f} GB total"
            ),
            data["ram_usage"]
        )

        self.update_drives(data)

        self.overlay.update_data(data)

        self.status_label.setText(
            "Monitoring active  |  "
            "Refresh interval: 2 seconds"
        )

    def show_error(self, error):

        self.status_label.setText(
            "Hardware monitoring connection error"
        )

        self.cards["cpu"]["details"].setText(
            "Waiting for sensor data..."
        )

        self.cards["gpu"]["details"].setText(
            "Waiting for sensor data..."
        )

        self.cards["ram"]["details"].setText(
            "Waiting for sensor data..."
        )

        # Keep the last valid readings visible.
        self.status_label.setToolTip(error)

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    def closeEvent(self, event):

        self.overlay.hide()

        if hasattr(self, "worker"):
            self.worker.stop()

        if self.hotkey_registered:

            try:
                keyboard.remove_hotkey(
                    self.normalize_shortcut(self.shortcut)
                )

            except Exception:
                pass

        keyboard.unhook_all()

        event.accept()


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
