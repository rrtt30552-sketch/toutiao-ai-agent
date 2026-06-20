"""工具函数：文件操作。"""

import json
import os


def ensure_dir(path: str):
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def safe_write(path: str, content: str):
    """安全写入文件（自动创建目录）。"""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def safe_write_json(path: str, data):
    """安全写入 JSON 文件。"""
    safe_write(path, json.dumps(data, ensure_ascii=False, indent=2))
