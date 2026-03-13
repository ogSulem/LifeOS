from __future__ import annotations

from datetime import date
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.goals import GoalsRepo
from lifeos_bot.database.models import DailyGoal

class GoalsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = GoalsRepo(session)

    async def get_goals_for_day(self, user_id: int, day: date) -> list[DailyGoal]:
        return await self.repo.list_for_day(user_id, day)

    async def add_goal(self, user_id: int, day: date, title: str) -> DailyGoal:
        return await self.repo.add(user_id, day, title)

    async def toggle_goal(self, goal_id: int) -> None:
        await self.repo.toggle_done(goal_id)

    async def toggle_goal_for_user(self, user_id: int, goal_id: int) -> bool:
        return await self.repo.toggle_done_for_user(user_id, goal_id)

    async def delete_goal(self, goal_id: int) -> None:
        await self.repo.delete(goal_id)

    async def delete_goal_for_user(self, user_id: int, goal_id: int) -> bool:
        return bool(await self.repo.delete_for_user(user_id, goal_id))

    async def update_goal_title(self, goal_id: int, title: str) -> None:
        await self.repo.update_title(goal_id, title)

    async def update_goal_title_for_user(self, user_id: int, goal_id: int, title: str) -> bool:
        return await self.repo.update_title_for_user(user_id, goal_id, title)

    async def move_goal_to_day_for_user(self, user_id: int, goal_id: int, day: date, *, days_delta: int) -> bool:
        new_day = day + timedelta(days=days_delta)
        return await self.repo.move_to_day_for_user(user_id, goal_id, new_day)
