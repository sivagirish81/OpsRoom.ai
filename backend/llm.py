import json
import logging
from typing import Any

import weave
from openai import OpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)


@weave.op()
def complete_json(system: str, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        return fallback
    try:
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("LLM call failed; using evidence-based fallback: %s", exc)
        return fallback

