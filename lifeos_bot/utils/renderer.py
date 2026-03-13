from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aiogram.types import InlineKeyboardMarkup

from lifeos_bot.services.dashboard_service import DashboardStats
from lifeos_bot.services.quote_service import Quote


@dataclass(frozen=True)
class DashboardView:
    text: str
    keyboard: InlineKeyboardMarkup


def render_dashboard(
    day: date,
    quote: Quote | None,
    keyboard: InlineKeyboardMarkup,
    stats: DashboardStats,
) -> DashboardView:
    rating = "—" if stats.day_rating is None else str(int(stats.day_rating))
    header = f"<b>🧠 LifeOS</b>\n{day.strftime('%d.%m.%Y')} ⭐ {rating}"

    meta_lines: list[str] = []
    wakeup = stats.wakeup_at or "—"
    sleep = stats.sleep_at or "—"
    meta_lines.append(f"☀️ {wakeup}")
    meta_lines.append(f"🌙 {sleep}")
    header += "\n" + "\n".join(meta_lines)

    quote_block = ""
    if quote and quote.text:
        quote_block = f"\n\n<i>“{quote.text}”</i>"
        if quote.author:
            quote_block += f"\n<i>— {quote.author}</i>"

    goals_check = " ✅" if stats.goals_total > 0 and stats.goals_done == stats.goals_total else ""
    habits_check = " ✅" if stats.habits_total > 0 and stats.habits_done == stats.habits_total else ""
    body = "\n\n" + "\n".join(
        [
            f"🎯 Цели: {stats.goals_done}/{stats.goals_total}{goals_check}",
            f"⚡ Привычки: {stats.habits_done}/{stats.habits_total}{habits_check}",
            f"💭 Мысли: {stats.thoughts}",
            f"🙏 Благодарности: {stats.gratitude}",
            f"🔥 Стрик: {stats.streak_text}",
        ]
    )

    habits_block = ""
    if stats.habits_list:
        lines: list[str] = []
        for i, (title, done) in enumerate(stats.habits_list):
            mark = "✅" if done else "⬜️"
            lines.append(f"{i + 1}. {mark} {title}")
        habits_block = "\n\n<b>⚡ Привычки</b>\n" + "\n".join(lines)

    schedule_block = ""
    if stats.events_list:
        lines: list[str] = []
        for time_from, time_to, title in stats.events_list:
            time = ""
            if time_from and time_to:
                time = f"{time_from}–{time_to} "
            elif time_from:
                time = f"{time_from} "
            lines.append(f"{time}{title}")
        schedule_block = "\n\n<b>📅 Расписание</b>\n" + "\n".join(lines)

    return DashboardView(text=header + quote_block + body + habits_block + schedule_block, keyboard=keyboard)
