from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


def habits_kb(habits: list[tuple[int, str, bool]], page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([InlineKeyboardButton(text="➕ Добавить привычку", callback_data="habits:add")])

    for i, (habit_id, title, done) in enumerate(habits):
        num = page * 7 + i + 1
        mark_emoji = "↩️" if done else "✅"
        rows.append(
            [
                InlineKeyboardButton(text=f"{mark_emoji} {num}", callback_data=f"habits:toggle:{habit_id}:{page}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"habits:delete:{habit_id}:{page}"),
            ]
        )

    pager = pager_row("habits", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def habits_input_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="habits:back")]]
    )
