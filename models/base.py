from abc import ABC, abstractmethod
from typing import List
from actions.types import Action


SYSTEM_PROMPT = """You are a computer-use agent. You control a desktop by returning JSON actions.

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
    ) -> Action:
        """
        Given a base64-encoded screenshot and the current task, return the next Action.

        history is a list of prior dicts: {"action": ..., "reasoning": ..., "result": ...}
        """
        ...

    def _build_history_text(self, history: List[dict]) -> str:
        if not history:
            return ""
        lines = ["Previous actions taken:"]
        for i, h in enumerate(history, 1):
            lines.append(f"  {i}. {h}")
        return "\n".join(lines)
