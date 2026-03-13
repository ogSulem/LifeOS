from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

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

    goals_block = ""
    if stats.goals_list:
        lines: list[str] = []
        for i, (title, done) in enumerate(stats.goals_list[:5]):
            mark = "✅" if done else "⬜️"
            lines.append(f"{i + 1}. {mark} {title}")
        goals_block = "\n\n<b>🎯 Цели дня</b>\n" + "\n".join(lines)

    habits_block = ""
    if stats.habits_list:
        undone = [(t, d) for t, d in stats.habits_list if not d]
        if undone:
            lines: list[str] = []
            for i, (title, done) in enumerate(undone[:5]):
                mark = "✅" if done else "⬜️"
                lines.append(f"{i + 1}. {mark} {title}")
            habits_block = "\n\n<b>⚡ Привычки</b>\n" + "\n".join(lines)

    schedule_block = ""
    if stats.events_list:
        tz_msk = ZoneInfo("Europe/Moscow")
        now_msk = datetime.now(tz_msk)

        items_all = stats.events_list
        items = items_all
        if day == now_msk.date():
            now_minutes = now_msk.hour * 60 + now_msk.minute

            def _time_to_minutes(t: str | None) -> int | None:
                if not t:
                    return None
                try:
                    hh_str, mm_str = t.split(":", 1)
                    hh = int(hh_str)
                    mm = int(mm_str)
                    if 0 <= hh <= 23 and 0 <= mm <= 59:
                        return hh * 60 + mm
                except Exception:
                    return None
                return None

            last_idx: int | None = None
            for i, (time_from, _time_to, _title) in enumerate(items_all):
                minutes = _time_to_minutes(time_from)
                if minutes is None:
                    continue
                if minutes <= now_minutes:
                    last_idx = i

            start_idx = last_idx if last_idx is not None else 0
            items = list(items_all[start_idx:])
            if start_idx > 0:
                untimed_before = [x for x in items_all[:start_idx] if not x[0]]
                if untimed_before:
                    items.extend(untimed_before)

        max_events = 10
        shown = items[:max_events]
        remaining = max(0, len(items) - len(shown))
        lines: list[str] = []
        for time_from, time_to, title in shown:
            time = ""
            if time_from and time_to:
                time = f"{time_from}–{time_to} "
            elif time_from:
                time = f"{time_from} "
            lines.append(f"{time}{title}")
        if remaining:
            lines.append(f"… и ещё {remaining}")
        schedule_block = "\n\n<b>📅 Расписание</b>\n" + "\n".join(lines)

    return DashboardView(text=header + quote_block + body + schedule_block + habits_block + goals_block, keyboard=keyboard)
