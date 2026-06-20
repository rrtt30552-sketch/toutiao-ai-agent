"""文章生成器 V8.2：Few-shot Prompt + 配置化。"""

import json
from typing import Dict, List, Optional

from modules.ai_client import call_ai_safe
from modules.logger import log_info, log_ok, log_warn, log_step

STEP = "write"

DEFAULT_CONFIG = {
    "target_audience": "中年人群",
    "content_domain": "生活故事、人生感悟",
    "writing_style": "真实、克制、不煽情不矫情",
}

ARTICLE_PROMPT = """你是一个今日头条爆款文章写手，专门写{audience}的{domain}。

【任务】
根据以下策略和参考数据，写一篇今日头条文章。

【当前策略】{strategy}

【该策略的历史爆款标题（供参考，不要抄袭）】
{top_titles}

【该策略的低表现标题（引以为戒，避免类似写法）】
{worst_titles}

【该策略的关键数据】
- 平均阅读量：{avg_reads}
- 平均展现量：{avg_impressions}
- 代表文章：{representative}

【该策略的数据画像】{data_profile}

【写作要求】
1. 标题：15-25字，必须有具体数字或年龄，制造画面感和悬念
2. 正文：800-1500字，分段清晰，每段2-3句话
3. 开头3句话必须抓住读者（制造冲突/悬念/共鸣）
4. 结尾要有回味，金句收束
5. 语气：{style}
6. 禁止使用"震惊""泪目""速看"等标题党词汇
7. 重点关注高完成率文章的写作技巧
8. 回避低表现文章的写法和标题风格

【评分标准】
emotion_score（情感强度）：0=平淡，50=有共鸣，85=催泪。建议60-85。
viral_score（传播潜力）：0=小众，50=有传播性，90=全网爆款。建议50-90。

【输出格式】
严格输出 JSON，不要加任何其他内容：

示例：
{{
  "title": "58岁退休后，我终于活成了自己讨厌的样子",
  "alt_titles": ["退休三年，我才发现前半生白活了", "58岁那年，我做了一个让全家反对的决定"],
  "body": "退休那天，同事们给我办了一个简单的欢送会。\\n\\n我笑着说终于自由了，心里却空落落的。\\n\\n回到家，老伴在厨房忙活，问我晚上想吃什么。我说随便。\\n\\n这个'随便'，就是我接下来三年的缩影。",
  "emotion_score": 72,
  "viral_score": 85
}}

现在请根据以上数据生成文章，严格输出 JSON："""


def _load_config() -> Dict:
    import os
    config_path = "config.json"
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def generate_article(strategy: str, articles: List[Dict], strategy_stats: Dict) -> Optional[Dict]:
    log_info(STEP, f"生成文章 [策略: {strategy}]")

    config = _load_config()
    strategy_articles = [a for a in articles if a.get("content_type") == strategy]

    sorted_articles = sorted(strategy_articles, key=lambda a: a.get("reads", 0), reverse=True)
    top_titles = "\n".join([
        f"- {a['title']} (阅读:{a.get('reads', 0)}, 展现:{a.get('impressions', 0)})"
        for a in sorted_articles[:5]
    ]) or "暂无历史数据"

    worst_articles = sorted(strategy_articles, key=lambda a: a.get("reads", 0))
    worst_titles = "\n".join([
        f"- {a['title']} (阅读:{a.get('reads', 0)}, 展现:{a.get('impressions', 0)})"
        for a in worst_articles[:5]
    ]) or "暂无"

    if strategy_articles:
        avg_reads = int(sum(a.get("reads", 0) for a in strategy_articles) / len(strategy_articles))
        avg_imp = int(sum(a.get("impressions", 0) for a in strategy_articles) / len(strategy_articles))
    else:
        avg_reads = avg_imp = 0

    rep = sorted_articles[0] if sorted_articles else None
    representative = f"「{rep['title']}」(阅读:{rep.get('reads', 0)})" if rep else "暂无"

    data_profile = _build_data_profile(strategy_articles)

    prompt = ARTICLE_PROMPT.format(
        audience=config["target_audience"],
        domain=config["content_domain"],
        style=config["writing_style"],
        strategy=strategy,
        top_titles=top_titles,
        worst_titles=worst_titles,
        avg_reads=avg_reads,
        avg_impressions=avg_imp,
        representative=representative,
        data_profile=data_profile,
    )

    result = call_ai_safe(prompt, fallback="", max_tokens=4096, timeout=180)
    if not result:
        log_warn(STEP, "AI 返回空内容")
        return None

    article = _parse_article(result)
    if not article:
        article = _fallback_parse(result)

    if article:
        article.setdefault("content_type", strategy)
        article.setdefault("impressions", 0)
        article.setdefault("reads", 0)
        article.setdefault("likes", 0)
        article.setdefault("comments", 0)
        article.setdefault("shares", 0)
        from datetime import datetime
        article.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        log_ok(STEP, f"生成成功: {article.get('title', 'N/A')[:40]}")
    else:
        log_warn(STEP, "所有解析方式均失败")

    return article


def _build_data_profile(articles: List[Dict]) -> str:
    if not articles:
        return "暂无数据，请根据常识写作"

    ctr_list = []
    comp_list = []
    fav_list = []

    for a in articles:
        imp = max(a.get("impressions", 0), 1)
        reads = a.get("reads", 0)
        ctr_list.append(reads / imp)
        comp = a.get("avg_completion_rate", 0)
        if comp:
            comp_list.append(comp)
        favs = a.get("favorites", 0)
        if favs:
            fav_list.append(favs / imp)

    lines = []
    if ctr_list:
        lines.append(f"- 平均点击率：{sum(ctr_list)/len(ctr_list)*100:.1f}%")
    if comp_list:
        lines.append(f"- 平均完成率：{sum(comp_list)/len(comp_list):.1f}%")
    if fav_list:
        lines.append(f"- 平均收藏率：{sum(fav_list)/len(fav_list)*100:.2f}%")

    high_comp = [a for a in articles if a.get("avg_completion_rate", 0) >= 50]
    if high_comp:
        best = max(high_comp, key=lambda x: x.get("avg_completion_rate", 0))
        lines.append(f"- 高完成率案例：「{best['title']}」({best.get('avg_completion_rate', 0):.0f}%)")

    high_fav = [a for a in articles if a.get("favorites", 0) >= 5]
    if high_fav:
        best = max(high_fav, key=lambda x: x.get("favorites", 0))
        lines.append(f"- 高收藏案例：「{best['title']}」(收藏{best.get('favorites', 0)})")

    return "\n" + "\n".join(lines) if lines else "数据不足，请根据常识写作"


def _parse_article(text: str) -> Optional[Dict]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "title" in parsed and "body" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start) if "```" in text[start:] else len(text)
        try:
            parsed = json.loads(text[start:end].strip())
            if isinstance(parsed, dict) and "title" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        try:
            parsed = json.loads(text[first:last + 1])
            if isinstance(parsed, dict) and "title" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _fallback_parse(text: str) -> Optional[Dict]:
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) < 3:
        return None
    title = lines[0].strip("#").strip()
    body_lines = [l for l in lines[1:] if not l.startswith("```") and '"title"' not in l and '"body"' not in l]
    body = "\n".join(body_lines).strip()
    if not body:
        return None
    return {"title": title, "alt_titles": [], "body": body, "emotion_score": 50, "viral_score": 50}
