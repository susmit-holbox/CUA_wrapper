from abc import ABC, abstractmethod
from typing import List, Optional

from actions.types import Action


def strip_fences(text: str) -> str:
    """Strip markdown code fences that some models wrap around JSON output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


SYSTEM_PROMPT = """You are a computer-use agent. You control a real desktop by returning JSON actions.

Each response must be a single JSON object with an "action" field. Available actions:

  {"action": "click", "x": <int>, "y": <int>, "reasoning": "<why>"}
  {"action": "double_click", "x": <int>, "y": <int>, "reasoning": "<why>"}
  {"action": "right_click", "x": <int>, "y": <int>, "reasoning": "<why>"}
  {"action": "type", "text": "<text to type>", "reasoning": "<why>"}
  {"action": "key", "text": "<key combo e.g. ctrl+c>", "reasoning": "<why>"}
  {"action": "scroll", "x": <int>, "y": <int>, "direction": "up|down|left|right", "amount": <lines>, "reasoning": "<why>"}
  {"action": "screenshot", "reasoning": "<why>"}
  {"action": "wait", "seconds": <float>, "reasoning": "<why>"}
  {"action": "done", "result": "<summary of what was accomplished>"}

Rules:
- Return ONLY a JSON object, no markdown, no extra text.
- Use coordinates relative to the screenshot dimensions provided.
- When the task is complete, return the "done" action.
- Be precise with coordinates. Click the center of UI elements.
- The screenshot may look very dark if a dark-theme application is open - that is normal.
- Use OS/desktop context (provided in each message) to make environment-appropriate decisions.
"""


class BaseModel(ABC):
    """Abstract interface every model provider must implement."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def get_action(
        self,
        screenshot_b64: str,
        task: str,
        history: List[dict],
        screen_width: int,
        screen_height: int,
        sysinfo_text: Optional[str] = None,
    ) -> Action:
        """
        Given a base64-encoded screenshot and the current task, return the next Action.

        history is a list of prior action dicts.
        sysinfo_text is a one-line environment summary (OS, DE, display server, resolution).
        """
        ...

    def _build_user_text(
        self,
        task: str,
        history: List[dict],
        screen_width: int,
        screen_height: int,
        sysinfo_text: Optional[str],
    ) -> str:
        parts = []
        if sysinfo_text:
            parts.append(f"System environment: {sysinfo_text}")
        parts.append(f"Task: {task}")
        parts.append(f"Screen resolution: {screen_width}x{screen_height}")
        if history:
            parts.append("Previous actions taken:")
            for i, h in enumerate(history, 1):
                parts.append(f"  {i}. {h}")
        parts.append("Current screenshot attached. Return your next action as JSON.")
        return "\n".join(parts)
