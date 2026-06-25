import json
import shutil
from pathlib import Path


DATA_DIR = Path("data")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            shutil.copy2(path, backup)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_platform_rules() -> list[dict]:
    rules = []

    platform_rules = {
        "xiaohongshu": [
            "小红书产品种草内容应避免绝对化表达和未经证实的功效承诺。",
            "小红书文案更适合使用真实体验、使用场景和适用边界，而不是直接强推购买。",
            "小红书内容应避免使用全网最低、必买、闭眼入、绝对安全等强营销表达。",
            "小红书产品体验内容建议包含个人使用感受、适用人群和注意事项。",
            "小红书健康、美妆、护肤相关内容不应承诺无副作用、立即见效或永久改善。",
            "小红书种草内容应减少焦虑制造和恐吓式表达。",
            "小红书标题可以突出体验和场景，但不应夸大结果。",
            "小红书内容需要区分个人体验和普遍效果，避免把个体感受写成确定结论。",
            "小红书推广内容应避免强诱导下单，如快冲、马上买、错过后悔。",
            "小红书文案建议使用口语化表达，但需要保留理性提示。",
        ],
        "wechat": [
            "公众号文章应保持信息完整、逻辑清晰，避免标题党和夸大承诺。",
            "公众号推广文案应说明适用场景、限制条件和必要说明。",
            "公众号知识类内容应注重事实准确，不应制造焦虑或恐慌。",
            "公众号内容适合采用问题引入、分点论证和总结建议的结构。",
            "公众号商业内容应避免使用稳赚、保过、百分百有效等承诺性表述。",
            "公众号文章标题应兼顾信息量和可信度，不宜过度煽动。",
            "公众号内容中涉及健康、教育、投资等主题时，应避免保证结果。",
            "公众号长文建议增强案例、解释和边界说明。",
            "公众号文案应减少直接命令式购买表达。",
            "公众号内容可以强调价值，但应避免绝对化结论。",
        ],
        "zhihu": [
            "知乎内容应保持理性分析和证据意识，避免单纯营销式表达。",
            "知乎回答适合解释原因、适用条件、优缺点和决策建议。",
            "知乎知识科普内容应避免未经证实的结论和恐吓式表达。",
            "知乎标题适合采用问题式表达，但不应制造夸张冲突。",
            "知乎内容需要区分事实、观点和个人经验。",
            "知乎回答中涉及产品推荐时，应说明适合谁、不适合谁。",
            "知乎内容应避免无依据地声称最佳、唯一、绝对有效。",
            "知乎风格更适合客观、克制、分析型表达。",
            "知乎内容应减少强促销词汇，增强信息可信度。",
            "知乎内容需要给出判断依据，而不是只给结论。",
        ],
        "short_video": [
            "短视频脚本需要开头清晰，但不应使用恐吓式钩子。",
            "短视频带货文案应避免绝对功效承诺和强诱导购买。",
            "短视频内容适合突出场景、痛点和体验，但要避免夸大效果。",
            "短视频标题可以简洁有冲击力，但不能制造虚假预期。",
            "短视频内容应避免使用马上见效、永久改善、百分百有效等表达。",
            "短视频口播建议加入理性选择和适用人群说明。",
            "短视频推广内容不应以焦虑驱动用户购买。",
            "短视频脚本可以使用悬念，但不得误导用户。",
            "短视频商品介绍应说明使用边界和注意事项。",
            "短视频内容需要在吸引力和合规性之间保持平衡。",
        ],
    }

    idx = 1
    for platform, texts in platform_rules.items():
        for text in texts:
            rules.append(
                {
                    "id": f"rule_{idx:03d}",
                    "platform": platform,
                    "content_type": "general",
                    "category": "platform_rule",
                    "text": text,
                }
            )
            idx += 1

    return rules


