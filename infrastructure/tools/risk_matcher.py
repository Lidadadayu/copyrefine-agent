import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_RISK_RULES = [
    {"text": "绝对", "risk_type": "absolute_claim", "severity": "high", "suggestion": "避免绝对化表达，改成相对、体验型描述。"},
    {"text": "百分百", "risk_type": "absolute_claim", "severity": "high", "suggestion": "避免承诺百分百结果。"},
    {"text": "100%", "risk_type": "absolute_claim", "severity": "high", "suggestion": "避免承诺百分百结果。"},
    {"text": "一定", "risk_type": "absolute_claim", "severity": "medium", "suggestion": "减少确定性承诺，改成可能、通常、体验上。"},
    {"text": "无副作用", "risk_type": "health_claim", "severity": "high", "suggestion": "健康相关内容不要承诺无副作用。"},
    {"text": "安全无害", "risk_type": "health_claim", "severity": "high", "suggestion": "安全性表述需要边界，避免绝对承诺。"},
    {"text": "7天见效", "risk_type": "effect_claim", "severity": "high", "suggestion": "避免承诺具体时间内的效果。"},
    {"text": "立刻见效", "risk_type": "effect_claim", "severity": "high", "suggestion": "避免即时效果承诺。"},
    {"text": "永久改善", "risk_type": "effect_claim", "severity": "high", "suggestion": "避免永久性效果承诺。"},
    {"text": "根治", "risk_type": "medical_claim", "severity": "high", "suggestion": "医疗健康相关内容不得承诺根治。"},
    {"text": "治愈", "risk_type": "medical_claim", "severity": "high", "suggestion": "避免使用医疗效果承诺词。"},
    {"text": "保过", "risk_type": "education_claim", "severity": "high", "suggestion": "教育培训内容不得承诺通过结果。"},
    {"text": "稳赚", "risk_type": "financial_claim", "severity": "high", "suggestion": "投资或收益相关内容不得承诺稳赚。"},
    {"text": "没有风险", "risk_type": "absolute_claim", "severity": "high", "suggestion": "避免承诺完全无风险。"},
    {"text": "全网最低", "risk_type": "price_claim", "severity": "high", "suggestion": "价格类结论需要证据，不建议直接承诺最低。"},
    {"text": "闭眼入", "risk_type": "strong_inducement", "severity": "medium", "suggestion": "避免无条件推荐，补充适用条件。"},
    {"text": "必须入手", "risk_type": "strong_inducement", "severity": "medium", "suggestion": "改成适合某类用户考虑。"},
    {"text": "必买", "risk_type": "strong_inducement", "severity": "medium", "suggestion": "降低强诱导语气，改成理性选择建议。"},
    {"text": "快冲", "risk_type": "strong_inducement", "severity": "medium", "suggestion": "减少强促销表达，改成根据需求选择。"},
    {"text": "错过后悔", "risk_type": "fear_marketing", "severity": "medium", "suggestion": "避免制造焦虑或损失恐惧。"},
    {"text": "逆袭", "risk_type": "anxiety_marketing", "severity": "medium", "suggestion": "避免制造焦虑，可改为提升、改善、积累。"},
]


NEGATION_WORDS = [
    "不要",
    "避免",
    "不能",
    "不得",
    "不建议",
    "减少",
    "弱化",
    "禁止",
]


@lru_cache(maxsize=1)
def load_risk_rules() -> List[Dict[str, Any]]:
    path = Path("data/risk_expressions.jsonl")

    if not path.exists():
        return DEFAULT_RISK_RULES

    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except Exception:
                continue

            if row.get("text") and row.get("risk_type") and row.get("severity"):
                rows.append(row)

    if not rows:
        return DEFAULT_RISK_RULES

    merged: Dict[str, Dict[str, Any]] = {}

    for row in DEFAULT_RISK_RULES + rows:
        merged[row["text"]] = row

    return list(merged.values())


def _is_negated_context(content: str, start_index: int) -> bool:
    """
    避免把“不要使用绝对化表达”“避免承诺无副作用”这种说明性文本误判为风险。

    例如：
    - “绝对安全，无副作用” 应该命中风险
    - “不要写绝对安全、无副作用” 可以视为说明性文本，不作为高风险命中
    """
    left = content[max(0, start_index - 8): start_index]

    return any(word in left for word in NEGATION_WORDS)


def match_risks(content: str) -> List[Dict[str, Any]]:
    if not content:
        return []

    rules = load_risk_rules()
    matched: List[Dict[str, Any]] = []
    seen = set()

    for rule in rules:
        term = str(rule.get("text", "")).strip()
        if not term:
            continue

        start = content.find(term)

        while start != -1:
            key = (term, rule.get("risk_type"))

            if key not in seen and not _is_negated_context(content, start):
                matched.append(
                    {
                        "text": term,
                        "risk_type": rule.get("risk_type", "unknown"),
                        "severity": rule.get("severity", "medium"),
                        "suggestion": rule.get("suggestion", "建议弱化该表达，补充边界说明。"),
                    }
                )
                seen.add(key)
                break

            start = content.find(term, start + len(term))

    severity_rank = {"high": 3, "medium": 2, "low": 1}

    matched.sort(
        key=lambda x: severity_rank.get(x.get("severity", "low"), 1),
        reverse=True,
    )

    return matched