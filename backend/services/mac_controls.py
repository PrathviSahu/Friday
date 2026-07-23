"""macOS Display & System Automation Controller for F.R.I.D.A.Y.

Provides zero-latency hardware & display controls:
- Display Brightness adjustment via CoreGraphics DisplayServices framework (0.0 to 1.0)
- System Dark Mode / Light Mode toggle via AppleScript
- System Volume & Mute control via AppleScript
- Screen Saver / Lock Display execution
"""
import ctypes
import os
import platform
import subprocess
from typing import Dict, Any

IS_MAC = platform.system() == "Darwin"

# ── Private DisplayServices C-Bindings for macOS Display Brightness ──────────
_display_services = None
if IS_MAC:
    try:
        _display_services = ctypes.CDLL(
            "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
        )
        _display_services.DisplayServicesSetBrightness.argtypes = [ctypes.c_uint32, ctypes.c_float]
        _display_services.DisplayServicesGetBrightness.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
    except Exception as err:
        print(f"[MacControls] DisplayServices framework warning: {err}")
        _display_services = None


def get_brightness() -> float:
    """Get current main display brightness (0.0 to 1.0)."""
    if _display_services:
        try:
            val = ctypes.c_float()
            _display_services.DisplayServicesGetBrightness(1, ctypes.byref(val))
            return round(float(val.value), 2)
        except Exception:
            pass
    return 0.75


def set_brightness(level: float) -> bool:
    """Set main display brightness (level between 0.0 and 1.0 or 0 and 100)."""
    if not IS_MAC:
        return False
    
    # Handle percentage inputs (e.g. 80 -> 0.8)
    if level > 1.0:
        level = level / 100.0
    level = max(0.0, min(1.0, float(level)))

    if _display_services:
        try:
            _display_services.DisplayServicesSetBrightness(1, level)
            print(f"[MacControls] Set display brightness to {int(level * 100)}%")
            return True
        except Exception as e:
            print(f"[MacControls] DisplayServices error: {e}")

    # Fallback to key code simulation via AppleScript
    try:
        current = get_brightness()
        steps = int(round((level - current) * 16))
        if steps != 0:
            key_code = 145 if steps > 0 else 144
            script = f'tell application "System Events" to repeat {abs(steps)} times\nkey code {key_code}\nend repeat'
            subprocess.run(["osascript", "-e", script], check=True)
            return True
    except Exception as e:
        print(f"[MacControls] AppleScript brightness fallback error: {e}")

    return False


def get_dark_mode() -> bool:
    """Check if macOS Dark Mode is currently enabled."""
    if not IS_MAC:
        return True
    try:
        script = 'tell application "System Events" to get dark mode of appearance preferences'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        return "true" in res.stdout.lower()
    except Exception:
        return True


def set_dark_mode(enabled: bool) -> bool:
    """Toggle macOS Dark Mode on or off."""
    if not IS_MAC:
        return False
    try:
        val = "true" if enabled else "false"
        script = f'tell application "System Events" to set dark mode of appearance preferences to {val}'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        print(f"[MacControls] Set Dark Mode to {enabled}")
        return res.returncode == 0
    except Exception as e:
        print(f"[MacControls] Dark mode error: {e}")
        return False


def get_system_volume() -> Dict[str, Any]:
    """Get system output volume level (0-100) and mute status."""
    if not IS_MAC:
        return {"volume": 70, "muted": False}
    try:
        script = 'get volume settings'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        out = res.stdout.strip()
        
        # Output format: output volume:80, input volume:50, alert volume:100, output muted:false
        vol_match = re.search(r'output volume:(\d+)', out)
        mute_match = re.search(r'output muted:(true|false)', out, re.IGNORECASE)
        
        vol = int(vol_match.group(1)) if vol_match else 70
        muted = mute_match.group(1).lower() == "true" if mute_match else False
        return {"volume": vol, "muted": muted}
    except Exception:
        return {"volume": 70, "muted": False}


def set_system_volume(level: int) -> bool:
    """Set system output volume level (0 to 100)."""
    if not IS_MAC:
        return False
    try:
        level = max(0, min(100, int(level)))
        script = f'set volume output volume {level}'
        subprocess.run(["osascript", "-e", script], check=True, timeout=2)
        print(f"[MacControls] Set system volume to {level}%")
        return True
    except Exception as e:
        print(f"[MacControls] System volume error: {e}")
        return False


def set_system_mute(muted: bool) -> bool:
    """Mute or unmute system audio output."""
    if not IS_MAC:
        return False
    try:
        val = "true" if muted else "false"
        script = f'set volume output muted {val}'
        subprocess.run(["osascript", "-e", script], check=True, timeout=2)
        print(f"[MacControls] System muted: {muted}")
        return True
    except Exception as e:
        print(f"[MacControls] Mute error: {e}")
        return False


def lock_display() -> bool:
    """Immediately lock display and trigger macOS lock screen."""
    if not IS_MAC:
        return False
    try:
        # Trigger macOS lock display
        subprocess.run(["pmset", "displaysleepnow"], check=True)
        print("[MacControls] Lock display executed")
        return True
    except Exception:
        try:
            script = 'tell application "System Events" to start current screen saver'
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception:
            return False


def get_display_status() -> Dict[str, Any]:
    """Get complete display and audio status overview."""
    vol_info = get_system_volume()
    return {
        "brightness": int(get_brightness() * 100),
        "dark_mode": get_dark_mode(),
        "volume": vol_info["volume"],
        "muted": vol_info["muted"],
        "platform": platform.system(),
    }
