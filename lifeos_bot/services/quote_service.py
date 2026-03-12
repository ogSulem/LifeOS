from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import choice


@dataclass(frozen=True)
class Quote:
    text: str
    author: str | None = None


class QuoteService:
    def __init__(self, quotes_path: Path) -> None:
        self.quotes_path = quotes_path

    def get_quote_of_day(self) -> Quote | None:
        if not self.quotes_path.exists():
            return None
        data = json.loads(self.quotes_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            return None
        value = choice(data)
        if isinstance(value, str):
            return Quote(text=value)
        if isinstance(value, dict):
            text = value.get("text")
            author = value.get("author")
            if isinstance(text, str) and text.strip():
                return Quote(text=text.strip(), author=str(author).strip() if author else None)
        return Quote(text=str(value))
