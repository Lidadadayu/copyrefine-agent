from __future__ import annotations

from typing import Any, Dict, List, Optional


PLATFORM_NAME_MAP = {
    "xiaohongshu": "小红书",
    "wechat": "公众号",
    "zhihu": "知乎",
    "short_video": "短视频",
}

CONTENT_TYPE_NAME_MAP = {
    "product_review": "产品种草",
    "knowledge_post": "知识科普",
    "course_promotion": "课程宣传",
    "activity_promotion": "活动推广",
    "recruitment": "招聘文案",
    "brand_story": "品牌介绍",
    "video_script": "短视频脚本",
    "live_script": "直播口播",
    "user_case": "用户案例",
    "general": "通用内容",
}

TASK_TYPE_NAME_MAP = {
    "review_and_rewrite": "发布前质检 + 改写",
    "review_only": "只做风险质检",
    "title_generation": "标题生成",
}


CONTENT_TYPE_KEYWORDS = {
    "product_review": [
        "产品", "体验", "使用", "种草", "测评", "入手", "好用", "功效", "护肤",
        "效果", "购买", "下单", "价格", "包装", "成分",
    ],
    "knowledge_post": [
        "科普", "知识", "方法", "原因", "为什么", "如何", "分析", "原理", "步骤",
        "技巧", "经验", "误区", "建议",
    ],
    "course_promotion": [
        "课程", "学习", "培训", "老师", "报名", "零基础", "考试", "提升", "训练营",
        "保过", "逆袭", "课时", "资料",
    ],
    "activity_promotion": [
        "活动", "报名", "参与", "讲座", "沙龙", "直播", "福利", "名额", "时间",
        "地点", "嘉宾", "流程",
    ],
    "recruitment": [
        "招聘", "岗位", "简历", "投递", "薪资", "实习", "校招", "社招", "职责",
        "要求", "经验", "面试",
    ],
    "brand_story": [
        "品牌", "故事", "理念", "愿景", "使命", "价值", "创始", "团队", "服务",
        "用户", "长期",
    ],
    "video_script": [
        "开头", "口播", "镜头", "视频", "脚本", "三句话", "结尾", "转场", "画面",
        "钩子", "评论区",
    ],
    "live_script": [
        "直播", "主播", "话术", "福利", "下单", "库存", "限时", "讲解", "链接",
        "弹幕", "上车",
    ],
    "user_case": [
        "案例", "客户", "用户", "反馈", "前后", "使用后", "场景", "问题", "解决",
        "过程", "结果",
    ],
}


PLATFORM_STRATEGIES = {
    "xiaohongshu": {
        "tone": "真实体验、轻口语、场景化、弱营销",
        "title_style": "体验感标题、问题式标题、场景式标题",
        "structure": ["开头场景", "个人体验", "适用人群", "注意事项", "理性建议"],
        "avoid": ["绝对化承诺", "强诱导下单", "制造焦虑", "未经证实的功效"],
        "rewrite_focus": ["增强个人体验", "补充使用场景", "弱化购买指令", "增加边界说明"],
    },
    "wechat": {
        "tone": "完整、可信、逻辑清晰、解释充分",
        "title_style": "信息型标题、总结型标题、问题引导标题",
        "structure": ["背景说明", "问题分析", "分点展开", "案例或依据", "总结建议"],
        "avoid": ["标题党", "夸大承诺", "缺少依据", "恐吓式表达"],
        "rewrite_focus": ["补充逻辑结构", "增强可信表达", "增加依据说明", "减少口号化"],
    },
    "zhihu": {
        "tone": "理性、分析型、证据意识、边界清楚",
        "title_style": "问题式标题、分析型标题、判断型标题",
        "structure": ["结论前置", "原因分析", "适用条件", "反例或限制", "建议"],
        "avoid": ["营销腔", "单一结论", "无依据推荐", "极端化评价"],
        "rewrite_focus": ["区分事实和观点", "补充判断依据", "说明适合与不适合", "保持克制表达"],
    },
    "short_video": {
        "tone": "短句、口播感、节奏明确、但不夸张",
        "title_style": "短标题、钩子标题、场景冲突标题",
        "structure": ["开头钩子", "核心问题", "三点说明", "适用人群", "结尾提醒"],
        "avoid": ["恐吓钩子", "绝对效果", "强迫下单", "虚假紧迫感"],
        "rewrite_focus": ["压缩长句", "增强口播节奏", "保留吸引力", "增加理性提醒"],
    },
}


