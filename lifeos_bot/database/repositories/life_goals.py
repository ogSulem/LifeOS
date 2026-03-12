from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import LifeGoal, LifeGoalCategory


class LifeGoalsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(self, user_id: int) -> list[LifeGoalCategory]:
        res = await self.session.execute(
            select(LifeGoalCategory)
            .where(LifeGoalCategory.user_id == user_id)
            .order_by(LifeGoalCategory.id.asc())
        )
        return list(res.scalars().all())

    async def add_category(self, user_id: int, title: str) -> LifeGoalCategory:
        cat = LifeGoalCategory(user_id=user_id, title=title)
        self.session.add(cat)
        await self.session.flush()
        return cat

    async def get_category(self, category_id: int) -> LifeGoalCategory | None:
        return await self.session.get(LifeGoalCategory, category_id)

    async def delete_category_for_user(self, user_id: int, category_id: int) -> int:
        res = await self.session.execute(
            delete(LifeGoalCategory).where(LifeGoalCategory.id == category_id, LifeGoalCategory.user_id == user_id)
        )
        return int(res.rowcount or 0)

    async def list_goals(self, category_id: int) -> list[LifeGoal]:
        res = await self.session.execute(
            select(LifeGoal).where(LifeGoal.category_id == category_id).order_by(LifeGoal.id.asc())
        )
        return list(res.scalars().all())

    async def add_goal(self, category_id: int, title: str) -> LifeGoal:
        goal = LifeGoal(category_id=category_id, title=title, is_done=False)
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def toggle_goal_done(self, goal_id: int) -> None:
        goal = await self.session.get(LifeGoal, goal_id)
        if goal is None:
            return
        goal.is_done = not goal.is_done

    async def toggle_goal_done_for_user(self, user_id: int, category_id: int, goal_id: int) -> bool:
        res = await self.session.execute(
            select(LifeGoal)
            .join(LifeGoalCategory, LifeGoalCategory.id == LifeGoal.category_id)
            .where(
                LifeGoal.id == goal_id,
                LifeGoal.category_id == category_id,
                LifeGoalCategory.user_id == user_id,
            )
        )
        goal = res.scalar_one_or_none()
        if goal is None:
            return False
        goal.is_done = not goal.is_done
        return True

    async def delete_goal(self, goal_id: int) -> None:
        await self.session.execute(delete(LifeGoal).where(LifeGoal.id == goal_id))

    async def delete_goal_for_user(self, user_id: int, category_id: int, goal_id: int) -> int:
        res = await self.session.execute(
            delete(LifeGoal)
            .where(
                LifeGoal.id == goal_id,
                LifeGoal.category_id == category_id,
                LifeGoal.category_id.in_(
                    select(LifeGoalCategory.id).where(LifeGoalCategory.user_id == user_id)
                ),
            )
        )
        return int(res.rowcount or 0)
