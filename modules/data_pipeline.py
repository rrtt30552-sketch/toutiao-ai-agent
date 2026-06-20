"""数据管道 V8.2：统一读取 CSV，校验字段完整性。

V8.2：统一用 reads 字段，兼容旧格式 clicks 自动迁移。
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional

from modules.logger import log_info, log_ok, log_warn, log_err, log_step

STEP = "data"

REQUIRED_FIELDS = [
    "title", "impressions", "reads", "likes",
    "comments", "shares", "date", "content_type",
]

FIELD_MIGRATION = {
    "views": "impressions",
    "clicks": "reads",
    "type": "content_type",
    "ctr": None,
    "engagement_score": None,
    "topic_type": None,
    "strategy": None,
}

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "articles.csv")
DEFAULT_TIMESERIES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "timeseries.csv")


def load_csv(csv_path: str = DEFAULT_CSV) -> List[Dict]:
    log_step(STEP, "加载 CSV 数据")

    if not os.path.isfile(csv_path):
        log_warn(STEP, f"CSV 文件不存在: {csv_path}")
        return []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)
            raw_fields = reader.fieldnames or []
    except Exception as e:
        log_err(STEP, f"读取 CSV 失败: {e}")
        return []

    if not raw_rows:
        log_warn(STEP, "CSV 为空")
        return []

    needs_migration = _needs_migration(raw_fields)
    articles = []
    for i, row in enumerate(raw_rows, 1):
        article = _normalize_row(row, i, needs_migration)
        if article:
            articles.append(article)

    log_ok(STEP, f"loaded {len(articles)} rows")
    return articles


def load_csv_with_timeseries(
    csv_path: str = DEFAULT_CSV,
    timeseries_path: str = DEFAULT_TIMESERIES,
) -> List[Dict]:
    """加载 articles 并关联 timeseries 历史。"""
    articles = load_csv(csv_path)
    if not articles:
        return []

    timeseries = load_timeseries(timeseries_path)
    if not timeseries:
        return articles

    ts_by_id: Dict[str, List[Dict]] = {}
    for row in timeseries:
        aid = row.get("article_id", "")
        if aid:
            ts_by_id.setdefault(aid, []).append(row)
    for history in ts_by_id.values():
        history.sort(key=lambda r: r.get("publish_date", ""))

    for article in articles:
        aid = article.get("article_id", "")
        if aid in ts_by_id:
            article["_timeseries_history"] = ts_by_id[aid]

    log_info(STEP, f"关联 timeseries: {len(ts_by_id)} 篇有历史数据")
    return articles


def validate_csv_structure(csv_path: str) -> Dict:
    if not os.path.isfile(csv_path):
        return {"valid": False, "error": "文件不存在"}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    effective = set(fields)
    if "clicks" in effective:
        effective.add("reads")

    missing = [f for f in REQUIRED_FIELDS if f not in effective]
    return {
        "valid": len(missing) == 0,
        "row_count": len(rows),
        "fields": fields,
        "missing_fields": missing,
        "needs_migration": _needs_migration(fields),
    }


def load_timeseries(timeseries_path: str = DEFAULT_TIMESERIES) -> List[Dict]:
    log_step(STEP, "加载 timeseries 数据")

    if not os.path.isfile(timeseries_path):
        log_warn(STEP, f"timeseries 文件不存在: {timeseries_path}")
        return []

    try:
        with open(timeseries_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        log_err(STEP, f"读取失败: {e}")
        return []

    int_fields = ["impressions", "fan_impressions", "reads", "fan_reads",
                  "likes", "comments", "reposts", "shares", "favorites", "avg_read_duration"]
    float_fields = ["avg_completion_rate"]

    for row in rows:
        for fld in int_fields:
            row[fld] = _safe_int(row.get(fld, "0"))
        for fld in float_fields:
            row[fld] = _safe_float(row.get(fld, "0"))

    log_ok(STEP, f"loaded {len(rows)} timeseries records")
    return rows


def _needs_migration(fields: List[str]) -> bool:
    return bool(set(FIELD_MIGRATION.keys()) & set(fields))


def _normalize_row(row: Dict, row_num: int, needs_migration: bool) -> Optional[Dict]:
    if needs_migration:
        row = _migrate_fields(row)

    result = {}
    for field in REQUIRED_FIELDS:
        value = row.get(field, "")
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()

        if field in ("impressions", "reads", "likes", "comments", "shares"):
            result[field] = _safe_int(value)
        elif field == "title":
            if not value:
                return None
            result[field] = value
        elif field == "content_type":
            result[field] = value or "未分类"
        else:
            result[field] = value

    for field in row:
        if field not in result and field not in FIELD_MIGRATION:
            result[field] = row[field]

    return result


def _migrate_fields(row: Dict) -> Dict:
    new_row = {}
    for key, value in row.items():
        if key in FIELD_MIGRATION:
            new_key = FIELD_MIGRATION[key]
            if new_key is not None:
                new_row[new_key] = value
        else:
            new_row[key] = value
    if "shares" not in new_row:
        new_row["shares"] = "0"
    if "reads" not in new_row:
        new_row["reads"] = "0"
    return new_row


def _safe_int(val) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0
