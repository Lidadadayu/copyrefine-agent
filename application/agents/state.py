from typing import Any, Dict, List, Optional, TypedDict


class ContentPilotState(TypedDict, total=False):
    task_id: str
    user_id: str
    raw_content: str
    platform: Optional[str]
    content_type: Optional[str]
    task_type: Optional[str]
    target_audience: Optional[str]
    rewrite_intensity: str
    expression_strength: str
    platforms: List[str]
    refine_instruction: Optional[str]
    parent_task_id: Optional[str]
    conversation_id: Optional[str]
    original_content: Optional[str]
    previous_output: Optional[str]
    user_preference: Optional[str]

    intent: Optional[str]
    detected_platform: Optional[str]
    detected_content_type: Optional[str]
    risk_sensitive: bool
    need_retrieval: bool
    need_rewrite: bool
    need_history: bool

    rewritten_queries: List[str]
    retrieval_routes: List[str]

    retrieved_rules: List[Dict[str, Any]]
    retrieved_risks: List[Dict[str, Any]]
    retrieved_cases: List[Dict[str, Any]]
    retrieved_history: List[Dict[str, Any]]
    
    keywords: List[str]
    content_profile: Dict[str, Any]
    explicit_style_request: bool
    style_profile: Dict[str, Any]
    platform_strategy: Dict[str, Any]
    rewrite_constraints: List[str]

    evidence_pack: Dict[str, Any]
    quality_scores: Dict[str, Any]
    rewrite_comparison: List[Dict[str, Any]]
    version_decision_pack: Dict[str, Any]
    recommended_version: Dict[str, Any]

    risk_report: Dict[str, Any]
    structure_report: Dict[str, Any]
    style_report: Dict[str, Any]

    title_suggestions: List[str]
    rewritten_versions: List[Dict[str, Any]]
    final_report: str
    score: int
    risk_level: str

    trace: List[Dict[str, Any]]
    errors: List[str]
