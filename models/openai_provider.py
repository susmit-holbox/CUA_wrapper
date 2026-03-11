import json
from typing import List

from openai import OpenAI

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT


class OpenAIProvider(BaseModel):
    """GPT-4o (or any OpenAI vision model) via the OpenAI API."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        super().__init__(api_key, model_name)
        self.client = OpenAI(api_key=api_key)

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

        response = self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=512,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
        )

        raw = response.choices[0].message.content.strip()
        return Action.from_dict(json.loads(raw))
