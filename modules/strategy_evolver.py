"""策略进化器 V8.2：基于真实 reward 的滚动平均。"""

import json
import os
from typing import Dict

from modules.logger import log_info, log_warn, log_step
from modules.utils import safe_write_json

STEP = "evolve"
WEIGHTS_FILE = "strategy_weights.json"


def load_weights(output_dir: str) -> Dict:
    path = os.path.join(output_dir, WEIGHTS_FILE)
    if not os.path.isfile(path):
        log_info(STEP, "使用默认策略权重")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            weights = json.load(f)
        log_info(STEP, f"loaded weights: {len(weights)} strategies")
        return weights
    except Exception as e:
        log_warn(STEP, f"权重文件损坏: {e}")
        return {}


def evolve_weights(current_weights: Dict, stats: Dict, output_dir: str = "", exploration_factor: float = 0.2) -> Dict:
    log_step(STEP, "策略进化（真实数据驱动）")

    strategies = stats.get("strategies", {})
    weights = dict(current_weights)

    for name, entry in strategies.items():
        rolling_avg = entry.get("rolling_avg", 0)
        count = entry.get("total_articles", 0)

        score = rolling_avg
        if count < 5:
            score += exploration_factor * 0.5
        elif count < 10:
            score += exploration_factor * 0.2

        weights[name] = {
            "score": round(score, 6),
            "rolling_avg": round(rolling_avg, 6),
            "avg_reward": round(entry.get("avg_reward", 0), 6),
            "count": count,
            "exploration_bonus": round(score - rolling_avg, 6),
        }
        log_info(STEP, f"  {name}: score={score:.4f} rolling={rolling_avg:.4f} n={count}")

    if output_dir:
        save_weights(weights, output_dir)
    return weights


def save_weights(weights: Dict, output_dir: str):
    safe_write_json(os.path.join(output_dir, WEIGHTS_FILE), weights)


def get_top_strategy(weights: Dict) -> str:
    if not weights:
        return ""
    return max(weights, key=lambda k: weights[k].get("score", 0))
