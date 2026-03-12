from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


def gratitude_kb(page: int = 0, total_pages: int = 1, show_clear: bool = True) -> InlineKeyboardMarkup:
    first_row: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="➕ Добавить", callback_data="gratitude:add"),
    ]
    if show_clear:
        first_row.append(InlineKeyboardButton(text="🧹 Очистить", callback_data="gratitude:clear"))
    rows: list[list[InlineKeyboardButton]] = [first_row]

    pager = pager_row("gratitude", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gratitude_input_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="gratitude:back")]]
    )
