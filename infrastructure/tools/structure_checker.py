from typing import Dict


def check_structure(content: str, platform: str = "xiaohongshu") -> Dict:
    problems = []
    if len(content) < 30:
        problems.append("正文较短，缺少使用场景或具体说明。")
    if "。" not in content and "\n" not in content:
        problems.append("句子结构较单一，可以拆分为开头、正文、结尾。")
    if platform == "xiaohongshu" and not any(x in content for x in ["我", "体验", "适合", "场景", "日常"]):
        problems.append("小红书文案缺少个人体验或场景化表达。")
    if not problems:
        problems.append("基础结构较完整。")
    return {"problems": problems, "score": max(60, 100 - 10 * len(problems))}
