"""CSV 同步脚本 V8.2：追加新文章到 data/articles.csv。"""

import argparse
import csv
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.data_pipeline import REQUIRED_FIELDS

FIELDS = REQUIRED_FIELDS


def append_article(csv_path: str, title: str, content_type: str = "未分类",
                   impressions: int = 0, reads: int = 0, likes: int = 0,
                   comments: int = 0, shares: int = 0, date: str = ""):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    row = {
        "title": title, "impressions": impressions, "reads": reads,
        "likes": likes, "comments": comments, "shares": shares,
        "date": date, "content_type": content_type,
    }

    file_exists = os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"[SYNC] appended '{title}' to {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="CSV 同步工具 V8.2")
    parser.add_argument("--csv", type=str, default=os.path.join(PROJECT_ROOT, "data", "articles.csv"))
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--content-type", type=str, default="未分类")
    parser.add_argument("--impressions", type=int, default=0)
    parser.add_argument("--reads", type=int, default=0)
    parser.add_argument("--likes", type=int, default=0)
    parser.add_argument("--comments", type=int, default=0)
    parser.add_argument("--shares", type=int, default=0)
    parser.add_argument("--date", type=str, default="")

    args = parser.parse_args()
    append_article(csv_path=args.csv, title=args.title, content_type=args.content_type,
                   impressions=args.impressions, reads=args.reads, likes=args.likes,
                   comments=args.comments, shares=args.shares, date=args.date)


if __name__ == "__main__":
    main()
