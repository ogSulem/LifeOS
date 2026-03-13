from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


GoalKbItem = tuple[int, bool, int]


def goals_kb(goals: list[GoalKbItem], page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="goals:add")])

    for goal_id, is_done, num in goals:
        mark_emoji = "↩️" if is_done else "✅"
        mark_text = f"{mark_emoji} {num}"
        rows.append(
            [
                InlineKeyboardButton(text=mark_text, callback_data=f"goals:toggle:{goal_id}:{page}"),
                InlineKeyboardButton(text="⏭", callback_data=f"goals:move:{goal_id}:{page}"),
                InlineKeyboardButton(text="❌", callback_data=f"goals:delete:{goal_id}:{page}"),
            ]
        )

    if goals:
        pager = pager_row("goals", page, total_pages)
        if pager:
            rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def goals_input_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="goals:back")]]
    )
