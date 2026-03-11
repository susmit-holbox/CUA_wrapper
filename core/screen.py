import base64
import io

import pyautogui
from PIL import Image


def capture() -> tuple[Image.Image, str]:
    """
    Take a screenshot of the primary display.
    Returns (PIL Image, base64-encoded PNG string).
    """
    screenshot = pyautogui.screenshot()
    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return screenshot, b64


def screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary display."""
    return pyautogui.size()
