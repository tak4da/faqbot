from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


class SubscriberStorage:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> set[int]:
        raw = self._path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return {int(item) for item in data}

    def _save(self, data: Iterable[int]) -> None:
        payload = sorted(set(data))
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, user_id: int) -> bool:
        data = self._load()
        if user_id in data:
            return False
        data.add(user_id)
        self._save(data)
        return True

    def remove(self, user_id: int) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        data.remove(user_id)
        self._save(data)
        return True

    def list_all(self) -> list[int]:
        return sorted(self._load())
