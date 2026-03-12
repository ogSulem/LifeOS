from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import DailyGoal, DailyStat, Event, Gratitude, Habit, HabitLog, SleepLog, Thought


@dataclass(frozen=True)
class AnalyticsSnapshot:
    period_title: str
    date_from: date
    date_to: date

    thoughts: int
    goals_total: int
    goals_done: int
    gratitude: int
    events: int

    habits_total: int
    habits_done: int

    wakeup_at: datetime | None = None
    sleep_at: datetime | None = None
    mood: int | None = None
    day_rating: int | None = None


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot_day(self, user_id: int, day: date) -> AnalyticsSnapshot:
        return await self._snapshot_range(user_id, day, day, period_title="День")

    async def snapshot_week(self, user_id: int, day: date) -> AnalyticsSnapshot:
        date_from = day - timedelta(days=6)
        return await self._snapshot_range(user_id, date_from, day, period_title="Неделя")

    async def snapshot_month(self, user_id: int, day: date) -> AnalyticsSnapshot:
        date_from = day - timedelta(days=29)
        return await self._snapshot_range(user_id, date_from, day, period_title="Месяц")

    async def get_timeline(self, user_id: int, date_from: date, date_to: date) -> list[dict[str, Any]]:
        # Возвращает динамику выполнения целей и привычек по дням
        goals_total_stmt = (
            select(DailyGoal.day, func.count())
            .where(DailyGoal.user_id == user_id, DailyGoal.day.between(date_from, date_to))
            .group_by(DailyGoal.day)
        )
        goals_done_stmt = (
            select(DailyGoal.day, func.count())
            .where(
                DailyGoal.user_id == user_id,
                DailyGoal.day.between(date_from, date_to),
                DailyGoal.is_done.is_(True),
            )
            .group_by(DailyGoal.day)
        )
        habits_done_stmt = (
            select(HabitLog.day, func.count())
            .select_from(HabitLog)
            .join(Habit, Habit.id == HabitLog.habit_id)
            .where(
                Habit.user_id == user_id,
                Habit.is_archived.is_(False),
                HabitLog.day.between(date_from, date_to),
                HabitLog.is_done.is_(True),
            )
            .group_by(HabitLog.day)
        )

        res = await self.session.execute(goals_total_stmt)
        goals_total_by_day = {row[0]: int(row[1] or 0) for row in res.all()}
        res = await self.session.execute(goals_done_stmt)
        goals_done_by_day = {row[0]: int(row[1] or 0) for row in res.all()}
        res = await self.session.execute(habits_done_stmt)
        habits_done_by_day = {row[0]: int(row[1] or 0) for row in res.all()}

        timeline: list[dict[str, Any]] = []
        curr = date_from
        while curr <= date_to:
            goals_total = goals_total_by_day.get(curr, 0)
            goals_done = goals_done_by_day.get(curr, 0)
            habits_done = habits_done_by_day.get(curr, 0)
            timeline.append(
                {
                    "date": curr,
                    "goals_pct": int((goals_done / goals_total * 100) if goals_total > 0 else 0),
                    "habits_done": habits_done,
                }
            )
            curr += timedelta(days=1)
        return timeline

    async def _snapshot_range(
        self,
        user_id: int,
        date_from: date,
        date_to: date,
        period_title: str,
    ) -> AnalyticsSnapshot:
        thoughts = await self._count(Thought, user_id, date_from, date_to)
        gratitude = await self._count(Gratitude, user_id, date_from, date_to)
        events = await self._count(Event, user_id, date_from, date_to)

        goals_total = await self._count(DailyGoal, user_id, date_from, date_to)
        goals_done = await self._count(DailyGoal, user_id, date_from, date_to, done_only=True)

        habits_total, habits_done = await self._habits_stats(user_id, date_from, date_to)

        wakeup_at = None
        sleep_at = None
        mood = None
        day_rating = None
        if date_from == date_to:
            res = await self.session.execute(
                select(SleepLog).where(SleepLog.user_id == user_id, SleepLog.day == date_to)
            )
            log = res.scalar_one_or_none()
            if log:
                wakeup_at = log.wakeup_at
                sleep_at = log.sleep_at

            res = await self.session.execute(
                select(DailyStat).where(DailyStat.user_id == user_id, DailyStat.day == date_to)
            )
            stat = res.scalar_one_or_none()
            if stat:
                mood = stat.mood
                day_rating = stat.day_rating

        return AnalyticsSnapshot(
            period_title=period_title,
            date_from=date_from,
            date_to=date_to,
            thoughts=thoughts,
            goals_total=goals_total,
            goals_done=goals_done,
            gratitude=gratitude,
            events=events,
            habits_total=habits_total,
            habits_done=habits_done,
            wakeup_at=wakeup_at,
            sleep_at=sleep_at,
            mood=int(mood) if mood is not None else None,
            day_rating=int(day_rating) if day_rating is not None else None,
        )

    async def _count(
        self,
        model: type,
        user_id: int,
        date_from: date,
        date_to: date,
        done_only: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(model)

        if hasattr(model, "user_id"):
            stmt = stmt.where(model.user_id == user_id)
        if hasattr(model, "day"):
            stmt = stmt.where(model.day.between(date_from, date_to))
        if done_only and hasattr(model, "is_done"):
            stmt = stmt.where(model.is_done.is_(True))

        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def _habits_stats(self, user_id: int, date_from: date, date_to: date) -> tuple[int, int]:
        res = await self.session.execute(
            select(Habit.id).where(Habit.user_id == user_id, Habit.is_archived.is_(False))
        )
        habit_ids = [int(x) for x in res.scalars().all()]
        habits_total = len(habit_ids)
        if not habit_ids:
            return 0, 0

        res = await self.session.execute(
            select(func.count())
            .select_from(HabitLog)
            .where(HabitLog.habit_id.in_(habit_ids), HabitLog.day.between(date_from, date_to), HabitLog.is_done.is_(True))
        )
        done = int(res.scalar_one() or 0)
        return habits_total, done
