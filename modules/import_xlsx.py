"""Excel 导入模块 V8.2：读取头条导出的 xlsx，写入 timeseries 和 articles。

V8.2：优先用 raw XML 解析（绕过 openpyxl 样式 bug），统一用 reads 字段。
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from modules.logger import log_info, log_ok, log_warn, log_err, log_step

STEP = "import"

XLSX_FIELD_MAP = {
    "标题": "title",
    "发布时间": "publish_date",
    "ID": "article_id",
    "链接": "url",
    "展现量": "impressions",
    "粉丝展现量": "fan_impressions",
    "阅读量": "reads",
    "粉丝阅读量": "fan_reads",
    "点击率": "_skip",
    "平均阅读完成率": "avg_completion_rate",
    "平均阅读时长": "avg_read_duration",
    "点赞量": "likes",
    "评论量": "comments",
    "转发量": "reposts",
    "分享量": "shares",
    "收藏量": "favorites",
}

TIMESERIES_FIELDS = [
    "article_id", "title", "publish_date", "import_date",
    "impressions", "fan_impressions", "reads", "fan_reads",
    "avg_completion_rate", "avg_read_duration",
    "likes", "comments", "reposts", "shares", "favorites", "url",
]

ARTICLES_FIELDS = [
    "article_id", "title", "impressions", "reads", "likes",
    "comments", "shares", "date", "content_type",
]


def read_xlsx(xlsx_path: str) -> List[Dict]:
    log_step(STEP, f"读取 Excel: {os.path.basename(xlsx_path)}")

    if not os.path.isfile(xlsx_path):
        log_err(STEP, f"文件不存在: {xlsx_path}")
        return []

    rows = _read_xlsx_raw(xlsx_path)
    if rows:
        log_info(STEP, "使用 raw XML 解析成功")
    else:
        log_warn(STEP, "raw XML 失败，尝试 openpyxl...")
        try:
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            log_info(STEP, "使用 openpyxl 读取成功")
        except Exception as e:
            log_err(STEP, f"openpyxl 也失败: {e}")
            return []

    if not rows:
        log_err(STEP, "无法读取文件数据")
        return []

    header = [str(h).strip() if h else "" for h in rows[0]]
    log_info(STEP, f"表头: {header}")

    col_map = {}
    for i, col_name in enumerate(header):
        if col_name in XLSX_FIELD_MAP:
            internal = XLSX_FIELD_MAP[col_name]
            if internal != "_skip":
                col_map[internal] = i

    required = ["title", "article_id"]
    missing = [f for f in required if f not in col_map]
    if missing:
        log_err(STEP, f"缺少必要列: {missing}")
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    total = len(rows) - 1

    for row_idx, row in enumerate(rows[1:], 2):
        record = {}
        for field, col_idx in col_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            record[field] = _clean_value(field, val)

        if not record.get("title"):
            continue

        raw_date = record.get("publish_date", "")
        record["publish_date"] = _parse_date(raw_date) if raw_date else today

        record["article_id"] = str(record.get("article_id", "")).strip()
        if not record["article_id"]:
            import hashlib
            record["article_id"] = hashlib.md5(record["title"].encode("utf-8")).hexdigest()[:16]

        record["import_date"] = today
        records.append(record)

    log_ok(STEP, f"解析到 {len(records)} 条记录")
    return records


def merge_timeseries(records: List[Dict], timeseries_path: str) -> Tuple[int, int]:
    log_step(STEP, "合并到 timeseries.csv")

    existing = {}
    existing_order = []
    if os.path.isfile(timeseries_path):
        with open(timeseries_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row.get("article_id", ""), row.get("publish_date", ""))
                existing[key] = row
                existing_order.append(key)

    added = updated = 0
    for record in records:
        key = (record["article_id"], record["publish_date"])
        row_data = {field: record.get(field, "") for field in TIMESERIES_FIELDS}
        if key in existing:
            existing[key] = row_data
            updated += 1
        else:
            existing[key] = row_data
            existing_order.append(key)
            added += 1

    _write_csv(timeseries_path, TIMESERIES_FIELDS, existing, existing_order)
    log_ok(STEP, f"timeseries: 新增 {added}, 更新 {updated}")
    return added, updated


def update_articles_snapshot(records: List[Dict], articles_path: str) -> Tuple[int, int]:
    log_step(STEP, "更新 articles.csv 快照")

    existing = {}
    existing_order = []
    if os.path.isfile(articles_path):
        with open(articles_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = row.get("article_id", row.get("title", ""))
                existing[aid] = row
                existing_order.append(aid)

    latest_by_id = {}
    for record in records:
        aid = record["article_id"]
        pub_date = record.get("publish_date", "")
        if aid not in latest_by_id or pub_date > latest_by_id[aid].get("publish_date", ""):
            latest_by_id[aid] = record

    added = updated = 0
    for aid, record in latest_by_id.items():
        article_row = {
            "article_id": record.get("article_id", ""),
            "title": record.get("title", ""),
            "impressions": record.get("impressions", 0),
            "reads": record.get("reads", 0),
            "likes": record.get("likes", 0),
            "comments": record.get("comments", 0),
            "shares": record.get("shares", 0),
            "date": record.get("publish_date", ""),
            "content_type": existing.get(aid, {}).get("content_type", "未分类"),
        }
        if aid in existing:
            existing[aid] = article_row
            updated += 1
        else:
            existing[aid] = article_row
            existing_order.append(aid)
            added += 1

    _write_csv(articles_path, ARTICLES_FIELDS, existing, existing_order)
    log_ok(STEP, f"articles: 新增 {added}, 更新 {updated}")
    return added, updated


def _write_csv(path: str, fields: List[str], data: Dict, order: List):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for key in order:
            if key in data:
                writer.writerow(data[key])


def _clean_value(field: str, val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _parse_date(raw: str) -> str:
    raw = str(raw).strip()
    if len(raw) >= 10:
        return raw[:10]
    return raw


def _read_xlsx_raw(xlsx_path: str) -> Optional[List[tuple]]:
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        z = zipfile.ZipFile(xlsx_path)
    except Exception:
        return None

    shared_strings = []
    if "xl/sharedStrings.xml" in z.namelist():
        try:
            tree = ET.parse(z.open("xl/sharedStrings.xml"))
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in tree.findall(".//s:si", ns):
                texts = []
                for t_elem in si.findall(".//s:t", ns):
                    if t_elem.text:
                        texts.append(t_elem.text)
                shared_strings.append("".join(texts) if texts else "")
        except Exception:
            pass

    sheet_path = "xl/worksheets/sheet1.xml"
    if sheet_path not in z.namelist():
        for name in z.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                sheet_path = name
                break

    try:
        tree = ET.parse(z.open(sheet_path))
    except Exception:
        return None

    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    result = []
    for row in tree.findall(".//s:row", ns):
        cells = row.findall("s:c", ns)
        row_vals = []
        for cell in cells:
            t = cell.get("t", "")
            v = cell.find("s:v", ns)
            if v is not None and v.text is not None:
                if t == "s":
                    try:
                        idx = int(v.text)
                        row_vals.append(shared_strings[idx] if idx < len(shared_strings) else "")
                    except (ValueError, IndexError):
                        row_vals.append(v.text)
                else:
                    row_vals.append(v.text)
            else:
                is_elem = cell.find("s:is", ns)
                if is_elem is not None:
                    t_elem = is_elem.find("s:t", ns)
                    row_vals.append(t_elem.text if t_elem is not None and t_elem.text else "")
                else:
                    row_vals.append("")
        result.append(tuple(row_vals))

    return result if result else None
