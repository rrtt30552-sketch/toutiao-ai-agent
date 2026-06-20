"""内容评分器 V8.2：Thompson Sampling + Bayesian Prior。"""

import random
from typing import Dict, List

from modules.logger import log_info, log_step

STEP = "rank"

PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0


def select_best_strategy(strategy_ranking: List[Dict], exploration_factor: float = 0.2) -> str:
    if not strategy_ranking:
        return "未分类"

    if len(strategy_ranking) == 1:
        best = strategy_ranking[0]
        log_info(STEP, f"  唯一策略: {best['strategy']}")
        return best["strategy"]

    samples = []
    for entry in strategy_ranking:
        strategy = entry["strategy"]
        rolling_avg = entry.get("rolling_avg", 0)
        count = entry.get("count", 0)

        alpha = rolling_avg * count + PRIOR_ALPHA
        beta_param = (1 - rolling_avg) * count + PRIOR_BETA

        sample = random.betavariate(alpha, beta_param)
        samples.append((strategy, sample, rolling_avg, count, alpha, beta_param))

    samples.sort(key=lambda x: x[1], reverse=True)
    chosen = samples[0]

    log_info(STEP, f"  Thompson Sampling: {chosen[0]} (sample={chosen[1]:.4f}, rolling={chosen[2]:.4f}, n={chosen[3]})")
    for s in samples:
        log_info(STEP, f"    {s[0]}: sample={s[1]:.4f} rolling={s[2]:.4f} n={s[3]} Beta({s[4]:.1f},{s[5]:.1f})")

    return chosen[0]


def classify_title_style(title: str) -> str:
    import re
    if re.search(r'\d+岁', title) or re.search(r'\d+年', title):
        return "数字型"
    if any(w in title for w in ["竟然", "没想到", "居然", "原来", "真相", "秘密", "…", "..."]):
        return "悬念型"
    if "？" in title or "?" in title or any(w in title for w in ["为什么", "怎么", "如何"]):
        return "疑问型"
    if any(w in title for w in ["心疼", "泪目", "感动", "心酸", "崩溃", "扎心", "哭了"]):
        return "情感型"
    if any(w in title for w in ["自述", "坦言", "说出真相"]):
        return "自述型"
    return "故事型"


def build_composite_strategy(content_type: str, title_style: str) -> str:
    return f"{content_type}-{title_style}"
