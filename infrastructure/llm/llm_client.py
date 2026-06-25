import json
import re
from typing import Any, Dict, List, Optional

import requests

from config.settings import get_settings


class LLMClient:
    """
    OpenAI-compatible LLM client.

    当前默认兼容 DashScope compatible-mode/v1/chat/completions。
    不依赖 openai SDK，避免额外依赖冲突。
    """

    def __init__(self):
        self.settings = get_settings()

    def enabled(self) -> bool:
        return (
            self.settings.enable_llm_optimize
            and self.settings.llm_provider.lower() != "mock"
            and bool(self.settings.llm_api_key)
        )

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.enabled():
            raise RuntimeError("LLM is disabled or API key is missing.")

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
        }

        response = requests.post(
            self.settings.llm_base_url,
            headers=headers,
            json=payload,
            timeout=self.settings.llm_timeout,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        从模型输出中提取 JSON。

        兼容以下情况：
        1. 纯 JSON
        2. ```json ... ```
        3. 前后带解释文字
        """
        text = text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"^```", "", text).strip()
            text = re.sub(r"```$", "", text).strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except Exception:
            return None