CONTENT_TYPE_STRATEGIES = {
    "product_review": {
        "core_goal": "把强推式文案改成真实体验和理性选择建议。",
        "must_have": ["使用场景", "体验感受", "适用人群", "注意事项"],
        "risk_focus": ["功效承诺", "绝对化表达", "强诱导购买"],
    },
    "knowledge_post": {
        "core_goal": "保证信息准确、结构清晰，减少焦虑和未经证实的判断。",
        "must_have": ["问题背景", "核心解释", "依据或原因", "总结建议"],
        "risk_focus": ["制造焦虑", "夸大结论", "缺少依据"],
    },
    "course_promotion": {
        "core_goal": "避免保过、速成、逆袭等结果承诺，改成学习路径和适用人群说明。",
        "must_have": ["适合人群", "课程内容", "学习方式", "效果边界"],
        "risk_focus": ["保过承诺", "速成承诺", "教育焦虑"],
    },
    "activity_promotion": {
        "core_goal": "说明活动价值、参与对象和具体安排，避免虚假紧迫感。",
        "must_have": ["活动对象", "时间地点", "核心亮点", "参与建议"],
        "risk_focus": ["虚假稀缺", "强诱导报名", "夸大收益"],
    },
    "recruitment": {
        "core_goal": "让岗位信息清晰可信，避免夸大薪资、虚假福利或歧视性表达。",
        "must_have": ["岗位职责", "能力要求", "工作方式", "投递说明"],
        "risk_focus": ["虚假薪资", "模糊承诺", "歧视性条件"],
    },
    "brand_story": {
        "core_goal": "增强品牌可信度，避免空泛口号和过度自夸。",
        "must_have": ["品牌背景", "服务对象", "核心价值", "真实案例"],
        "risk_focus": ["过度自夸", "绝对领先", "缺少事实"],
    },
    "video_script": {
        "core_goal": "提升口播节奏和转化表达，但保持合规边界。",
        "must_have": ["开头钩子", "核心内容", "转折点", "结尾行动建议"],
        "risk_focus": ["恐吓钩子", "夸张效果", "强诱导"],
    },
    "live_script": {
        "core_goal": "提升直播话术清晰度，避免虚假限时、虚假库存和过度催单。",
        "must_have": ["开场", "产品说明", "权益说明", "理性提醒"],
        "risk_focus": ["虚假稀缺", "价格误导", "强迫下单"],
    },
    "user_case": {
        "core_goal": "突出真实问题和解决过程，避免把个案包装成普遍承诺。",
        "must_have": ["用户背景", "原始问题", "解决过程", "结果边界"],
        "risk_focus": ["个案泛化", "效果承诺", "缺少限制说明"],
    },
    "general": {
        "core_goal": "提高内容清晰度、安全性和平台适配度。",
        "must_have": ["主题", "目标受众", "核心信息", "结尾建议"],
        "risk_focus": ["绝对化表达", "夸大承诺", "强诱导"],
    },
}


def normalize_platform(platform: Optional[str]) -> str:
    if platform in PLATFORM_STRATEGIES:
        return str(platform)
    return "xiaohongshu"


def normalize_content_type(content_type: Optional[str]) -> str:
    if content_type in CONTENT_TYPE_NAME_MAP:
        return str(content_type)
    return "general"


def normalize_task_type(task_type: Optional[str]) -> str:
    if task_type in TASK_TYPE_NAME_MAP:
        return str(task_type)
    return "review_and_rewrite"


def _score_keywords(content: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw and kw in content)


def infer_content_type(content: str, provided: Optional[str] = None) -> str:
    provided_norm = normalize_content_type(provided)

    scores: Dict[str, int] = {
        ctype: _score_keywords(content, keywords)
        for ctype, keywords in CONTENT_TYPE_KEYWORDS.items()
    }

    if not scores:
        return provided_norm

    # 不使用 max(scores, key=scores.get)，避免 Pylance 认为 scores.get 可能返回 None
    top_type, top_score = max(scores.items(), key=lambda item: item[1])
    provided_score = scores.get(provided_norm, 0)

    # 用户明确选择非 general 时，一般尊重用户选择；
    # 但如果文本对另一个类型有明显更强信号，则自动修正。
    if provided_norm != "general":
        if top_type != provided_norm and top_score >= max(provided_score + 2, 3):
            return top_type
        return provided_norm

    if top_score >= 2:
        return top_type

    return "general"

    scores = {
        ctype: _score_keywords(content, keywords)
        for ctype, keywords in CONTENT_TYPE_KEYWORDS.items()
    }

    top_type = max(scores, key=scores.get)
    top_score = scores[top_type]
    provided_score = scores.get(provided_norm, 0)

    # 用户明确选择非 general 时，一般尊重用户选择；
    # 但如果文本对另一个类型有明显更强信号，则自动修正。
    if provided_norm != "general":
        if top_type != provided_norm and top_score >= max(provided_score + 2, 3):
            return top_type
        return provided_norm

    if top_score >= 2:
        return top_type

    return "general"