def build_risk_expressions() -> list[dict]:
    base = [
        ("绝对", "absolute_claim", "high", "避免绝对化表达，改成相对、体验型描述。"),
        ("百分百", "absolute_claim", "high", "避免承诺百分百结果。"),
        ("100%", "absolute_claim", "high", "避免承诺百分百结果。"),
        ("一定", "absolute_claim", "medium", "减少确定性承诺，改成可能、通常、体验上。"),
        ("必买", "strong_inducement", "medium", "降低强诱导语气，改成理性选择建议。"),
        ("闭眼入", "strong_inducement", "medium", "避免无条件推荐，补充适用条件。"),
        ("快冲", "strong_inducement", "medium", "减少强促销表达，改成根据需求选择。"),
        ("错过后悔", "fear_marketing", "medium", "避免制造焦虑或损失恐惧。"),
        ("全网最低", "price_claim", "high", "价格类结论需要证据，不建议直接承诺最低。"),
        ("稳赚", "financial_claim", "high", "投资或收益相关内容不得承诺稳赚。"),
        ("保过", "education_claim", "high", "教育培训内容不得承诺通过结果。"),
        ("逆袭", "anxiety_marketing", "medium", "避免制造焦虑，可改为提升、改善、积累。"),
        ("无副作用", "health_claim", "high", "健康相关内容不要承诺无副作用。"),
        ("7天见效", "effect_claim", "high", "避免承诺具体时间内的效果。"),
        ("立刻见效", "effect_claim", "high", "避免即时效果承诺。"),
        ("永久改善", "effect_claim", "high", "避免永久性效果承诺。"),
        ("根治", "medical_claim", "high", "医疗健康相关内容不得承诺根治。"),
        ("治愈", "medical_claim", "high", "避免使用医疗效果承诺词。"),
        ("最强", "absolute_claim", "medium", "避免最高级表达，改成体验较好或适合某类场景。"),
        ("第一", "absolute_claim", "medium", "排名类表达需要证据支撑。"),
        ("唯一", "absolute_claim", "high", "避免唯一性结论。"),
        ("神器", "overstatement", "medium", "减少夸大表达，改成具体功能描述。"),
        ("吊打", "comparison_claim", "medium", "避免攻击式比较，改成差异化说明。"),
        ("碾压", "comparison_claim", "medium", "避免夸张比较，提供具体维度。"),
        ("智商税", "negative_attack", "medium", "避免攻击性表达，改成不适合某类需求。"),
        ("不买亏", "strong_inducement", "medium", "避免强诱导购买。"),
        ("必须入手", "strong_inducement", "medium", "改成适合某类用户考虑。"),
        ("秒杀", "overstatement", "medium", "避免夸张效果或价格表达。"),
        ("爆瘦", "health_claim", "high", "健康体重相关内容避免夸张效果承诺。"),
        ("安全无害", "health_claim", "high", "安全性表述需要边界，避免绝对承诺。"),
        ("没有风险", "absolute_claim", "high", "避免承诺完全无风险。"),
        ("人人适用", "absolute_claim", "high", "补充适用人群和不适用情况。"),
        ("小白必看", "mild_inducement", "low", "可保留，但建议避免过度焦虑化。"),
        ("最后机会", "fear_marketing", "medium", "避免制造紧迫焦虑。"),
        ("内部渠道", "credibility_risk", "medium", "避免暗示非正规渠道或虚假背书。"),
    ]

    rows = []
    for idx, item in enumerate(base, 1):
        text, risk_type, severity, suggestion = item
        rows.append(
            {
                "id": f"risk_{idx:03d}",
                "text": text,
                "risk_type": risk_type,
                "severity": severity,
                "suggestion": suggestion,
            }
        )
    return rows


