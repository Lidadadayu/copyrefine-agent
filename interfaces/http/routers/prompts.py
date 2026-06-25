from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from infrastructure.prompting.prompt_store import (
    get_prompt_template,
    list_prompt_templates,
    reset_prompt_template,
    update_prompt_template,
)


router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptUpdateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    version: str = "v1"


@router.get("/templates")
def list_templates() -> Dict[str, Any]:
    return {"items": list_prompt_templates()}


@router.get("/templates/{name}")
def get_template(name: str) -> Dict[str, Any]:
    try:
        return get_prompt_template(name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/templates/{name}")
def update_template(name: str, req: PromptUpdateRequest) -> Dict[str, Any]:
    try:
        return update_prompt_template(name=name, prompt=req.prompt, version=req.version)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/templates/{name}/reset")
def reset_template(name: str) -> Dict[str, Any]:
    try:
        return reset_prompt_template(name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
