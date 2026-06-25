from pathlib import Path
from typing import Any, Dict
import yaml


class PromptRegistry:
    def __init__(self, prompt_dir: str = "prompts"):
        self.prompt_dir = Path(prompt_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, name: str) -> Dict[str, Any]:
        if name in self._cache:
            return self._cache[name]
        path = self.prompt_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self._cache[name] = data
        return data

    def render(self, name: str, **kwargs: Any) -> str:
        data = self.load(name)
        return data.get("prompt", "").format(**kwargs)
