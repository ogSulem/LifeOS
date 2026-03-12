from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton


@dataclass(frozen=True)
class PageSlice:
    page: int
    total_pages: int
    items: list[str]


@dataclass(frozen=True)
class CountSlice:
    page: int
    total_pages: int
    items: list


def clamp_page(page: int, total_pages: int) -> int:
    if total_pages <= 0:
        return 0
    if page < 0:
        return 0
    if page >= total_pages:
        return total_pages - 1
    return page


def paginate_by_chars(
    lines: list[str],
    page: int,
    *,
    header: str = "",
    max_chars: int = 3500,
) -> PageSlice:
    chunks: list[list[str]] = []
    current: list[str] = []

    current_len = len(header)
    for line in lines:
        extra = len(line) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            chunks.append(current)
            current = [line]
            current_len = len(header) + len(line)
            continue

        current.append(line)
        current_len += extra

    if current or not chunks:
        chunks.append(current)

    total_pages = len(chunks)
    safe_page = clamp_page(page, total_pages)

    return PageSlice(page=safe_page, total_pages=total_pages, items=chunks[safe_page])


def pager_row(prefix: str, page: int, total_pages: int) -> list[InlineKeyboardButton]:
    if total_pages <= 1:
        return []

    prev_page = page - 1
    next_page = page + 1

    left = InlineKeyboardButton(
        text="⬅️",
        callback_data=f"{prefix}:page:{prev_page}" if prev_page >= 0 else "noop",
    )
    mid = InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    right = InlineKeyboardButton(
        text="➡️",
        callback_data=f"{prefix}:page:{next_page}" if next_page < total_pages else "noop",
    )

    return [left, mid, right]


def paginate_by_count(items: list, page: int, *, per_page: int) -> CountSlice:
    if per_page <= 0:
        per_page = 1

    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages <= 0:
        total_pages = 1

    safe_page = clamp_page(page, total_pages)
    start = safe_page * per_page
    end = start + per_page
    return CountSlice(page=safe_page, total_pages=total_pages, items=items[start:end])
