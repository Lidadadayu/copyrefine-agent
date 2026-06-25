import json
from pathlib import Path
from typing import Dict, List


def load_jsonl(path: str | Path) -> List[Dict]:
    path = Path(path)
    if not path.exists():
        return []
    docs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            docs.append(json.loads(line))
    return docs
