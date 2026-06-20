"""Reward 计算器 V8.2：基于真实数据，30天衰减，线性回归增长。

V8.2：半衰期 7→30 天，增长率改线性回归，reward 量级更合理。
"""

import math
from datetime import datetime
from typing import Dict, List

from modules.logger import log_info, log_step, log_warn

STEP = "reward"


def _growth_slope_score(reads_series: List[float]) -> float:
    """线性回归斜率 → [0,1] 增长分，0.5=无增长。"""
    n = len(reads_series)
    if n < 3:
        return 0.5

    x_mean = (n - 1) / 2.0
    y_mean = sum(reads_series) / n

    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(reads_series))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.5

    slope = num / den
    rel_slope = slope / y_mean if y_mean > 0 else 0.0
    return round(1.0 / (1.0 + math.exp(-5.0 * rel_slope)), 6)


def compute_reward_from_timeseries(history: List[Dict], decay_days: int = 30) -> float:
    if not history:
        return 0.0

    latest = history[-1]
    imp = max(latest.get("impressions", 0), 1)

    reads = latest.get("reads", 0)
    likes = latest.get("likes", 0)
    comments = latest.get("comments", 0)
    shares = latest.get("shares", 0)
    reposts = latest.get("reposts", 0)
    favorites = latest.get("favorites", 0)
    comp_rate = latest.get("avg_completion_rate", 0)

    ctr = reads / imp
    eng = (likes + comments + shares + reposts) / imp
    comp = comp_rate / 100.0 if comp_rate else 0.0
    fav = favorites / imp

    unique_dates = len(set(r.get("publish_date", "") or r.get("import_date", "") for r in history))

    if len(history) >= 3 and unique_dates >= 3:
        reads_series = [float(r.get("reads", 0)) for r in history]
        growth = _growth_slope_score(reads_series)
        raw = ctr * 0.25 + eng * 0.25 + comp * 0.15 + fav * 0.15 + growth * 0.20
    else:
        w = {"ctr": 0.3, "eng": 0.3, "comp": 0.0, "fav": 0.0}
        active = 0.6
        if comp > 0:
            w["comp"] = 0.2
            active += 0.2
        if fav > 0:
            w["fav"] = 0.2
            active += 0.2
        raw = (ctr * w["ctr"] + eng * w["eng"] + comp * w["comp"] + fav * w["fav"]) / active if active > 0 else 0.0

    days = _days_since(latest.get("publish_date", ""))
    weight = max(math.exp(-days / decay_days), 0.1) if days >= 0 else 1.0

    return round(min(max(raw * weight, 0.0), 1.0), 6)


def compute_reward(article: Dict, decay_days: int = 30) -> float:
    history = article.get("_timeseries_history")
    if history:
        return compute_reward_from_timeseries(history, decay_days)

    imp = max(article.get("impressions", 0), 1)
    reads = article.get("reads", 0)
    likes = article.get("likes", 0)
    comments = article.get("comments", 0)
    shares = article.get("shares", 0)
    favorites = article.get("favorites", 0)
    comp_rate = article.get("avg_completion_rate", 0)
    date_str = article.get("date", "")

    ctr = reads / imp
    eng = (likes + comments + shares) / imp
    comp = comp_rate / 100.0 if comp_rate else 0.0
    fav = favorites / imp

    raw = ctr * 0.35 + eng * 0.25 + comp * 0.2 + fav * 0.2

    days = _days_since(date_str)
    weight = max(math.exp(-days / decay_days), 0.1) if days >= 0 else 1.0

    return round(min(max(raw * weight, 0.0), 1.0), 6)


def compute_reward_batch(articles: List[Dict], decay_days: int = 30) -> List[Dict]:
    results = []
    for a in articles:
        a_copy = dict(a)
        a_copy["reward"] = compute_reward(a, decay_days)
        results.append(a_copy)
    return results


def compute_avg_reward(articles: List[Dict], decay_days: int = 30) -> float:
    if not articles:
        return 0.0
    rewards = [compute_reward(a, decay_days) for a in articles]
    return round(sum(rewards) / len(rewards), 6)


def compute_strategy_rewards(articles: List[Dict], strategy_field: str = "content_type", decay_days: int = 30) -> Dict[str, Dict]:
    groups: Dict[str, List[float]] = {}
    for a in articles:
        key = a.get(strategy_field, "未分类")
        groups.setdefault(key, []).append(compute_reward(a, decay_days))

    result = {}
    for key, rewards in groups.items():
        result[key] = {
            "avg_reward": round(sum(rewards) / len(rewards), 6) if rewards else 0.0,
            "count": len(rewards),
            "rewards": rewards,
            "rolling_avg": _rolling_average(rewards, window=10),
        }
    return result


def _rolling_average(values: List[float], window: int = 10) -> float:
    if not values:
        return 0.0
    return round(sum(values[-window:]) / len(values[-window:]), 6)


def _days_since(date_str: str) -> int:
    if not date_str:
        return -1
    try:
        return max((datetime.now() - datetime.strptime(date_str.strip(), "%Y-%m-%d")).days, 0)
    except (ValueError, TypeError):
        return -1
