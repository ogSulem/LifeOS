from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def support_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="support:cancel")]]
    )


def support_ok_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Ок", callback_data="support:ok")]]
    )
