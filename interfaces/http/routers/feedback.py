from fastapi import APIRouter

from domain.models.schemas import FeedbackRequest, PreferenceRequest
from infrastructure.database.sqlite import (
    append_user_feedback,
    get_user_preference,
    upsert_user_preference,
)


router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def create_feedback(req: FeedbackRequest):
    item = append_user_feedback(
        task_id=req.task_id,
        user_id=req.user_id,
        rating=req.rating,
        comment=req.comment,
        preferred_version_type=req.preferred_version_type,
    )
    preference = None
    if req.remember_as_preference and (req.comment or req.preferred_version_type):
        current = get_user_preference(req.user_id)
        parts = [p for p in [current, req.comment.strip()] if p]
        if req.preferred_version_type:
            parts.append(f"Preferred version type: {req.preferred_version_type}")
        preference = upsert_user_preference(req.user_id, "\n".join(dict.fromkeys(parts)))
    return {"item": item, "preference": preference}


@router.get("/preferences/{user_id}")
def get_preference(user_id: str):
    return {"user_id": user_id, "preference_text": get_user_preference(user_id)}


@router.put("/preferences/{user_id}")
def update_preference(user_id: str, req: PreferenceRequest):
    return upsert_user_preference(user_id, req.preference_text)
