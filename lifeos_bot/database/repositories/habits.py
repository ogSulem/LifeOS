from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Habit, HabitLog


class HabitsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_habits(self, user_id: int) -> list[Habit]:
        res = await self.session.execute(
            select(Habit)
            .where(Habit.user_id == user_id, Habit.is_archived.is_(False))
            .order_by(Habit.id.asc())
        )
        return list(res.scalars().all())

    async def list_habits_all(self, user_id: int) -> list[Habit]:
        res = await self.session.execute(
            select(Habit)
            .where(Habit.user_id == user_id)
            .order_by(Habit.id.asc())
        )
        return list(res.scalars().all())

    async def add_habit(self, user_id: int, title: str) -> Habit:
        habit = Habit(user_id=user_id, title=title, is_archived=False)
        self.session.add(habit)
        await self.session.flush()
        return habit

    async def get_by_id(self, habit_id: int) -> Habit | None:
        return await self.session.get(Habit, habit_id)

    async def archive_habit(self, habit_id: int) -> None:
        habit = await self.session.get(Habit, habit_id)
        if habit is None:
            return
        habit.is_archived = True

    async def archive_habit_for_user(self, user_id: int, habit_id: int) -> bool:
        habit = await self.session.get(Habit, habit_id)
        if habit is None or int(habit.user_id) != int(user_id) or bool(habit.is_archived):
            return False
        habit.is_archived = True
        return True

    async def get_log(self, habit_id: int, day: date) -> HabitLog | None:
        res = await self.session.execute(
            select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.day == day)
        )
        return res.scalar_one_or_none()

    async def set_done(self, habit_id: int, day: date, is_done: bool) -> None:
        log = await self.get_log(habit_id, day)
        if log is None:
            log = HabitLog(habit_id=habit_id, day=day, is_done=is_done)
            self.session.add(log)
            await self.session.flush()
            return
        log.is_done = is_done

    async def toggle_done(self, habit_id: int, day: date) -> None:
        log = await self.get_log(habit_id, day)
        if log is None:
            log = HabitLog(habit_id=habit_id, day=day, is_done=True)
            self.session.add(log)
            await self.session.flush()
            return
        log.is_done = not log.is_done

    async def toggle_done_for_user(self, user_id: int, habit_id: int, day: date) -> bool:
        habit = await self.session.get(Habit, habit_id)
        if habit is None or int(habit.user_id) != int(user_id) or bool(habit.is_archived):
            return False
        await self.toggle_done(habit_id, day)
        return True

    async def list_logs_for_day(self, habit_ids: list[int], day: date) -> dict[int, HabitLog]:
        if not habit_ids:
            return {}
        res = await self.session.execute(
            select(HabitLog).where(and_(HabitLog.habit_id.in_(habit_ids), HabitLog.day == day))
        )
        logs = list(res.scalars().all())
        return {x.habit_id: x for x in logs}
