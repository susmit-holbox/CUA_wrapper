import os
import platform
import subprocess
from dataclasses import dataclass


@dataclass
class SystemInfo:
    os_name: str        # "Linux", "Darwin", "Windows"
    os_version: str     # kernel / OS version
    distro: str         # "Fedora Linux 43", "Ubuntu 24.04", etc.
    desktop: str        # "GNOME", "KDE Plasma", "XFCE", etc.
    display_server: str # "Wayland", "X11"
    screen_width: int
    screen_height: int

    def as_prompt_text(self) -> str:
        """One-line summary to inject into every model prompt."""
        return (
            f"OS: {self.os_name} ({self.distro}) | "
            f"Desktop: {self.desktop} | "
            f"Display: {self.display_server} | "
            f"Screen: {self.screen_width}x{self.screen_height}"
        )

    def as_dict(self) -> dict:
        return self.__dict__


def gather(screen_width: int = 0, screen_height: int = 0) -> SystemInfo:
    """Collect OS, desktop environment, and display server information."""
    os_name = platform.system()

    # OS version
    os_version = platform.release()

    # Linux distro from /etc/os-release
    distro = os_name
    if os_name == "Linux":
        try:
            out = subprocess.check_output(["cat", "/etc/os-release"], text=True)
            for line in out.splitlines():
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            pass
    elif os_name == "Darwin":
        try:
            distro = subprocess.check_output(
                ["sw_vers", "-productVersion"], text=True
            ).strip()
            distro = f"macOS {distro}"
        except Exception:
            distro = "macOS"

    # Desktop environment
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or _detect_desktop_windows()
        or "Unknown"
    )

    # Display server
    if os.environ.get("WAYLAND_DISPLAY"):
        display_server = "Wayland"
    elif os.environ.get("DISPLAY"):
        display_server = "X11"
    elif os_name == "Darwin":
        display_server = "Quartz"
    elif os_name == "Windows":
        display_server = "Win32"
    else:
        display_server = "Unknown"

    return SystemInfo(
        os_name=os_name,
        os_version=os_version,
        distro=distro,
        desktop=desktop,
        display_server=display_server,
        screen_width=screen_width,
        screen_height=screen_height,
    )


def _detect_desktop_windows() -> str:
    """Best-effort desktop detection when XDG vars are absent (Windows/macOS)."""
    import platform
    system = platform.system()
    if system == "Windows":
        return "Windows Shell"
    if system == "Darwin":
        return "Aqua"
    return ""
