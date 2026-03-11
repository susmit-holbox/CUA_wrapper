import json
from typing import List, Optional

import anthropic

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT, strip_fences


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
        sysinfo_text: Optional[str] = None,
    ) -> Action:
        user_text = self._build_user_text(
            task, history, screen_width, screen_height, sysinfo_text
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
        raw = strip_fences(message.content[0].text.strip())
        if not raw:
            raise ValueError("Model returned empty response")
        return Action.from_dict(json.loads(raw))
