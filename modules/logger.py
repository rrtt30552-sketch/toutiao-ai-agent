"""结构化日志系统 V8.2：统一规范。"""

import os
import sys
from datetime import datetime


STEP_LABELS = {
    "main":     "MAIN",
    "data":     "DATA",
    "import":   "IMPORT",
    "classify": "CLASSIFY",
    "reward":   "REWARD",
    "feedback": "FEEDBACK",
    "evolve":   "EVOLVE",
    "rank":     "RANK",
    "write":    "WRITE",
    "save":     "SAVE",
    "ai":       "AI",
    "sync":     "SYNC",
}


def _write(level: str, step: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    tag = STEP_LABELS.get(step, step.upper())
    line = f"  [{ts}] [{tag}] {msg}"
    if level == "ERROR":
        print(line, file=sys.stderr, flush=True)
    elif level == "WARN":
        print(line, file=sys.stderr, flush=True)
    else:
        print(line, flush=True)


def log_info(step: str, msg: str):
    _write("INFO", step, msg)


def log_ok(step: str, msg: str):
    _write("OK", step, msg)


def log_warn(step: str, msg: str):
    _write("WARN", step, msg)


def log_err(step: str, msg: str):
    _write("ERROR", step, msg)


def log_step(step: str, title: str):
    print(f"\n{'='*50}", flush=True)
    print(f"  [{STEP_LABELS.get(step, step.upper())}] {title}", flush=True)
    print(f"{'='*50}", flush=True)
