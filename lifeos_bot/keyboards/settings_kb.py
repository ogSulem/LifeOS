from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def settings_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📅 Шаблон расписания", callback_data="settings:schedule")],
        [InlineKeyboardButton(text="⚡ Шаблон привычек", callback_data="settings:habits")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_input_kb(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)]])
