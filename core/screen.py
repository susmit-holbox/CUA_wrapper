"""
Screen capture - platform-aware, OS-agnostic.

Linux Wayland:  XDG ScreenCast portal (org.freedesktop.portal.ScreenCast).
                OpenPipeWireRemote returns a PRIVATE PipeWire fd that only
                exposes the user-selected screen.  The camera is not visible
                on this fd, so GStreamer pipewiresrc cannot accidentally
                connect to it regardless of WirePlumber routing.

                First run: a GNOME screen-share dialog appears once so the
                user can select which screen to share.  A restore_token is
                saved to ~/.config/cua-facilitator/screencast_token so
                subsequent runs skip the dialog entirely.

Linux X11:      mss (XGetImage).
Windows:        mss (DXGI/GDI).
macOS:          screencapture subprocess.
"""

import atexit
import base64
import io
import os
import platform
import random
import string
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN_FILE = Path.home() / ".config" / "cua-facilitator" / "screencast_token"


def _is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _ensure_gi() -> None:
    gi_path = "/usr/lib64/python3.14/site-packages"
    if gi_path not in sys.path and os.path.isdir(gi_path):
        sys.path.insert(0, gi_path)


def _make_token() -> str:
    return "cua" + "".join(random.choices(string.ascii_lowercase, k=8))


# ---------------------------------------------------------------------------
# XDG ScreenCast portal  (Linux Wayland)
# ---------------------------------------------------------------------------