def infer_task_type(content: str, provided: Optional[str] = None) -> str:
    provided_norm = normalize_task_type(provided)

    title_signals = ["起标题", "标题", "取标题", "标题建议", "小标题"]
    review_only_signals = ["只检查", "只质检", "不用改写", "只看风险", "风险检查"]

    if any(s in content for s in title_signals):
        return "title_generation"

    if any(s in content for s in review_only_signals):
        return "review_only"

    return provided_norm


def build_content_profile(
    content: str,
    platform: str,
    content_type: str,
    target_audience: Optional[str],
) -> Dict[str, Any]:
    length = len(content.strip())

    has_scene = any(w in content for w in ["场景", "适合", "使用时", "我在", "体验", "案例"])
    has_audience = bool(target_audience) or any(w in content for w in ["适合", "人群", "小白", "学生", "上班族", "用户"])
    has_evidence = any(w in content for w in ["因为", "数据", "案例", "反馈", "原因", "对比", "实验"])
    has_call_to_action = any(w in content for w in ["购买", "下单", "报名", "点击", "领取", "咨询", "投递"])
    has_strong_marketing = any(w in content for w in ["快冲", "必买", "闭眼入", "错过后悔", "必须入手", "全网最低"])

    if length < 40:
        length_level = "short"
    elif length <= 220:
        length_level = "medium"
    else:
        length_level = "long"

    return {
        "platform": platform,
        "platform_name": PLATFORM_NAME_MAP.get(platform, platform),
        "content_type": content_type,
        "content_type_name": CONTENT_TYPE_NAME_MAP.get(content_type, content_type),
        "target_audience": target_audience or "未指定",
        "length": length,
        "length_level": length_level,
        "has_scene": has_scene,
        "has_audience": has_audience,
        "has_evidence": has_evidence,
        "has_call_to_action": has_call_to_action,
        "has_strong_marketing": has_strong_marketing,
    }


def get_platform_strategy(
    platform: str,
    content_type: str,
    task_type: str,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    platform_strategy = PLATFORM_STRATEGIES.get(platform, PLATFORM_STRATEGIES["xiaohongshu"])
    content_strategy = CONTENT_TYPE_STRATEGIES.get(content_type, CONTENT_TYPE_STRATEGIES["general"])

    constraints = [
        "避免绝对化表达",
        "避免未经证实的效果承诺",
        "避免强诱导、恐吓式或焦虑式表达",
        "不生成规避平台审核的绕审建议",
    ]

    if not profile.get("has_scene"):
        constraints.append("补充具体使用场景或问题背景")

    if not profile.get("has_audience"):
        constraints.append("补充适用人群与不适用人群")

    if not profile.get("has_evidence"):
        constraints.append("补充依据、原因、案例或边界说明")

    if task_type == "title_generation":
        output_focus = "优先生成标题建议，不生成完整正文改写。"
    elif task_type == "review_only":
        output_focus = "只输出风险诊断、结构建议和依据，不做正文改写。"
    else:
        output_focus = "输出风险诊断、标题建议和多版本正文改写。"

    return {
        "platform_name": PLATFORM_NAME_MAP.get(platform, platform),
        "content_type_name": CONTENT_TYPE_NAME_MAP.get(content_type, content_type),
        "task_type_name": TASK_TYPE_NAME_MAP.get(task_type, task_type),
        "tone": platform_strategy["tone"],
        "title_style": platform_strategy["title_style"],
        "recommended_structure": platform_strategy["structure"],
        "platform_avoid": platform_strategy["avoid"],
        "platform_rewrite_focus": platform_strategy["rewrite_focus"],
        "content_core_goal": content_strategy["core_goal"],
        "content_must_have": content_strategy["must_have"],
        "content_risk_focus": content_strategy["risk_focus"],
        "rewrite_constraints": constraints,
        "output_focus": output_focus,
    }


def build_query_plan(
    content: str,
    platform: str,
    content_type: str,
    task_type: str,
    target_audience: Optional[str],
    keywords: List[str],
) -> List[str]:
    platform_name = PLATFORM_NAME_MAP.get(platform, platform)
    content_type_name = CONTENT_TYPE_NAME_MAP.get(content_type, content_type)
    task_type_name = TASK_TYPE_NAME_MAP.get(task_type, task_type)

    queries = [
        f"{platform_name} {content_type_name} 发布前风险规则",
        f"{platform_name} 文案风格 平台适配 结构优化",
        f"{content_type_name} 常见违规表达 风险词 功效承诺",
        f"{content_type_name} 安全改写 真实体验 适用边界",
        f"{task_type_name} 标题 正文 质检策略",
    ]

    if target_audience:
        queries.append(f"{target_audience} 内容表达 适用人群 注意事项")

    keyword_text = " ".join(keywords[:8]).strip()
    if keyword_text:
        queries.append(keyword_text)

    # 去重并保持顺序
    seen = set()
    deduped = []

    for q in queries:
        q = q.strip()
        if q and q not in seen:
            deduped.append(q)
            seen.add(q)

    return deduped