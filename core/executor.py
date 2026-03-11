import time

from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

from actions.types import Action, ActionType

INTER_ACTION_DELAY = 0.3

_mouse = MouseController()
_keyboard = KeyboardController()

# Maps common string names to pynput Key constants
_KEY_MAP: dict[str, Key] = {
    "enter": Key.enter,
    "return": Key.enter,
    "tab": Key.tab,
    "space": Key.space,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "escape": Key.esc,
    "esc": Key.esc,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
    "shift": Key.shift,
    "super": Key.cmd,
    "cmd": Key.cmd,
    "win": Key.cmd,
    "left": Key.left,
    "right": Key.right,
    "up": Key.up,
    "down": Key.down,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "page_down": Key.page_down,
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
}


def _resolve_key(k: str) -> Key | str:
    return _KEY_MAP.get(k.strip().lower(), k.strip())


def execute(action: Action) -> None:
    """Translate an Action into pynput calls. Works on Windows, macOS, and Linux (X11 + Wayland)."""
    time.sleep(INTER_ACTION_DELAY)

    if action.type == ActionType.CLICK:
        _mouse.position = (action.x, action.y)
        _mouse.click(Button.left)

    elif action.type == ActionType.DOUBLE_CLICK:
        _mouse.position = (action.x, action.y)
        _mouse.click(Button.left, count=2)

    elif action.type == ActionType.RIGHT_CLICK:
        _mouse.position = (action.x, action.y)
        _mouse.click(Button.right)

    elif action.type == ActionType.TYPE:
        _keyboard.type(action.text)

    elif action.type == ActionType.KEY:
        keys = [_resolve_key(k) for k in action.text.split("+")]
        for k in keys:
            _keyboard.press(k)
        for k in reversed(keys):
            _keyboard.release(k)

    elif action.type == ActionType.SCROLL:
        amount = action.amount or 3
        dx, dy = 0, 0
        if action.direction == "up":
            dy = amount
        elif action.direction == "down":
            dy = -amount
        elif action.direction == "left":
            dx = -amount
        elif action.direction == "right":
            dx = amount
        _mouse.position = (action.x, action.y)
        _mouse.scroll(dx, dy)

    elif action.type == ActionType.WAIT:
        time.sleep(action.seconds or 1.0)

    elif action.type in (ActionType.SCREENSHOT, ActionType.DONE):
        pass