class _ScreenCastSession:
    """
    Persistent XDG ScreenCast portal session.

    The session is created once at first use and kept alive for the entire
    run so each grab() call only needs OpenPipeWireRemote + gst-launch-1.0.

    OpenPipeWireRemote returns a private PipeWire socket fd that exposes ONLY
    the selected monitor node.  The camera is completely invisible on this fd,
    making accidental camera capture impossible.
    """

    def __init__(self):
        self._connection = None
        self._proxy = None
        self._session_handle: str = ""
        self._node_id: int = 0
        atexit.register(self.stop)

    # ------------------------------------------------------------------
    # Internal D-Bus helpers
    # ------------------------------------------------------------------

    def _call_and_wait(self, method: str, args, req_path: str, timeout: int = 60):
        """
        Subscribe to the portal Response signal BEFORE making the D-Bus call
        to avoid missing fast responses (race condition if we subscribe after).
        """
        _ensure_gi()
        from gi.repository import Gio, GLib  # type: ignore[import]

        result: dict = {}
        loop = GLib.MainLoop()

        def _cb(c, s, o, i, sig, params, d):
            code, data = params.unpack()
            result["code"] = code
            result["data"] = data
            loop.quit()

        sub = self._connection.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            "org.freedesktop.portal.Request",
            "Response",
            req_path,
            None,
            Gio.DBusSignalFlags.NONE,
            _cb,
            None,
        )
        # Call AFTER subscription is active
        self._proxy.call_sync(method, args, Gio.DBusCallFlags.NONE, -1, None)
        GLib.timeout_add_seconds(timeout, loop.quit)
        loop.run()
        self._connection.signal_unsubscribe(sub)
        return result.get("code", -1), result.get("data", {})

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self) -> None:
        _ensure_gi()
        import gi  # type: ignore[import]
        gi.require_version("Gio", "2.0")
        gi.require_version("GLib", "2.0")
        from gi.repository import Gio, GLib  # type: ignore[import]

        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        sender = self._connection.get_unique_name()[1:].replace(".", "_")

        self._proxy = Gio.DBusProxy.new_sync(
            self._connection, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.ScreenCast",
            None,
        )

        restore_token = _TOKEN_FILE.read_text().strip() if _TOKEN_FILE.exists() else ""

        # --- CreateSession ---
        ht = _make_token()
        sht = _make_token()
        req1 = f"/org/freedesktop/portal/desktop/request/{sender}/{ht}"
        code, data = self._call_and_wait(
            "CreateSession",
            GLib.Variant("(a{sv})", ({
                "handle_token": GLib.Variant("s", ht),
                "session_handle_token": GLib.Variant("s", sht),
            },)),
            req1,
        )
        if code != 0:
            raise RuntimeError(f"ScreenCast CreateSession failed (code {code})")
        self._session_handle = data["session_handle"]

        # --- SelectSources ---
        ht2 = _make_token()
        req2 = f"/org/freedesktop/portal/desktop/request/{sender}/{ht2}"
        opts: dict = {
            "handle_token": GLib.Variant("s", ht2),
            "types": GLib.Variant("u", 1),          # 1 = Monitor
            "multiple": GLib.Variant("b", False),
            "persist_mode": GLib.Variant("u", 2),   # persist permanently
        }
        if restore_token:
            opts["restore_token"] = GLib.Variant("s", restore_token)
        code, data = self._call_and_wait(
            "SelectSources",
            GLib.Variant("(oa{sv})", (self._session_handle, opts)),
            req2,
            timeout=120,
        )
        if code != 0:
            raise RuntimeError(f"ScreenCast SelectSources failed (code {code})")

        # --- Start ---
        ht3 = _make_token()
        req3 = f"/org/freedesktop/portal/desktop/request/{sender}/{ht3}"
        code, data = self._call_and_wait(
            "Start",
            GLib.Variant("(osa{sv})", (self._session_handle, "", {
                "handle_token": GLib.Variant("s", ht3),
            })),
            req3,
            timeout=120,
        )
        if code != 0:
            raise RuntimeError(f"ScreenCast Start failed (code {code})")

        # Save restore_token for next run (silent start)
        new_token = data.get("restore_token", "")
        if new_token:
            _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            _TOKEN_FILE.write_text(new_token)

        streams = data.get("streams", [])
        if not streams:
            raise RuntimeError("ScreenCast Start returned no streams")
        self._node_id = streams[0][0]

    # ------------------------------------------------------------------
    # Grab one frame
    # ------------------------------------------------------------------

    def grab(self) -> Image.Image:
        _ensure_gi()
        from gi.repository import Gio, GLib  # type: ignore[import]

        # OpenPipeWireRemote - returns a private PipeWire socket fd
        # (only the selected screen is visible on this socket)
        ret, fd_list = self._proxy.call_with_unix_fd_list_sync(
            "OpenPipeWireRemote",
            GLib.Variant("(oa{sv})", (self._session_handle, {})),
            Gio.DBusCallFlags.NONE, -1, None, None,
        )
        pw_fd_index = ret.unpack()[0]
        pw_fd = fd_list.get(pw_fd_index)

        # Inherit the fd into the subprocess
        os.set_inheritable(pw_fd, True)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            outpath = f.name
        try:
            subprocess.run(
                [
                    "gst-launch-1.0", "-q",
                    "pipewiresrc", f"fd={pw_fd}", f"path={self._node_id}",
                    "num-buffers=1",
                    "!", "videoconvert",
                    "!", "pngenc",
                    "!", "filesink", f"location={outpath}",
                ],
                check=True,
                timeout=10,
                pass_fds=(pw_fd,),
            )
            return Image.open(outpath).copy()
        finally:
            try:
                os.close(pw_fd)
            except OSError:
                pass
            if os.path.exists(outpath):
                os.unlink(outpath)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def stop(self) -> None:
        if not self._session_handle:
            return
        try:
            _ensure_gi()
            from gi.repository import Gio, GLib  # type: ignore[import]
            session_proxy = Gio.DBusProxy.new_sync(
                self._connection, Gio.DBusProxyFlags.NONE, None,
                "org.freedesktop.portal.Desktop",
                self._session_handle,
                "org.freedesktop.portal.Session",
                None,
            )
            session_proxy.call_sync(
                "Close", GLib.Variant("()", ()), Gio.DBusCallFlags.NONE, -1, None,
            )
        except Exception:
            pass
        self._session_handle = ""


_screencast_session: "_ScreenCastSession | None" = None


def _get_screencast_session() -> _ScreenCastSession:
    global _screencast_session
    if _screencast_session is None:
        _screencast_session = _ScreenCastSession()
        _screencast_session.setup()
    return _screencast_session


def _capture_linux_wayland() -> Image.Image:
    sess = _get_screencast_session()
    return sess.grab()


# ---------------------------------------------------------------------------
# Non-Wayland backends
# ---------------------------------------------------------------------------

def _capture_macos() -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        subprocess.run(["screencapture", "-x", path], check=True, timeout=5)
        return Image.open(path).copy()
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _capture_mss() -> Image.Image:
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def capture() -> tuple[Image.Image, str]:
    """
    Take a full-screen screenshot.
    Returns (PIL Image, base64-encoded PNG string).
    """
    system = platform.system()

    if system == "Darwin":
        img = _capture_macos()
    elif system == "Linux" and _is_wayland():
        img = _capture_linux_wayland()
    else:
        img = _capture_mss()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return img, b64


def screen_size() -> tuple[int, int]:
    img, _ = capture()
    return img.size
