from __future__ import annotations

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.habits import HabitsRepo
from lifeos_bot.database.models import Habit, HabitLog

class HabitService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = HabitsRepo(session)

    async def get_habits_with_logs(self, user_id: int, day: date) -> list[tuple[int, str, bool]]:
        habits = await self.repo.list_habits(user_id)
        logs = await self.repo.list_logs_for_day([h.id for h in habits], day)
        return [(h.id, h.title, bool(logs.get(h.id) and logs[h.id].is_done)) for h in habits]

    async def add_habit(self, user_id: int, title: str) -> Habit:
        return await self.repo.add_habit(user_id, title)

    async def toggle_habit(self, habit_id: int, day: date) -> None:
        await self.repo.toggle_done(habit_id, day)

    async def toggle_habit_for_user(self, user_id: int, habit_id: int, day: date) -> bool:
        return await self.repo.toggle_done_for_user(user_id, habit_id, day)

    async def get_habit(self, habit_id: int) -> Habit | None:
        return await self.repo.get_by_id(habit_id)

    async def delete_habit(self, habit_id: int) -> None:
        await self.repo.archive_habit(habit_id)

    async def delete_habit_for_user(self, user_id: int, habit_id: int) -> bool:
        return await self.repo.archive_habit_for_user(user_id, habit_id)
