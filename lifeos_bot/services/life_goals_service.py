from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.life_goals import LifeGoalsRepo
from lifeos_bot.database.models import LifeGoal, LifeGoalCategory

class LifeGoalsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = LifeGoalsRepo(session)

    async def get_categories(self, user_id: int) -> list[LifeGoalCategory]:
        return await self.repo.list_categories(user_id)

    async def add_category(self, user_id: int, title: str) -> LifeGoalCategory:
        return await self.repo.add_category(user_id, title)

    async def get_category(self, category_id: int) -> LifeGoalCategory | None:
        return await self.repo.get_category(category_id)

    async def delete_category_for_user(self, user_id: int, category_id: int) -> bool:
        return bool(await self.repo.delete_category_for_user(user_id, category_id))

    async def get_goals(self, category_id: int) -> list[LifeGoal]:
        return await self.repo.list_goals(category_id)

    async def add_goal(self, category_id: int, title: str) -> LifeGoal:
        return await self.repo.add_goal(category_id, title)

    async def toggle_goal(self, goal_id: int) -> None:
        await self.repo.toggle_goal_done(goal_id)

    async def toggle_goal_for_user(self, user_id: int, category_id: int, goal_id: int) -> bool:
        return await self.repo.toggle_goal_done_for_user(user_id, category_id, goal_id)

    async def delete_goal(self, goal_id: int) -> None:
        await self.repo.delete_goal(goal_id)

    async def delete_goal_for_user(self, user_id: int, category_id: int, goal_id: int) -> bool:
        return bool(await self.repo.delete_goal_for_user(user_id, category_id, goal_id))
