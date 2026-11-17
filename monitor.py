
import json
import re
import urllib.request

import psutil

from PySide6.QtCore import QObject, Signal


LHM_URL = "http://127.0.0.1:8085/data.json"
REQUEST_TIMEOUT = 3


def to_number(value):
    """Convert a LibreHardwareMonitor value into a float."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"-?\d+(?:\.\d+)?", str(value))

    if match:
        return float(match.group())

    return None


def flatten_hardware(node, hardware_name="", hardware_id=""):
    """Extract all sensors while preserving their hardware identity."""

    if not isinstance(node, dict):
        return []

    if "HardwareId" in node:
        hardware_id = str(node.get("HardwareId") or "")
        hardware_name = str(node.get("Text") or hardware_name)

    results = []

    if "SensorId" in node and "Type" in node:
        results.append({
            "sensor_name": str(node.get("Text") or ""),
            "sensor_type": str(node.get("Type") or ""),
            "sensor_id": str(node.get("SensorId") or ""),
            "hardware_name": hardware_name,
            "hardware_id": hardware_id,
            "value": to_number(node.get("RawValue")),
        })

    for child in node.get("Children", []):
        results.extend(
            flatten_hardware(
                child,
                hardware_name,
                hardware_id
            )
        )

    return results


class LibreHardwareMonitor:

    def __init__(self):
        self.last_error = None

    def read_sensors(self):
        """Read the LHM v0.9.6 Remote Web Server."""

        request = urllib.request.Request(
            LHM_URL,
            headers={
                "User-Agent": "Helios-System-Monitor"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        sensors = []

        for hardware in data.get("Children", []):
            sensors.extend(flatten_hardware(hardware))

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
        return sensor["sensor_name"].strip().lower()

    # --------------------------------------------------
    # CPU TEMPERATURE
    # --------------------------------------------------

    def get_cpu_temperature(self, sensors):

        candidates = []

        for sensor in sensors:
            if not self.is_temperature(sensor):
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)

            if (
                "/amdcpu/" in hardware
                or "ryzen" in hardware
            ):
                candidates.append(sensor)

        preferred_names = [
            "cpu package",
            "tctl/tdie",
            "tdie",
            "cpu die",
            "core average",
        ]

        for preferred in preferred_names:
            for sensor in candidates:
                if preferred in self.sensor_text(sensor):
                    return sensor["value"]

        if candidates:
            return candidates[0]["value"]

        return None

    # --------------------------------------------------
    # GPU TEMPERATURE
    # --------------------------------------------------

    def get_gpu_temperature(self, sensors):

        candidates = []

        for sensor in sensors:
            if not self.is_temperature(sensor):
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)

            if (
                "/nvidiagpu/" in hardware
                or "geforce" in hardware
                or "rtx" in hardware
            ):
                candidates.append(sensor)

        preferred_names = [
            "gpu core",
            "gpu temperature",
            "core",
        ]

        for preferred in preferred_names:
            for sensor in candidates:
                if self.sensor_text(sensor) == preferred:
                    return sensor["value"]

        if candidates:
            return candidates[0]["value"]

        return None

    # --------------------------------------------------
    # CPU / GPU USAGE
    # --------------------------------------------------

    def get_cpu_usage(self, sensors):

        # Windows CPU usage is obtained through psutil.
        return psutil.cpu_percent(interval=None)

    def get_gpu_usage(self, sensors):

        candidates = []

        for sensor in sensors:
            if not self.is_load(sensor):
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)

            if (
                "/nvidiagpu/" in hardware
                or "geforce" in hardware
                or "rtx" in hardware
            ):
                candidates.append(sensor)

        # Prefer GPU Core load when available.
        for sensor in candidates:
            name = self.sensor_text(sensor)

            if name in ("gpu core", "gpu core load"):
                return sensor["value"]

        # Otherwise use the first available GPU load.
        if candidates:
            return candidates[0]["value"]

        return None

    # --------------------------------------------------
    # DRIVE TEMPERATURES
    # --------------------------------------------------

    def get_drive_temperatures(self, sensors):

        drives = {}

        drive_markers = (
            "/nvme/",
            "/hdd/",
            "/ata/",
            "/storage/",
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

            if not any(
                marker in hardware
                for marker in drive_markers
            ):
                continue

            hardware_id = sensor["hardware_id"]

            if not hardware_id:
                continue

            sensor_name = self.sensor_text(sensor)

            # Never display warning or critical thresholds.
            if sensor_name in (
                "warning temperature",
                "critical temperature",
            ):
                continue

            # NVMe SSDs: ONLY Composite Temperature.
            if "/nvme/" in hardware_id.lower():

                if sensor_name != "composite temperature":
                    continue

            # HDD / SATA: ordinary Temperature.
            else:

                if sensor_name not in (
                    "temperature",
                    "composite temperature",
                ):
                    continue

            drives[hardware_id] = {
                "name": sensor["hardware_name"] or "Drive",
                "temperature": sensor["value"],
            }

        return list(drives.values())


    # --------------------------------------------------
    # DRIVE ACTIVITY / USAGE
    # --------------------------------------------------

    def get_drive_usage(self, sensors):

        drives = {}

        for sensor in sensors:

            if sensor["sensor_type"].lower() != "load":
                continue

            if sensor["value"] is None:
                continue

            hardware = self.hardware_text(sensor)
            hardware_id = sensor["hardware_id"]

            if not hardware_id:
                continue

            if not any(marker in hardware for marker in (
                "/nvme/",
                "/hdd/",
                "/ata/",
                "/storage/",
            )):
                continue

            # Only use actual disk activity, not used space.
            if self.sensor_text(sensor) != "total activity":
                continue

            drives[hardware_id] = {
                "id": hardware_id,
                "name": sensor["hardware_name"] or "Drive",
                "usage": max(0.0, min(100.0, sensor["value"]))
            }

        return list(drives.values())

    # --------------------------------------------------
    # COMPLETE HARDWARE READINGS
    # --------------------------------------------------

    def get_all_readings(self):

        self.last_error = None

        try:

            sensors = self.read_sensors()

            readings = {
                "connected": True,
                "error": None,

                "cpu_temperature":
                    self.get_cpu_temperature(sensors),

                "gpu_temperature":
                    self.get_gpu_temperature(sensors),

                "cpu_usage":
                    self.get_cpu_usage(sensors),

                "gpu_usage":
                    self.get_gpu_usage(sensors),

                "ram_usage":
                    psutil.virtual_memory().percent,

                "drives":
                    self.get_drive_temperatures(sensors),
                
                "drive_usage": 
                    self.get_drive_usage(sensors),

                "sensor_count":
                    len(sensors),
            }

            return readings

        except Exception as error:

            self.last_error = str(error)

            return {
                "connected": False,
                "error": self.last_error,

                "cpu_temperature": None,
                "gpu_temperature": None,

                "cpu_usage":
                    psutil.cpu_percent(interval=None),

                "gpu_usage": None,
                "drive_usage": [],
                "ram_usage":
                    psutil.virtual_memory().percent,

                "drives": [],
                "sensor_count": 0,
            }


# ======================================================
# BACKGROUND MONITORING WORKER
# ======================================================

class MonitorWorker(QObject):

    readings_ready = Signal(dict)
    finished = Signal()

    def __init__(self):
        super().__init__()

        self.monitor = LibreHardwareMonitor()
        self.running = True

    def update_readings(self):

        if not self.running:
            return

        readings = self.monitor.get_all_readings()

        self.readings_ready.emit(readings)

    def stop(self):
        self.running = False
