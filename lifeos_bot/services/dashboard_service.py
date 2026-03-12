from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import DailyGoal, DailyStat, Event, Gratitude, Habit, HabitLog, SleepLog, Thought


@dataclass(frozen=True)
class DashboardStats:
    goals_total: int
    goals_done: int
    thoughts: int
    gratitude: int
    events: int
    habits_total: int
    habits_done: int
    streak: int
    streak_text: str
    habits_list: list[tuple[str, bool]] = field(default_factory=list)
    events_list: list[tuple[str | None, str | None, str]] = field(default_factory=list)
    wakeup_at: str | None = None
    sleep_at: str | None = None
    mood: int | None = None
    day_rating: int | None = None


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stats_for_day(self, user_id: int, day: date) -> DashboardStats:
        thoughts = await self._count(Thought, user_id, day)
        gratitude = await self._count(Gratitude, user_id, day)
        events_list = await self._events_day(user_id, day)
        events = len(events_list)

        goals_total = await self._count(DailyGoal, user_id, day)
        goals_done = await self._count(DailyGoal, user_id, day, done_only=True)

        habits_total, habits_done, habits_list = await self._habits_day(user_id, day)

        wakeup_at, sleep_at = await self._sleep_day(user_id, day)
        mood, day_rating = await self._day_stats(user_id, day)

        streak = await self._calculate_streak(user_id, day)
        streak_text = f"{streak} " + self._get_day_word(streak)

        return DashboardStats(
            goals_total=goals_total,
            goals_done=goals_done,
            thoughts=thoughts,
            gratitude=gratitude,
            events=events,
            habits_total=habits_total,
            habits_done=habits_done,
            habits_list=habits_list,
            streak=streak,
            streak_text=streak_text,
            events_list=events_list,
            wakeup_at=wakeup_at,
            sleep_at=sleep_at,
            mood=mood,
            day_rating=day_rating,
        )

    async def _calculate_streak(self, user_id: int, start_day: date) -> int:
        days_back = 365
        date_from = start_day - timedelta(days=days_back)

        goals_days_stmt = (
            select(DailyGoal.day.label("day"))
            .where(
                DailyGoal.user_id == user_id,
                DailyGoal.day.between(date_from, start_day),
                DailyGoal.is_done.is_(True),
            )
            .group_by(DailyGoal.day)
        )

        habits_days_stmt = (
            select(HabitLog.day.label("day"))
            .select_from(HabitLog)
            .join(Habit, Habit.id == HabitLog.habit_id)
            .where(
                Habit.user_id == user_id,
                Habit.is_archived.is_(False),
                HabitLog.day.between(date_from, start_day),
                HabitLog.is_done.is_(True),
            )
            .group_by(HabitLog.day)
        )

        days_subq = union_all(goals_days_stmt, habits_days_stmt).subquery("days")
        stmt = select(days_subq.c.day).distinct()
        res = await self.session.execute(stmt)
        active_days = {d for d in res.scalars().all() if d is not None}

        streak = 0
        current_day = start_day
        while current_day in active_days:
            streak += 1
            current_day -= timedelta(days=1)
        return streak

    def _get_day_word(self, n: int) -> str:
        if 11 <= n % 100 <= 14:
            return "дней"
        last_digit = n % 10
        if last_digit == 1:
            return "день"
        if 2 <= last_digit <= 4:
            return "дня"
        return "дней"

    async def _count(self, model: type, user_id: int, day: date, done_only: bool = False) -> int:
        stmt = select(func.count()).select_from(model)
        if hasattr(model, "user_id"):
            stmt = stmt.where(model.user_id == user_id)
        if hasattr(model, "day"):
            stmt = stmt.where(model.day == day)
        if done_only and hasattr(model, "is_done"):
            stmt = stmt.where(model.is_done.is_(True))
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def _habits_day(self, user_id: int, day: date) -> tuple[int, int, list[tuple[str, bool]]]:
        res = await self.session.execute(
            select(Habit.id).where(Habit.user_id == user_id, Habit.is_archived.is_(False))
        )
        habit_ids = [int(x) for x in res.scalars().all()]
        total = len(habit_ids)
        if not habit_ids:
            return 0, 0, []

        res = await self.session.execute(
            select(func.count())
            .select_from(HabitLog)
            .where(HabitLog.habit_id.in_(habit_ids), HabitLog.day == day, HabitLog.is_done.is_(True))
        )
        done = int(res.scalar_one() or 0)

        res = await self.session.execute(
            select(Habit.title, HabitLog.is_done)
            .select_from(Habit)
            .outerjoin(HabitLog, (HabitLog.habit_id == Habit.id) & (HabitLog.day == day))
            .where(Habit.user_id == user_id, Habit.is_archived.is_(False))
            .order_by(Habit.id.asc())
        )
        habits_list = [(str(title), bool(is_done)) for title, is_done in res.all()]

        return total, done, habits_list

    async def _events_day(self, user_id: int, day: date) -> list[tuple[str | None, str | None, str]]:
        res = await self.session.execute(
            select(Event.time_from, Event.time_to, Event.title)
            .where(Event.user_id == user_id, Event.day == day)
            .order_by(Event.time_from.asc().nulls_last(), Event.id.asc())
        )
        return [(t_from, t_to, str(title)) for t_from, t_to, title in res.all()]

    async def _sleep_day(self, user_id: int, day: date) -> tuple[str | None, str | None]:
        res = await self.session.execute(
            select(SleepLog.wakeup_at, SleepLog.sleep_at).where(SleepLog.user_id == user_id, SleepLog.day == day)
        )
        row = res.one_or_none()
        if row is None:
            return None, None

        wakeup_at, sleep_at = row
        tz_msk = ZoneInfo("Europe/Moscow")
        tz_utc = ZoneInfo("UTC")

        wakeup_str = (
            wakeup_at.replace(tzinfo=tz_utc).astimezone(tz_msk).strftime("%H:%M") if wakeup_at else None
        )
        sleep_str = sleep_at.replace(tzinfo=tz_utc).astimezone(tz_msk).strftime("%H:%M") if sleep_at else None
        return wakeup_str, sleep_str

    async def _day_stats(self, user_id: int, day: date) -> tuple[int | None, int | None]:
        res = await self.session.execute(
            select(DailyStat.mood, DailyStat.day_rating).where(DailyStat.user_id == user_id, DailyStat.day == day)
        )
        row = res.one_or_none()
        if row is None:
            return None, None
        mood, day_rating = row
        return int(mood) if mood is not None else None, int(day_rating) if day_rating is not None else None
