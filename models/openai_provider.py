import json
from typing import List, Optional

from openai import OpenAI

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT, strip_fences


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
        sysinfo_text: Optional[str] = None,
    ) -> Action:
        user_text = self._build_user_text(
            task, history, screen_width, screen_height, sysinfo_text
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
        raw = response.choices[0].message.content or ""
        raw = strip_fences(raw.strip())
        if not raw:
            raise ValueError(
                f"Model returned empty response. finish_reason={response.choices[0].finish_reason}"
            )
        return Action.from_dict(json.loads(raw))
