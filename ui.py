
import keyboard

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QObject, QSettings
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
)

from monitor import MonitorWorker
from styles import get_stylesheet


class HotkeyBridge(QObject):
    toggle_overlay = Signal()


class TemperatureCard(QFrame):
    def __init__(self, title, accent):
        super().__init__()

        self.setObjectName("temperatureCard")
        self.setMinimumHeight(155)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.temperature_label = QLabel("-- °C")
        self.temperature_label.setObjectName("temperatureValue")

        self.temperature_label.setStyleSheet(
            f"color: {accent};"
        )

        self.status_label = QLabel("Waiting for sensor")
        self.status_label.setObjectName("sensorStatus")

        layout.addWidget(self.title_label)
        layout.addWidget(self.temperature_label)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def set_temperature(self, value):
        if value is None:
            self.temperature_label.setText("-- °C")
            self.status_label.setText("Sensor unavailable")
        else:
            self.temperature_label.setText(
                f"{value:.1f} °C"
            )
            self.status_label.setText("Live temperature")


class UsageCard(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setObjectName("usageCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("usageTitle")

        self.value_label = QLabel("--%")
        self.value_label.setObjectName("usageValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        if value is None:
            self.value_label.setText("--%")
        else:
            self.value_label.setText(f"{value:.0f}%")


class DriveRow(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("driveRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        self.name_label = QLabel("Drive")
        self.name_label.setObjectName("driveName")

        self.temperature_label = QLabel("-- °C")
        self.temperature_label.setObjectName("driveTemperature")

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.temperature_label)

    def set_drive(self, name, temperature):
        self.name_label.setText(name)
        self.temperature_label.setText(
            f"{temperature:.1f} °C"
        )


class GamingOverlay(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Helios Gaming Overlay")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating
        )

        self.setFixedWidth(245)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(18, 20, 27, 225);
                color: white;
                border-radius: 12px;
            }

            QLabel {
                background: transparent;
                border: none;
            }

            QLabel#overlayTitle {
                color: #aeb8c8;
                font-size: 11px;
                font-weight: bold;
            }

            QLabel#overlayValue {
                color: #55d6a0;
                font-size: 19px;
                font-weight: bold;
            }

            QLabel#overlayDrive {
                color: #e0e5ee;
                font-size: 12px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 13, 15, 13)
        self.layout.setSpacing(8)

        heading = QLabel("HELIOS  •  LIVE")
        heading.setObjectName("overlayTitle")
        self.layout.addWidget(heading)

        self.cpu_label = self.add_temperature("CPU")
        self.gpu_label = self.add_temperature("GPU")

        self.drive_labels = []

        self.layout.addSpacing(3)

    def add_temperature(self, name):
        row = QHBoxLayout()

        name_label = QLabel(name)
        name_label.setStyleSheet(
            "color: #c4cad5; font-size: 12px;"
        )

        value_label = QLabel("-- °C")
        value_label.setObjectName("overlayValue")

        row.addWidget(name_label)
        row.addStretch()
        row.addWidget(value_label)

        self.layout.addLayout(row)

        return value_label

    def update_readings(self, readings):
        cpu = readings.get("cpu_temperature")
        gpu = readings.get("gpu_temperature")

        self.cpu_label.setText(
            f"{cpu:.1f} °C" if cpu is not None else "-- °C"
        )

        self.gpu_label.setText(
            f"{gpu:.1f} °C" if gpu is not None else "-- °C"
        )

        for label in self.drive_labels:
            self.layout.removeWidget(label)
            label.deleteLater()

        self.drive_labels.clear()

        for drive in readings.get("drives", []):
            label = QLabel(
                f"{drive['name']}: "
                f"{drive['temperature']:.1f} °C"
            )

            label.setObjectName("overlayDrive")
            self.layout.addWidget(label)

            self.drive_labels.append(label)

        self.adjustSize()

    def move_to_top_right(self):
        screen = QApplication.primaryScreen()

        if screen is None:
            return

        geometry = screen.availableGeometry()

        self.move(
            geometry.right() - self.width() - 18,
            geometry.top() + 55
        )


