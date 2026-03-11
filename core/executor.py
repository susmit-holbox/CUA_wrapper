import time

import pyautogui

from actions.types import Action, ActionType

# small delay between actions so the UI has time to react
INTER_ACTION_DELAY = 0.3

pyautogui.FAILSAFE = True  # move mouse to corner to abort


def execute(action: Action) -> None:
    """Translate an Action into pyautogui calls."""
    time.sleep(INTER_ACTION_DELAY)

    if action.type == ActionType.CLICK:
        pyautogui.click(action.x, action.y)

    elif action.type == ActionType.DOUBLE_CLICK:
        pyautogui.doubleClick(action.x, action.y)

    elif action.type == ActionType.RIGHT_CLICK:
        pyautogui.rightClick(action.x, action.y)

    elif action.type == ActionType.TYPE:
        pyautogui.typewrite(action.text, interval=0.05)

    elif action.type == ActionType.KEY:
        keys = action.text.split("+")
        pyautogui.hotkey(*keys)

    elif action.type == ActionType.SCROLL:
        scroll_amount = action.amount or 3
        if action.direction in ("up", "down"):
            clicks = scroll_amount if action.direction == "up" else -scroll_amount
            pyautogui.scroll(clicks, x=action.x, y=action.y)
        elif action.direction == "left":
            pyautogui.hscroll(-scroll_amount, x=action.x, y=action.y)
        elif action.direction == "right":
            pyautogui.hscroll(scroll_amount, x=action.x, y=action.y)

    elif action.type == ActionType.WAIT:
        time.sleep(action.seconds or 1.0)

    elif action.type in (ActionType.SCREENSHOT, ActionType.DONE):
        pass  # handled by the loop
