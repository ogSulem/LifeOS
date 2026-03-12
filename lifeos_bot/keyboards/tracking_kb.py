from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def morning_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Я встал", callback_data="track:wakeup")]]
    )

def day_rating_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐1", callback_data="track:rate:1"),
                InlineKeyboardButton(text="⭐2", callback_data="track:rate:2"),
                InlineKeyboardButton(text="⭐3", callback_data="track:rate:3"),
                InlineKeyboardButton(text="⭐4", callback_data="track:rate:4"),
                InlineKeyboardButton(text="⭐5", callback_data="track:rate:5"),
            ]
        ]
    )


def sleep_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌙 Споки", callback_data="track:sleep")]]
    )