class HeliosWindow(QMainWindow):
    request_readings = Signal()

    def __init__(self):
        super().__init__()

        self.settings = QSettings("Helios", "HeliosMonitor")

        self.theme = self.settings.value(
            "theme", "dark"
        )

        self.overlay = GamingOverlay()
        self.last_readings = {}

        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.toggle_overlay.connect(
            self.toggle_overlay
        )

        self.hotkey_handle = None

        self.setWindowTitle("Helios System Monitor")
        self.setMinimumSize(850, 650)
        self.resize(1050, 760)

        self.build_interface()
        self.apply_theme()

        self.start_monitoring()
        self.setup_hotkey()

    def build_interface(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)

        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(18)

        # Header
        header = QHBoxLayout()

        title = QLabel("HELIOS")
        title.setObjectName("mainTitle")

        subtitle = QLabel("SYSTEM MONITOR")
        subtitle.setObjectName("mainSubtitle")

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.theme_button = QPushButton("Switch Theme")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.clicked.connect(
            self.toggle_theme
        )

        header.addLayout(title_layout)
        header.addStretch()
        header.addWidget(self.theme_button)

        main_layout.addLayout(header)

        # Connection status
        self.connection_label = QLabel(
            "Connecting to LibreHardwareMonitor..."
        )
        self.connection_label.setObjectName("connectionStatus")

        main_layout.addWidget(self.connection_label)

        # Temperature section
        temperature_heading = QLabel("TEMPERATURES")
        temperature_heading.setObjectName("sectionTitle")

        main_layout.addWidget(temperature_heading)

        temperature_grid = QGridLayout()
        temperature_grid.setSpacing(14)

        self.cpu_card = TemperatureCard(
            "CPU TEMPERATURE", "#55d6a0"
        )

        self.gpu_card = TemperatureCard(
            "GPU TEMPERATURE", "#65a9ff"
        )

        temperature_grid.addWidget(self.cpu_card, 0, 0)
        temperature_grid.addWidget(self.gpu_card, 0, 1)

        main_layout.addLayout(temperature_grid)

        # Drive section
        drive_heading = QLabel("DRIVE TEMPERATURES")
        drive_heading.setObjectName("sectionTitle")

        main_layout.addWidget(drive_heading)

        self.drive_container = QWidget()
        self.drive_layout = QVBoxLayout(
            self.drive_container
        )

        self.drive_layout.setContentsMargins(0, 0, 0, 0)
        self.drive_layout.setSpacing(8)

        self.no_drives_label = QLabel(
            "Waiting for drive sensors..."
        )
        self.no_drives_label.setObjectName("emptyMessage")

        self.drive_layout.addWidget(self.no_drives_label)

        main_layout.addWidget(self.drive_container)

        # Usage section
        usage_heading = QLabel("SYSTEM USAGE")
        usage_heading.setObjectName("sectionTitle")

        main_layout.addWidget(usage_heading)

        usage_grid = QGridLayout()
        usage_grid.setSpacing(12)

        self.cpu_usage_card = UsageCard("CPU USAGE")
        self.gpu_usage_card = UsageCard("GPU USAGE")
        self.ram_usage_card = UsageCard("RAM USAGE")

        usage_grid.addWidget(self.cpu_usage_card, 0, 0)
        usage_grid.addWidget(self.gpu_usage_card, 0, 1)
        usage_grid.addWidget(self.ram_usage_card, 0, 2)

        main_layout.addLayout(usage_grid)

        # Overlay settings
        overlay_heading = QLabel("GAMING OVERLAY")
        overlay_heading.setObjectName("sectionTitle")

        main_layout.addWidget(overlay_heading)

        overlay_row = QHBoxLayout()

        self.overlay_button = QPushButton(
            "Show Overlay"
        )

        self.overlay_button.clicked.connect(
            self.toggle_overlay
        )

        overlay_row.addWidget(self.overlay_button)
        overlay_row.addStretch()

        main_layout.addLayout(overlay_row)

        # Hotkey settings
        hotkey_row = QHBoxLayout()

        hotkey_label = QLabel("Global shortcut:")
        hotkey_label.setObjectName("settingLabel")

        self.hotkey_edit = QKeySequenceEdit()

        saved_hotkey = self.settings.value(
            "hotkey", "F11"
        )

        self.hotkey_edit.setKeySequence(
            QKeySequence(saved_hotkey)
        )

        self.save_hotkey_button = QPushButton(
            "Save Shortcut"
        )

        self.save_hotkey_button.clicked.connect(
            self.save_hotkey
        )

        hotkey_row.addWidget(hotkey_label)
        hotkey_row.addWidget(self.hotkey_edit)
        hotkey_row.addWidget(self.save_hotkey_button)

        main_layout.addLayout(hotkey_row)

        # Footer
        self.footer_label = QLabel(
            "Helios • Refresh interval: 2 seconds"
        )
        self.footer_label.setObjectName("footerLabel")

        main_layout.addStretch()
        main_layout.addWidget(self.footer_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(central)

        self.setCentralWidget(scroll)

    def start_monitoring(self):
        self.monitor_thread = QThread(self)
        self.monitor_worker = MonitorWorker()

        self.monitor_worker.moveToThread(
            self.monitor_thread
        )

        self.request_readings.connect(
            self.monitor_worker.update_readings
        )

        self.monitor_worker.readings_ready.connect(
            self.update_interface
        )

        self.monitor_thread.start()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(
            self.request_readings.emit
        )

        self.refresh_timer.start(2000)

        self.request_readings.emit()

    def update_interface(self, readings):
        self.last_readings = readings

        self.cpu_card.set_temperature(
            readings.get("cpu_temperature")
        )

        self.gpu_card.set_temperature(
            readings.get("gpu_temperature")
        )

        self.cpu_usage_card.set_value(
            readings.get("cpu_usage")
        )

        self.gpu_usage_card.set_value(
            readings.get("gpu_usage")
        )

        self.ram_usage_card.set_value(
            readings.get("ram_usage")
        )

        if readings.get("connected"):
            count = readings.get("sensor_count", 0)

            self.connection_label.setText(
                f"● LibreHardwareMonitor connected "
                f"• {count} sensors detected"
            )
        else:
            self.connection_label.setText(
                "● LibreHardwareMonitor disconnected "
                f"• {readings.get('error', 'Unknown error')}"
            )

        self.update_drive_list(
            readings.get("drives", [])
        )

        self.overlay.update_readings(readings)

    def update_drive_list(self, drives):
        while self.drive_layout.count():
            item = self.drive_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if not drives:
            message = QLabel(
                "No drive temperature sensors detected"
            )

            message.setObjectName("emptyMessage")
            self.drive_layout.addWidget(message)
            return

        for drive in drives:
            row = DriveRow()

            row.set_drive(
                drive["name"],
                drive["temperature"]
            )

            self.drive_layout.addWidget(row)

    def apply_theme(self):
        self.setStyleSheet(
            get_stylesheet(self.theme)
        )

        self.theme_button.setText(
            "Switch to Light Mode"
            if self.theme == "dark"
            else "Switch to Dark Mode"
        )

    def toggle_theme(self):
        self.theme = (
            "light" if self.theme == "dark" else "dark"
        )

        self.settings.setValue("theme", self.theme)
        self.apply_theme()

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
            self.overlay_button.setText("Show Overlay")
        else:
            self.overlay.update_readings(
                self.last_readings
            )

            self.overlay.move_to_top_right()
            self.overlay.show()

            self.overlay_button.setText("Hide Overlay")

    def setup_hotkey(self):
        saved_hotkey = self.settings.value(
            "hotkey", "F11"
        )

        self.register_hotkey(saved_hotkey)

    def register_hotkey(self, sequence):
        if self.hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(
                    self.hotkey_handle
                )
            except Exception:
                pass

            self.hotkey_handle = None

        key_string = sequence.lower().replace(
            " ", ""
        )

        try:
            self.hotkey_handle = keyboard.add_hotkey(
                key_string,
                lambda: self.hotkey_bridge.toggle_overlay.emit()
            )

            self.footer_label.setText(
                f"Helios • Global shortcut: {sequence}"
            )

            return True

        except Exception as error:
            self.footer_label.setText(
                f"Could not register shortcut: {error}"
            )

            return False

    def save_hotkey(self):
        sequence = self.hotkey_edit.keySequence().toString()

        if not sequence:
            self.footer_label.setText(
                "Please choose a keyboard shortcut."
            )
            return

        if self.register_hotkey(sequence):
            self.settings.setValue(
                "hotkey", sequence
            )

            self.footer_label.setText(
                f"Shortcut saved: {sequence}"
            )

    def closeEvent(self, event):
        self.refresh_timer.stop()

        if self.hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(
                    self.hotkey_handle
                )
            except Exception:
                pass

        self.overlay.close()

        self.monitor_thread.quit()
        self.monitor_thread.wait(3000)

        event.accept()
