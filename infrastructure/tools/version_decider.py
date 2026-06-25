from __future__ import annotations

from typing import Any, Dict, List, Tuple

from infrastructure.tools.risk_matcher import match_risks
from infrastructure.tools.rewrite_comparator import compare_rewrite_versions


SAFE_REPLACEMENTS = {
    "绝对安全": "使用体验相对温和",
    "安全无害": "使用感受因人而异，建议结合自身情况判断",
    "无副作用": "使用感受因人而异，建议结合自身情况判断",
    "7天见效": "坚持使用后可能逐步感受到变化",
    "立刻见效": "可能需要结合实际情况持续观察",
    "永久改善": "可能在一定程度上带来体验变化",
    "根治": "改善相关体验",
    "治愈": "改善相关体验",
    "保过": "有助于提升学习准备效率",
    "稳赚": "存在不确定性，需要理性判断",
    "没有风险": "需要结合实际情况评估风险",
    "100%": "较大程度上",
    "百分百": "较大程度上",
    "全网最低": "价格相对有优势",
    "闭眼入": "适合有相关需求的用户考虑",
    "必须入手": "可以根据自己的需求理性选择",
    "必买": "可以根据自己的需求理性选择",
    "快冲": "可以根据自己的需求理性选择",
    "大家快冲": "可以根据自己的需求理性选择",
    "错过后悔": "建议根据实际需求判断是否适合",
    "逆袭": "逐步提升",
}


STATUS_PRIORITY = {
    "ready": 3,
    "need_revision": 2,
    "need_review": 1,
    "unknown": 0,
}


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """
    对标题或正文做安全修复。

    返回：
    - 修复后的文本
    - 被替换的风险表达列表
    """
    if not text:
        return "", []

    repaired = text
    changed_terms: List[str] = []

    for risky, safe in SAFE_REPLACEMENTS.items():
        if risky in repaired:
            repaired = repaired.replace(risky, safe)
            changed_terms.append(risky)

    return repaired, changed_terms


def sanitize_title_suggestions(titles: List[str]) -> Tuple[List[str], List[str]]:
    cleaned: List[str] = []
    changed_terms: List[str] = []

    for title in titles:
        safe_title, changed = sanitize_text(str(title))
        safe_title = safe_title.strip()

        if safe_title and safe_title not in cleaned:
            cleaned.append(safe_title)

        changed_terms.extend(changed)

    return cleaned[:5], sorted(set(changed_terms))


def _compute_decision_score(
    version: Dict[str, Any],
    comparison: Dict[str, Any] | None,
) -> int:
    base_score = int(version.get("score", 70))

    remaining_risks = version.get("remaining_risks", []) or []
    remaining_count = len(remaining_risks)

    decision_score = base_score

    # 风险残留是最重要的扣分项
    decision_score -= remaining_count * 18

    if comparison:
        removed_count = len(comparison.get("removed_risk_terms", []) or [])
        new_count = len(comparison.get("new_risk_terms", []) or [])
        remaining_terms_count = len(comparison.get("remaining_risk_terms", []) or [])

        decision_score += removed_count * 6
        decision_score -= new_count * 20
        decision_score -= remaining_terms_count * 12

        readability = comparison.get("readability", {}) or {}
        long_sentence_delta = readability.get("long_sentence_delta", 0)
        paragraph_delta = readability.get("paragraph_delta", 0)

        if long_sentence_delta < 0:
            decision_score += 4

        if paragraph_delta > 0:
            decision_score += 4

    return max(0, min(100, int(decision_score)))


def _status_from_risks(
    remaining_risks: List[Dict[str, Any]],
    comparison: Dict[str, Any] | None,
) -> str:
    if comparison:
        if comparison.get("new_risk_terms"):
            return "need_review"

        if comparison.get("remaining_risk_terms"):
            return "need_revision"

    if remaining_risks:
        return "need_revision"

    return "ready"


def _suggestion_from_status(status: str) -> str:
    if status == "ready":
        return "该版本主要风险表达已被移除，可作为候选发布版本，但建议发布前人工确认。"

    if status == "need_revision":
        return "该版本仍存在少量风险残留，建议继续弱化后再发布。"

    if status == "need_review":
        return "该版本可能引入新的风险表达，建议人工复核后再使用。"

    return "该版本状态未知，建议人工复查。"


def decide_versions(
    original_content: str,
    versions: List[Dict[str, Any]],
    platform: str,
    content_type: str,
    target_audience: str | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    对改写版本进行：
    1. 自动风险词修复
    2. 二次风险检测
    3. 改写对比
    4. 版本排序
    5. 推荐最佳版本
    """
    processed_versions: List[Dict[str, Any]] = []
    auto_repair_records: List[Dict[str, Any]] = []

    for index, version in enumerate(versions):
        item = dict(version)

        old_title = str(item.get("title", "")).strip()
        old_body = str(item.get("body", "")).strip()

        new_title, changed_title_terms = sanitize_text(old_title)
        new_body, changed_body_terms = sanitize_text(old_body)

        changed_terms = sorted(set(changed_title_terms + changed_body_terms))

        item["title"] = new_title
        item["body"] = new_body

        remaining_risks = match_risks(f"{new_title}\n{new_body}")

        item["guard_passed"] = len(remaining_risks) == 0
        item["remaining_risks"] = remaining_risks
        item["auto_repaired"] = bool(changed_terms)
        item["auto_repair_terms"] = changed_terms

        if changed_terms:
            old_notes = item.get("notes", "")
            item["notes"] = f"{old_notes} 已自动弱化风险表达：{'、'.join(changed_terms)}。".strip()

            auto_repair_records.append(
                {
                    "version_index": index,
                    "version_type": item.get("version_type", "version"),
                    "changed_terms": changed_terms,
                }
            )

        processed_versions.append(item)

    comparisons = compare_rewrite_versions(
        original_content=original_content,
        versions=processed_versions,
        platform=platform,
        content_type=content_type,
        target_audience=target_audience,
    )

    # compare_rewrite_versions 会跳过无 body 的版本，所以这里按 version_type 做弱匹配
    comparison_by_type: Dict[str, Dict[str, Any]] = {
        str(item.get("version_type", "")): item for item in comparisons
    }

    ranked_versions: List[Dict[str, Any]] = []

    for version in processed_versions:
        version_type = str(version.get("version_type", ""))
        comparison = comparison_by_type.get(version_type)

        status = _status_from_risks(version.get("remaining_risks", []) or [], comparison)
        decision_score = _compute_decision_score(version, comparison)

        version["publish_status"] = status
        version["publish_suggestion"] = _suggestion_from_status(status)
        version["decision_score"] = decision_score

        ranked_versions.append(version)

    ranked_versions.sort(
        key=lambda v: (
            STATUS_PRIORITY.get(v.get("publish_status", "unknown"), 0),
            int(v.get("decision_score", 0)),
            int(v.get("score", 0)),
        ),
        reverse=True,
    )

    recommended_version = ranked_versions[0] if ranked_versions else None

    decision_pack = {
        "has_versions": bool(processed_versions),
        "auto_repair_records": auto_repair_records,
        "recommended_version": recommended_version,
        "ranking": [
            {
                "version_type": v.get("version_type"),
                "title": v.get("title"),
                "score": v.get("score"),
                "decision_score": v.get("decision_score"),
                "publish_status": v.get("publish_status"),
                "guard_passed": v.get("guard_passed"),
                "auto_repaired": v.get("auto_repaired"),
                "publish_suggestion": v.get("publish_suggestion"),
            }
            for v in ranked_versions
        ],
    }

    return processed_versions, comparisons, decision_pack