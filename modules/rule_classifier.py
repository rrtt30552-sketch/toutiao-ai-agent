"""规则分类器 V8.2：不依赖 AI，纯关键词分类。"""

import re
import csv
import os
from typing import Dict, List, Tuple

from modules.logger import log_info, log_ok, log_step

STEP = "classify"

CATEGORY_RULES = {
    "保安故事": {
        "keywords": ["保安", "值夜班", "夜班", "值班", "门卫", "巡逻", "安保"],
        "strong": ["保安自述", "当保安", "保安值", "保安发现"],
    },
    "快递人生": {
        "keywords": ["快递", "外卖", "配送", "骑手", "送餐", "快递员"],
        "strong": ["快递员", "送快递", "快递说出"],
    },
    "网约车洞察": {
        "keywords": ["网约车", "滴滴", "司机", "出租车", "打车", "乘客"],
        "strong": ["网约车司机", "滴滴司机"],
    },
    "失业转型": {
        "keywords": ["失业", "裁员", "被裁", "下岗", "找工作", "求职", "离职", "辞职"],
        "strong": ["失业后", "被裁后", "失业男人"],
    },
    "职场感悟": {
        "keywords": ["上班", "工作", "领导", "同事", "升职", "加薪", "加班", "老板", "公司"],
        "strong": ["职场", "上班后", "工作后"],
    },
    "货车司机": {
        "keywords": ["货车", "卡车", "长途", "服务区", "跑运输"],
        "strong": ["货车司机", "卡车司机"],
    },
    "生活哲思": {
        "keywords": ["人生", "生活", "明白", "发现", "真相", "现实", "成年人", "底气"],
        "strong": ["人生真相", "成年人的", "生活的真相"],
    },
}

STYLE_RULES = {
    "数字型": {"patterns": [r'\d+岁', r'\d+年', r'\d+万', r'\d+元', r'\d+天', r'\d+个月'], "keywords": []},
    "悬念型": {"patterns": [r'[…\.]{2,}'], "keywords": ["竟然", "没想到", "居然", "原来", "其实", "真相", "秘密", "发现"]},
    "疑问型": {"patterns": [r'[？?]$'], "keywords": ["为什么", "怎么", "如何", "难道"]},
    "情感型": {"patterns": [], "keywords": ["心疼", "泪目", "感动", "心酸", "无奈", "崩溃", "扎心", "哭了"]},
    "自述型": {"patterns": [], "keywords": ["自述", "坦言", "说出真相"]},
}


def classify_article(title: str) -> Tuple[str, str, float]:
    """规则分类单篇文章。Returns: (content_type, title_style, confidence)"""
    scores = {}
    for category, rules in CATEGORY_RULES.items():
        score = sum(1 for kw in rules["keywords"] if kw in title) + sum(3 for kw in rules["strong"] if kw in title)
        if score > 0:
            scores[category] = score

    if scores:
        content_type = max(scores, key=scores.get)
        confidence = min(scores[content_type] / 5.0, 1.0)
    else:
        content_type = "生活哲思"
        confidence = 0.2

    title_style = "故事型"
    for style, rules in STYLE_RULES.items():
        if style == "故事型":
            continue
        matched = any(re.search(p, title) for p in rules["patterns"]) or any(kw in title for kw in rules["keywords"])
        if matched:
            title_style = style
            break

    return content_type, title_style, confidence


def classify_batch(articles: List[Dict]) -> Dict[str, Tuple[str, str, float]]:
    results = {}
    for a in articles:
        aid = a.get("article_id", a.get("title", ""))
        results[aid] = classify_article(a.get("title", ""))
    return results


def classify_and_update_csv(articles_path: str, dry_run: bool = False) -> int:
    log_step(STEP, "规则分类（不消耗 API）")

    with open(articles_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    stats = {}

    for row in rows:
        old_type = row.get("content_type", "未分类")
        if old_type and old_type != "未分类":
            stats[old_type] = stats.get(old_type, 0) + 1
            continue

        content_type, title_style, confidence = classify_article(row.get("title", ""))
        row["content_type"] = content_type
        updated += 1
        stats[content_type] = stats.get(content_type, 0) + 1

        if dry_run:
            log_info(STEP, f"  [{content_type}|{title_style}|{confidence:.0%}] {row.get('title', '')[:40]}")

    if not dry_run:
        with open(articles_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        log_ok(STEP, f"规则分类完成，更新 {updated} 篇")
    else:
        log_info(STEP, f"预览模式，将更新 {updated} 篇")

    log_info(STEP, "分类统计：")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        log_info(STEP, f"  {cat}: {count}篇")

    return updated
