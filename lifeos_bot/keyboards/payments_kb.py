from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def buy_subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить подписку", callback_data="pay:buy")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")],
        ]
    )


def yookassa_payment_kb(confirmation_url: str, payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"pay:check:{payment_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")],
        ]
    )
