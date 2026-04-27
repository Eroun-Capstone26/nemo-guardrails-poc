import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.config import LOGS_DIR


def save_json_log(payload: Dict[str, Any]) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_path = LOGS_DIR / f"log_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path
