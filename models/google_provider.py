import base64
import io
import json
from typing import List, Optional

import google.generativeai as genai
from PIL import Image

from actions.types import Action
from models.base import BaseModel, SYSTEM_PROMPT, strip_fences


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
        sysinfo_text: Optional[str] = None,
    ) -> Action:
        user_text = self._build_user_text(
            task, history, screen_width, screen_height, sysinfo_text
        )
        image_bytes = base64.b64decode(screenshot_b64)
        image = Image.open(io.BytesIO(image_bytes))
        response = self.client.generate_content(
            [user_text, image],
            generation_config=genai.types.GenerationConfig(max_output_tokens=512),
        )
        raw = strip_fences(response.text.strip())
        if not raw:
            raise ValueError("Model returned empty response")
        return Action.from_dict(json.loads(raw))
