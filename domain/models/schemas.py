from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContentAnalyzeRequest(BaseModel):
    raw_content: str = Field(..., min_length=1, description="source content")
    platform: Optional[str] = Field(default="xiaohongshu", description="target platform")
    platforms: List[str] = Field(default_factory=list, description="batch target platforms")
    content_type: Optional[str] = Field(default="product_review", description="content type")
    task_type: Optional[str] = Field(default="review_and_rewrite", description="task type")
    target_audience: Optional[str] = Field(default=None, description="target audience")
    rewrite_intensity: str = Field(default="medium", description="light, medium, or deep rewrite intensity")
    expression_strength: str = Field(default="moderate", description="restrained, moderate, or strong compliant appeal")
    user_id: str = Field(default="default_user")
    refine_instruction: Optional[str] = Field(default=None, description="refine instruction")
    parent_task_id: Optional[str] = Field(default=None, description="source task id")
    conversation_id: Optional[str] = Field(default=None, description="multi-turn conversation id")
    original_content: Optional[str] = Field(default=None, description="original source content for multi-turn editing")
    previous_output: Optional[str] = Field(default=None, description="previous assistant output summary")


class RiskItem(BaseModel):
    text: str
    risk_type: str
    severity: str
    suggestion: str


class ContentVersion(BaseModel):
    version_type: str
    title: str
    body: str
    score: int
    notes: str


class ContentAnalyzeResponse(BaseModel):
    task_id: str
    platform: str
    content_type: str
    risk_level: str
    score: int
    risk_items: List[RiskItem]
    title_suggestions: List[str]
    rewritten_versions: List[ContentVersion]
    evidence_pack: Dict[str, Any]
    final_report: str
    trace: List[Dict[str, Any]] = []


class BatchAnalyzeResponse(BaseModel):
    items: List[ContentAnalyzeResponse]


class RefineRequest(BaseModel):
    task_id: Optional[str] = None
    version_id: Optional[int] = None
    raw_content: Optional[str] = None
    instruction: str = Field(..., min_length=1)
    platform: Optional[str] = None
    platforms: List[str] = Field(default_factory=list)
    content_type: Optional[str] = None
    task_type: Optional[str] = "review_and_rewrite"
    target_audience: Optional[str] = None
    rewrite_intensity: str = "medium"
    expression_strength: str = "moderate"
    selected_version_body: Optional[str] = None
    selected_version_type: Optional[str] = None
    original_content: Optional[str] = None
    previous_output: Optional[str] = None
    user_id: str = "default_user"
    conversation_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    task_id: str
    user_id: str = "default_user"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: str = ""
    preferred_version_type: Optional[str] = None
    remember_as_preference: bool = True


class PreferenceRequest(BaseModel):
    user_id: str = "default_user"
    preference_text: str = ""


class KnowledgeItemRequest(BaseModel):
    collection: str = "general"
    title: str
    body: str
    platform: Optional[str] = None
    content_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class KnowledgeItemResponse(KnowledgeItemRequest):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
