from __future__ import annotations
# ruff: noqa: E402

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict

from config.settings import get_settings
from infrastructure.retrieval.embedding_client import get_embedding_function
from infrastructure.retrieval.hybrid_retriever import HybridRetriever


CHROMA_DIR = Path("data/chroma")


def clear_chroma_dir(path: Path) -> None:
    target = path.resolve()
    workspace = PROJECT_ROOT.resolve()

    if workspace not in target.parents:
        raise SystemExit(f"Refusing to delete outside project workspace: {target}")

    try:
        shutil.rmtree(target)
    except PermissionError as exc:
        raise SystemExit(
            "Cannot clear Chroma index because a file is still in use.\n"
            f"Locked path: {exc.filename or target}\n\n"
            "Close running ContentPilot API/Streamlit processes, VSCode terminals, "
            "or Python sessions that imported Chroma, then rerun this command.\n"
            "If you only need to refresh changed documents, run without --clear."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild ContentPilot Chroma vector indexes.")
    parser.add_argument("--clear", action="store_true", help="delete data/chroma before rebuilding")
    parser.add_argument("--data-dir", default="data", help="knowledge jsonl directory")
    args = parser.parse_args()

    settings = get_settings()
    embedding_fn = get_embedding_function()

    if args.clear and CHROMA_DIR.exists():
        clear_chroma_dir(CHROMA_DIR)

    retriever = HybridRetriever(data_dir=args.data_dir)
    result: Dict[str, Any] = retriever.reset_vector_indexes(force=True)

    payload = {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_function": embedding_fn.name(),
        "chroma_dir": str(CHROMA_DIR),
        "result": result,
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
