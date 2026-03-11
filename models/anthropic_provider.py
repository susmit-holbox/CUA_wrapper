import json
from typing import List

import anthropic

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT


class AnthropicProvider(BaseModel):
    """Claude via the Anthropic API."""

    def __init__(self, api_key: str, model_name: str = "claude-opus-4-5"):
        super().__init__(api_key, model_name)
        self.client = anthropic.Anthropic(api_key=api_key)

    def get_action(
        self,
        screenshot_b64: str,
        task: str,
        history: List[dict],
        screen_width: int,
        screen_height: int,
    ) -> Action:
        history_text = self._build_history_text(history)
        user_text = (
            f"Task: {task}\n"
            f"Screen resolution: {screen_width}x{screen_height}\n"
            f"{history_text}\n\n"
            "Current screenshot attached. Return your next action as JSON."
        )

        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()
        return Action.from_dict(json.loads(raw))
