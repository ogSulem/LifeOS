from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def analytics_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="📅 День", callback_data="analytics:day"),
            InlineKeyboardButton(text="📆 Неделя", callback_data="analytics:week"),
            InlineKeyboardButton(text="🗓 Месяц", callback_data="analytics:month"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
