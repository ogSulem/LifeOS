from __future__ import annotations

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.config import settings


def dashboard_kb(selected_day: date, tg_user_id: int | None = None) -> InlineKeyboardMarkup:
    today = date.today()
    if selected_day == today:
        mid_btn = InlineKeyboardButton(text="Сегодня", callback_data="day:0")
    else:
        mid_btn = InlineKeyboardButton(text=selected_day.strftime("%d.%m"), callback_data="noop")

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="💭 Мысли", callback_data="nav:thoughts"),
            InlineKeyboardButton(text="🎯 Цели", callback_data="nav:goals"),
            InlineKeyboardButton(text="📅 Расписание", callback_data="nav:schedule"),
        ],
        [
            InlineKeyboardButton(text="🙏 Благодарности", callback_data="nav:gratitude"),
            InlineKeyboardButton(text="🧭 Жизненные цели", callback_data="nav:life_goals"),
            InlineKeyboardButton(text="⚡ Полезное", callback_data="nav:habits"),
        ],
        [
            InlineKeyboardButton(text="📊 Аналитика", callback_data="nav:analytics"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="nav:settings"),
        ],
        [
            InlineKeyboardButton(text="⬅️", callback_data="day:-1"),
            mid_btn,
            InlineKeyboardButton(text="➡️", callback_data="day:1"),
        ],
    ]

    if settings.admin_id is not None and tg_user_id == settings.admin_id:
        rows.append(
            [
                InlineKeyboardButton(text="🛠 Админ", callback_data="admin:panel"),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
