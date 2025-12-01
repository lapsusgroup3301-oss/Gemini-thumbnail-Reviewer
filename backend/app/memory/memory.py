import uuid
import json
import os
from typing import Dict, List, Any
from collections import defaultdict

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory_store.json")

_sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


def _load_from_disk() -> None:
    if not os.path.exists(MEMORY_PATH):
        return
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sid, events in data.items():
            _sessions[sid] = list(events)
    except Exception:
        pass


def _save_to_disk() -> None:
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({sid: ev for sid, ev in _sessions.items()}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load_from_disk()


def get_or_create_session(session_id: str | None) -> str:
    if session_id and session_id in _sessions:
        return session_id
    new_id = str(uuid.uuid4())
    _sessions[new_id] = []
    _save_to_disk()
    return new_id


def append_event(session_id: str, event: Dict[str, Any]):
    _sessions[session_id].append(event)
    if len(_sessions[session_id]) > 20:
        _sessions[session_id] = _sessions[session_id][-20:]
    _save_to_disk()


def summarize_history(session_id: str) -> str:
    items = _sessions.get(session_id, [])
    if not items:
        return ""
    lines = []
    for ev in items[-8:]:
        score = ev.get("score")
        title = ev.get("title") or ""
        summary = ev.get("summary") or ""
        lines.append(f"[score={score}] {title} :: {summary}")
    full = " | ".join(lines)
    return full[-2000:]


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    return list(_sessions.get(session_id, []))
