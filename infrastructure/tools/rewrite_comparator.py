from __future__ import annotations

from typing import Any, Dict, List

from infrastructure.tools.risk_matcher import match_risks
from infrastructure.strategy.content_strategy import build_content_profile


def _risk_terms(risks: List[Dict[str, Any]]) -> set[str]:
    return {str(item.get("text", "")).strip() for item in risks if item.get("text")}


def _readability_features(text: str) -> Dict[str, Any]:
    clean = text.strip()
    paragraphs = [p for p in clean.splitlines() if p.strip()]
    sentences = [
        s for s in clean.replace("！", "。").replace("？", "。").split("。")
        if s.strip()
    ]

    long_sentence_count = sum(1 for s in sentences if len(s) > 60)

    return {
        "length": len(clean),
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "long_sentence_count": long_sentence_count,
        "has_paragraphs": len(paragraphs) >= 2,
    }


def _structure_gains(
    original_profile: Dict[str, Any],
    rewritten_profile: Dict[str, Any],
) -> List[str]:
    gains: List[str] = []

    if not original_profile.get("has_scene") and rewritten_profile.get("has_scene"):
        gains.append("补充了使用场景或体验语境。")

    if not original_profile.get("has_audience") and rewritten_profile.get("has_audience"):
        gains.append("补充了适用人群或选择边界。")

    if not original_profile.get("has_evidence") and rewritten_profile.get("has_evidence"):
        gains.append("补充了原因、依据或说明性表达。")

    if original_profile.get("has_strong_marketing") and not rewritten_profile.get("has_strong_marketing"):
        gains.append("弱化了强营销和催促购买语气。")

    if not gains:
        gains.append("结构变化不明显，主要进行了风险表达弱化和语气调整。")

    return gains


def compare_one_version(
    original_content: str,
    version: Dict[str, Any],
    platform: str,
    content_type: str,
    target_audience: str | None = None,
) -> Dict[str, Any]:
    title = str(version.get("title", "")).strip()
    body = str(version.get("body", "")).strip()
    combined = f"{title}\n{body}".strip()

    original_risks = match_risks(original_content)
    rewritten_risks = match_risks(combined)

    original_terms = _risk_terms(original_risks)
    rewritten_terms = _risk_terms(rewritten_risks)

    removed_terms = sorted(original_terms - rewritten_terms)
    remaining_terms = sorted(original_terms & rewritten_terms)
    new_terms = sorted(rewritten_terms - original_terms)

    original_profile = build_content_profile(
        content=original_content,
        platform=platform,
        content_type=content_type,
        target_audience=target_audience,
    )
    rewritten_profile = build_content_profile(
        content=combined,
        platform=platform,
        content_type=content_type,
        target_audience=target_audience,
    )

    original_readability = _readability_features(original_content)
    rewritten_readability = _readability_features(combined)

    gains = _structure_gains(original_profile, rewritten_profile)

    if new_terms:
        publish_status = "need_review"
        publish_suggestion = "改写版本引入了新的风险表达，建议人工复查后再发布。"
    elif remaining_terms:
        publish_status = "need_revision"
        publish_suggestion = "改写版本仍残留部分原始风险表达，建议继续弱化。"
    elif removed_terms:
        publish_status = "ready"
        publish_suggestion = "主要风险表达已被移除，建议结合平台语气进行最终人工确认。"
    else:
        publish_status = "ready"
        publish_suggestion = "未发现明显风险残留，可作为候选发布版本。"

    return {
        "version_type": version.get("version_type", "version"),
        "title": title,
        "score": version.get("score", 0),
        "removed_risk_terms": removed_terms,
        "remaining_risk_terms": remaining_terms,
        "new_risk_terms": new_terms,
        "original_risk_count": len(original_risks),
        "rewritten_risk_count": len(rewritten_risks),
        "structure_gains": gains,
        "readability": {
            "original": original_readability,
            "rewritten": rewritten_readability,
            "length_delta": rewritten_readability["length"] - original_readability["length"],
            "paragraph_delta": rewritten_readability["paragraph_count"] - original_readability["paragraph_count"],
            "long_sentence_delta": rewritten_readability["long_sentence_count"] - original_readability["long_sentence_count"],
        },
        "publish_status": publish_status,
        "publish_suggestion": publish_suggestion,
    }


def compare_rewrite_versions(
    original_content: str,
    versions: List[Dict[str, Any]],
    platform: str,
    content_type: str,
    target_audience: str | None = None,
) -> List[Dict[str, Any]]:
    comparisons: List[Dict[str, Any]] = []

    for version in versions:
        body = str(version.get("body", "")).strip()

        # title_generation 场景下可能没有正文改写版本
        if not body:
            continue

        comparisons.append(
            compare_one_version(
                original_content=original_content,
                version=version,
                platform=platform,
                content_type=content_type,
                target_audience=target_audience,
            )
        )

    return comparisons