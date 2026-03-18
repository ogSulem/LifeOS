from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def buy_subscription_kb(
    *,
    show_back: bool = True,
    back_callback_data: str = "nav:dashboard",
    show_trial: bool = True,
) -> InlineKeyboardMarkup:
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    if show_trial:
        inline_keyboard.append([InlineKeyboardButton(text="🆓 Тест на 3 дня", callback_data="pay:trial")])
    inline_keyboard.append([InlineKeyboardButton(text="💳 Купить подписку", callback_data="pay:buy")])
    if show_back:
        inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data)])

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *inline_keyboard,
        ]
    )


def yookassa_payment_kb(confirmation_url: str, payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"pay:check:{payment_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:payments")],
        ]
    )