def build_content_cases() -> list[dict]:
    cases = [
        {
            "platform": "xiaohongshu",
            "content_type": "product_review",
            "title": "这份体验分享，适合正在犹豫的你",
            "body": "最近体验了一款产品，整体感受是更适合有明确需求的人。它的优势在于使用场景清晰，但实际体验会因人而异，建议结合自己的情况判断。",
            "reason": "使用真实体验、使用场景和适用边界，避免直接强推购买。",
        },
        {
            "platform": "xiaohongshu",
            "content_type": "product_review",
            "title": "使用前先看看：真实体验和注意点",
            "body": "这次主要从使用感受、适用人群和注意事项三个方面分享。它不是适合所有人，但对某些场景确实有参考价值。",
            "reason": "强调适用边界，避免绝对化种草。",
        },
        {
            "platform": "xiaohongshu",
            "content_type": "knowledge_post",
            "title": "别被焦虑带着走，先弄清这几个问题",
            "body": "在选择前，可以先看需求是否真实存在、产品是否匹配场景、是否有必要长期使用。理性判断比盲目跟风更重要。",
            "reason": "适合知识科普内容，减少焦虑制造。",
        },
        {
            "platform": "wechat",
            "content_type": "knowledge_post",
            "title": "理性选择这类产品，需要关注哪些细节？",
            "body": "判断一款产品是否适合自己，可以从使用场景、成本、预期效果和风险提示四个方面分析。不要只看单一卖点。",
            "reason": "公众号风格更完整，强调分析框架。",
        },
        {
            "platform": "wechat",
            "content_type": "course_promotion",
            "title": "课程适合谁？报名前先看这几点",
            "body": "这门课程更适合有明确学习目标、愿意持续练习的人。课程可以帮助提升学习效率，但最终效果仍取决于个人投入。",
            "reason": "避免保过、速成等教育承诺。",
        },
        {
            "platform": "wechat",
            "content_type": "activity_promotion",
            "title": "活动亮点与参与建议",
            "body": "本次活动主要面向对主题感兴趣的用户，适合希望了解基础信息和实际案例的人。建议根据时间和需求安排参与。",
            "reason": "活动推广保持清晰和克制。",
        },
        {
            "platform": "zhihu",
            "content_type": "product_review",
            "title": "这类产品是否值得尝试？需要先看哪些因素",
            "body": "是否值得尝试，取决于需求强度、使用场景和可接受成本。不能只看宣传语，还要看它解决的是不是自己的真实问题。",
            "reason": "知乎适合分析型表达。",
        },
        {
            "platform": "zhihu",
            "content_type": "knowledge_post",
            "title": "如何理性看待这类产品的使用体验？",
            "body": "个体体验不等于普遍结论。更合理的判断方式是看证据、看适用条件，也看不适合的情况。",
            "reason": "区分事实、观点和个人经验。",
        },
        {
            "platform": "zhihu",
            "content_type": "course_promotion",
            "title": "学习效果为什么不能简单承诺？",
            "body": "学习结果受到基础、时间投入、练习质量和反馈机制影响。课程可以提供路径和方法，但不能替代个人持续投入。",
            "reason": "避免教育培训结果承诺。",
        },
        {
            "platform": "short_video",
            "content_type": "product_review",
            "title": "别急着下单，先看这几个细节",
            "body": "先看它适合什么场景，再看自己是否真的需要。体验分享可以参考，但不要把别人的结果直接当成自己的结果。",
            "reason": "适合短视频开头，同时避免强诱导。",
        },
        {
            "platform": "short_video",
            "content_type": "knowledge_post",
            "title": "三句话讲清楚：适合谁，不适合谁",
            "body": "第一，适合有明确需求的人。第二，不适合期待立刻改变的人。第三，选择前先看场景和预算。",
            "reason": "短视频脚本简洁，结构清晰。",
        },
        {
            "platform": "short_video",
            "content_type": "activity_promotion",
            "title": "这个活动适合哪些人参加？",
            "body": "适合想快速了解主题、获取基础信息和案例的人。如果你已经有系统经验，可以重点关注交流环节。",
            "reason": "活动推广避免夸大收益。",
        },
    ]

    rows = []
    idx = 1

    # 原始案例
    for case in cases:
        row = dict(case)
        row["id"] = f"case_{idx:03d}"
        rows.append(row)
        idx += 1

    # 扩展一些通用案例，增加检索多样性
    platforms = ["xiaohongshu", "wechat", "zhihu", "short_video"]
    content_types = ["product_review", "knowledge_post", "course_promotion", "activity_promotion"]

    for platform in platforms:
        for content_type in content_types:
            rows.append(
                {
                    "id": f"case_{idx:03d}",
                    "platform": platform,
                    "content_type": content_type,
                    "title": "从真实需求出发，而不是被宣传语带着走",
                    "body": "这类内容更适合从真实需求、使用场景、适用边界和注意事项展开。表达上可以保留推荐语气，但不要使用绝对化承诺或制造焦虑。",
                    "reason": "通用安全表达案例，适合多数平台和内容类型。",
                }
            )
            idx += 1

            rows.append(
                {
                    "id": f"case_{idx:03d}",
                    "platform": platform,
                    "content_type": content_type,
                    "title": "适合谁、不适合谁，讲清楚比强推更重要",
                    "body": "推荐内容不一定要强推购买。更可信的方式是说明适合的人群、不适合的人群、可能的体验差异和选择建议。",
                    "reason": "增强可信度和平台适配度。",
                }
            )
            idx += 1

    return rows


def build_seed_history() -> list[dict]:
    return [
        {
            "id": "history_001",
            "user_id": "default_user",
            "platform": "xiaohongshu",
            "content_type": "product_review",
            "title": "使用前先看这几点",
            "body": "这类产品更适合有明确需求的人，建议结合自身情况判断，不要只看单一卖点。",
        },
        {
            "id": "history_002",
            "user_id": "default_user",
            "platform": "wechat",
            "content_type": "knowledge_post",
            "title": "理性判断比盲目跟风更重要",
            "body": "内容发布前应检查事实依据、适用边界和潜在风险表达，避免夸大承诺。",
        },
        {
            "id": "history_003",
            "user_id": "default_user",
            "platform": "zhihu",
            "content_type": "knowledge_post",
            "title": "如何判断一个推荐是否可靠",
            "body": "可靠的推荐通常会说明使用条件、限制和替代方案，而不是只强调优势。",
        },
    ]


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    rules = build_platform_rules()
    risks = build_risk_expressions()
    cases = build_content_cases()
    history = build_seed_history()

    write_jsonl(DATA_DIR / "platform_rules.jsonl", rules)
    write_jsonl(DATA_DIR / "risk_expressions.jsonl", risks)
    write_jsonl(DATA_DIR / "content_cases.jsonl", cases)
    write_jsonl(DATA_DIR / "seed_history.jsonl", history)

    print("Knowledge base expanded.")
    print(f"platform_rules: {len(rules)}")
    print(f"risk_expressions: {len(risks)}")
    print(f"content_cases: {len(cases)}")
    print(f"seed_history: {len(history)}")


if __name__ == "__main__":
    main()