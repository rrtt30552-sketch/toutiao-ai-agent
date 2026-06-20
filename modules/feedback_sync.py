"""反馈同步器 V8.2：策略统计 + 分词级标题相似度。"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple

from modules.logger import log_info, log_ok, log_warn, log_step
from modules.reward_calculator import compute_reward
from modules.utils import safe_write_json

STEP = "feedback"
STATS_FILE = "strategy_stats.json"
SIMILARITY_THRESHOLD = 0.6

_jieba_available = None


def _check_jieba():
    global _jieba_available
    if _jieba_available is None:
        try:
            import jieba
            _jieba_available = True
        except ImportError:
            _jieba_available = False
    return _jieba_available


_STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
    '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
    '看', '好', '自己', '这', '他', '她', '它', '们', '那', '被', '从', '把',
}


def _tokenize(text: str) -> set:
    cleaned = re.sub(r'[\s\W]', '', text)
    if not cleaned:
        return set()
    if _check_jieba():
        import jieba
        return set(w for w in jieba.lcut(cleaned) if len(w) > 1 and w not in _STOPWORDS)
    return set(cleaned)


def _rolling_average(values: list, window: int = 10) -> float:
    if not values:
        return 0.0
    return round(sum(values[-window:]) / len(values[-window:]), 6)


def load_stats(output_dir: str) -> Dict:
    path = os.path.join(output_dir, STATS_FILE)
    if not os.path.isfile(path):
        log_info(STEP, "无历史统计，从零开始")
        return _empty_stats()
    try:
        with open(path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        log_info(STEP, f"loaded stats: {len(stats.get('strategies', {}))} strategies")
        return stats
    except Exception as e:
        log_warn(STEP, f"统计文件损坏: {e}")
        return _empty_stats()


def update_stats(stats: Dict, articles: List[Dict], decay_days: int = 30) -> Dict:
    log_step(STEP, "更新策略统计")

    strategies = stats.setdefault("strategies", {})
    processed = set(stats.get("_processed_keys", []))
    updated = skipped = 0

    for article in articles:
        dedup_key = f"{article.get('title', '')}|{article.get('date', '')}"
        if dedup_key in processed:
            skipped += 1
            continue
        processed.add(dedup_key)

        content_type = article.get("content_type", "未分类")
        reward = compute_reward(article, decay_days)

        if content_type not in strategies:
            strategies[content_type] = {
                "reward_history": [], "total_articles": 0,
                "avg_reward": 0.0, "rolling_avg": 0.0, "last_updated": "",
            }

        entry = strategies[content_type]
        entry["reward_history"].append(reward)
        entry["total_articles"] += 1
        entry["last_updated"] = datetime.now().isoformat()
        if len(entry["reward_history"]) > 100:
            entry["reward_history"] = entry["reward_history"][-100:]
        history = entry["reward_history"]
        entry["avg_reward"] = round(sum(history) / len(history), 6)
        entry["rolling_avg"] = _rolling_average(history)
        updated += 1

    processed_list = list(processed)[-500:]
    stats["last_update"] = datetime.now().isoformat()
    stats["total_updates"] = stats.get("total_updates", 0) + 1
    stats["_processed_keys"] = processed_list

    log_ok(STEP, f"updated {updated} articles across {len(strategies)} strategies (skipped {skipped})")
    for name, entry in strategies.items():
        log_info(STEP, f"  {name}: avg={entry['avg_reward']:.4f} rolling={entry['rolling_avg']:.4f} n={entry['total_articles']}")

    return stats


def check_title_similarity(new_title: str, existing_titles: List[str], threshold: float = SIMILARITY_THRESHOLD) -> Tuple[bool, float, str]:
    if not existing_titles:
        return False, 0.0, ""

    new_words = _tokenize(new_title)
    if not new_words:
        return False, 0.0, ""

    max_sim = 0.0
    most_similar = ""
    for title in existing_titles:
        existing_words = _tokenize(title)
        if not existing_words:
            continue
        intersection = new_words & existing_words
        union = new_words | existing_words
        sim = len(intersection) / len(union) if union else 0.0
        if sim > max_sim:
            max_sim = sim
            most_similar = title

    return max_sim >= threshold, max_sim, most_similar


def save_stats(stats: Dict, output_dir: str):
    safe_write_json(os.path.join(output_dir, STATS_FILE), stats)


def get_strategy_ranking(stats: Dict) -> List[Dict]:
    ranking = []
    for name, entry in stats.get("strategies", {}).items():
        ranking.append({
            "strategy": name,
            "rolling_avg": entry.get("rolling_avg", 0),
            "avg_reward": entry.get("avg_reward", 0),
            "count": entry.get("total_articles", 0),
        })
    ranking.sort(key=lambda x: x["rolling_avg"], reverse=True)
    return ranking


def _empty_stats() -> Dict:
    return {"strategies": {}, "last_update": "", "total_updates": 0}
