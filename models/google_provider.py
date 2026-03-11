import base64
import json
from typing import List

import google.generativeai as genai
from PIL import Image
import io

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT


class GoogleProvider(BaseModel):
    """Gemini vision models via the Google Generative AI API."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        super().__init__(api_key, model_name)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
        )

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

        image_bytes = base64.b64decode(screenshot_b64)
        image = Image.open(io.BytesIO(image_bytes))

        response = self.client.generate_content(
            [user_text, image],
            generation_config=genai.types.GenerationConfig(max_output_tokens=512),
        )

        raw = response.text.strip()
        # strip markdown code fences if the model wraps its output
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return Action.from_dict(json.loads(raw))
