from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


ScheduleKbEvent = tuple[int, str | None, str | None, str]


def schedule_kb(
    page: int = 0,
    total_pages: int = 1,
    events: list[ScheduleKbEvent] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="schedule:add"),
        ],
    ]

    if events:
        for event_id, time_from, time_to, title in events:
            if time_from and time_to:
                time_part = f"{time_from}-{time_to}"
            elif time_from:
                time_part = time_from
            else:
                time_part = "—"

            rows.append(
                [
                    InlineKeyboardButton(text=f"⏰ {time_part}", callback_data=f"schedule:evt_time:{event_id}:{page}"),
                    InlineKeyboardButton(text=title[:30], callback_data=f"schedule:evt_title:{event_id}:{page}"),
                    InlineKeyboardButton(text="❌", callback_data=f"schedule:evt_del:{event_id}:{page}"),
                ]
            )

    pager = pager_row("schedule", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def schedule_input_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule:back")]]
    )
