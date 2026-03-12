from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


def thoughts_kb(page: int = 0, total_pages: int = 1, show_clear: bool = True) -> InlineKeyboardMarkup:
    first_row: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="➕ Дописать", callback_data="thoughts:add"),
    ]
    if show_clear:
        first_row.append(InlineKeyboardButton(text="🧹 Очистить", callback_data="thoughts:clear"))
    rows: list[list[InlineKeyboardButton]] = [first_row]

    pager = pager_row("thoughts", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def thoughts_input_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="thoughts:back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
