
import json
import re
import urllib.request

import psutil

from PySide6.QtCore import QObject, QThread, Signal


LHM_URL = "http://127.0.0.1:8085/data.json"
REQUEST_TIMEOUT = 3


def to_number(value):
    """Convert LibreHardwareMonitor sensor values to floats."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"-?\d+(?:\.\d+)?", str(value))

    if match:
        try:
            return float(match.group())
        except ValueError:
            return None

    return None


def get_sensor_value(sensor):
    """Prefer RawValue, falling back to the displayed Value."""
    raw = to_number(sensor.get("RawValue"))

    if raw is not None:
        return raw

    return to_number(sensor.get("Value"))


def flatten_hardware(node, inherited_name="", inherited_id=""):
    """
    Recursively extract sensors while preserving their parent
    hardware identity.
    """
    if not isinstance(node, dict):
        return []

    hardware_name = inherited_name
    hardware_id = inherited_id

    if "HardwareId" in node:
        hardware_id = str(node.get("HardwareId") or "")
        hardware_name = str(node.get("Text") or inherited_name)

    results = []

    if "SensorId" in node and "Type" in node:
        results.append({
            "sensor_name": str(node.get("Text") or ""),
            "sensor_type": str(node.get("Type") or ""),
            "sensor_id": str(node.get("SensorId") or ""),
            "hardware_name": hardware_name,
            "hardware_id": hardware_id,
            "value": get_sensor_value(node),
        })

    for child in node.get("Children", []):
        results.extend(
            flatten_hardware(child, hardware_name, hardware_id)
        )

    return results


class LibreHardwareMonitor:
    def __init__(self):
        self.last_error = None

    def read_sensors(self):
        """Fetch and flatten the complete LHM sensor tree."""
        request = urllib.request.Request(
            LHM_URL,
            headers={"User-Agent": "Helios-Monitor"}
        )

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:
            data = json.loads(response.read().decode("utf-8"))

        sensors = []

        for root in data.get("Children", []):
            sensors.extend(flatten_hardware(root))

        return sensors

    @staticmethod
    def is_temperature(sensor):
        return sensor["sensor_type"].lower() == "temperature"

    @staticmethod
    def is_load(sensor):
        return sensor["sensor_type"].lower() == "load"

    @staticmethod
    def hardware_text(sensor):
        return (
            sensor["hardware_name"] + " " +
            sensor["hardware_id"]
        ).lower()

    @staticmethod
    def sensor_text(sensor):
        return sensor["sensor_name"].lower()

    def find_temperature(self, sensors, hardware_filter, preferred_names):
        candidates = []

        for sensor in sensors:
            if not self.is_temperature(sensor):
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)

            if not hardware_filter(hardware):
                continue

            candidates.append(sensor)

        if not candidates:
            return None

        # Prefer meaningful CPU/GPU temperature labels.
        for preferred in preferred_names:
            for sensor in candidates:
                if preferred in self.sensor_text(sensor):
                    return sensor["value"]

        return candidates[0]["value"]

    def find_load(self, sensors, hardware_filter):
        candidates = []

        for sensor in sensors:
            if not self.is_load(sensor):
                continue

            if sensor["value"] is None:
                continue

            if hardware_filter(self.hardware_text(sensor)):
                candidates.append(sensor)

        if not candidates:
            return None

        # Prefer total or overall load sensors.
        for sensor in candidates:
            name = self.sensor_text(sensor)

            if "total" in name or "overall" in name:
                return sensor["value"]

        return candidates[0]["value"]

    def get_cpu_temperature(self, sensors):
        return self.find_temperature(
            sensors,
            lambda h: (
                "/amdcpu/" in h
                or "/intelcpu/" in h
                or "ryzen" in h
            ),
            [
                "cpu package",
                "tctl/tdie",
                "tdie",
                "cpu die",
                "ccd1",
                "core average",
            ]
        )

    def get_gpu_temperature(self, sensors):
        return self.find_temperature(
            sensors,
            lambda h: (
                "/nvidiagpu/" in h
                or "/atigpu/" in h
                or "geforce" in h
                or "rtx" in h
            ),
            [
                "gpu core",
                "gpu temperature",
                "hot spot",
                "core",
            ]
        )

    def get_gpu_usage(self, sensors):
        return self.find_load(
            sensors,
            lambda h: (
                "/nvidiagpu/" in h
                or "/atigpu/" in h
                or "geforce" in h
                or "rtx" in h
            )
        )

    def get_drive_temperatures(self, sensors):
        drives = {}

        drive_markers = (
            "/nvme/",
            "/ata/",
            "/storage/",
            "/hdd/",
            "nvme",
            "samsung",
            "western digital",
            "wd ",
            "seagate",
            "crucial",
            "kingston",
            "sk hynix",
            "solidigm",
        )

        for sensor in sensors:
            if not self.is_temperature(sensor):
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)

            if not any(marker in hardware for marker in drive_markers):
                continue

            hardware_id = sensor["hardware_id"]

            if not hardware_id:
                hardware_id = sensor["hardware_name"]

            if not hardware_id:
                continue

            # Avoid duplicate readings for the same physical drive.
            if hardware_id not in drives:
                drives[hardware_id] = {
                    "name": sensor["hardware_name"] or "Drive",
                    "temperature": sensor["value"],
                }

            elif (
                "composite" in self.sensor_text(sensor)
                or "temperature" in self.sensor_text(sensor)
            ):
                drives[hardware_id]["temperature"] = sensor["value"]

        return list(drives.values())

    def get_all_readings(self):
        """Collect all hardware readings into one dictionary."""
        self.last_error = None

        try:
            sensors = self.read_sensors()

            cpu_temperature = self.get_cpu_temperature(sensors)
            gpu_temperature = self.get_gpu_temperature(sensors)

            gpu_usage = self.get_gpu_usage(sensors)

            cpu_usage = psutil.cpu_percent(interval=None)
            ram_usage = psutil.virtual_memory().percent

            drive_temperatures = self.get_drive_temperatures(sensors)

            return {
                "connected": True,
                "error": None,
                "cpu_temperature": cpu_temperature,
                "gpu_temperature": gpu_temperature,
                "cpu_usage": cpu_usage,
                "gpu_usage": gpu_usage,
                "ram_usage": ram_usage,
                "drives": drive_temperatures,
                "sensor_count": len(sensors),
            }

        except Exception as error:
            self.last_error = str(error)

            return {
                "connected": False,
                "error": self.last_error,
                "cpu_temperature": None,
                "gpu_temperature": None,
                "cpu_usage": psutil.cpu_percent(interval=None),
                "gpu_usage": None,
                "ram_usage": psutil.virtual_memory().percent,
                "drives": [],
                "sensor_count": 0,
            }


class MonitorWorker(QObject):
    """Background worker that reads hardware without freezing the UI."""

    readings_ready = Signal(dict)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.monitor = LibreHardwareMonitor()
        self.running = True

    def update_readings(self):
        if not self.running:
            self.finished.emit()
            return

        readings = self.monitor.get_all_readings()
        self.readings_ready.emit(readings)

    def stop(self):
        self.running = False
