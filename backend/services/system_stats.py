"""
FRIDAY System Monitor Service
Fetches CPU, RAM, Disk, and Battery usage on macOS via psutil.
"""
import psutil


def get_system_stats() -> dict:
    """Return CPU %, RAM %, Disk %, and Battery % stats."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        return {
            "cpu_percent": round(cpu_pct, 1),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": round(mem.used / (1024 ** 3), 1),
            "ram_total_gb": round(mem.total / (1024 ** 3), 1),
            "disk_percent": round(disk.percent, 1),
            "battery_percent": round(battery.percent, 1) if battery else 100,
            "power_plugged": battery.power_plugged if battery else True,
        }
    except Exception as e:
        print(f"[SystemStats] Error fetching stats: {e}")
        return {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "disk_percent": 0.0,
            "battery_percent": 100,
            "power_plugged": True,
        }
