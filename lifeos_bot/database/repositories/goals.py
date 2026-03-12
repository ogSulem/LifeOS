from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import DailyGoal


class GoalsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_day(self, user_id: int, day: date) -> list[DailyGoal]:
        res = await self.session.execute(
            select(DailyGoal)
            .where(DailyGoal.user_id == user_id, DailyGoal.day == day)
            .order_by(DailyGoal.id.asc())
        )
        return list(res.scalars().all())

    async def add(self, user_id: int, day: date, title: str) -> DailyGoal:
        goal = DailyGoal(user_id=user_id, day=day, title=title, is_done=False)
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def toggle_done(self, goal_id: int) -> None:
        goal = await self.session.get(DailyGoal, goal_id)
        if goal is None:
            return
        goal.is_done = not goal.is_done

    async def toggle_done_for_user(self, user_id: int, goal_id: int) -> bool:
        goal = await self.session.get(DailyGoal, goal_id)
        if goal is None or int(goal.user_id) != int(user_id):
            return False
        goal.is_done = not goal.is_done
        return True

    async def delete(self, goal_id: int) -> None:
        await self.session.execute(delete(DailyGoal).where(DailyGoal.id == goal_id))

    async def delete_for_user(self, user_id: int, goal_id: int) -> int:
        res = await self.session.execute(
            delete(DailyGoal).where(DailyGoal.id == goal_id, DailyGoal.user_id == user_id)
        )
        return int(res.rowcount or 0)

    async def update_title(self, goal_id: int, title: str) -> None:
        goal = await self.session.get(DailyGoal, goal_id)
        if goal is None:
            return
        goal.title = title

    async def update_title_for_user(self, user_id: int, goal_id: int, title: str) -> bool:
        goal = await self.session.get(DailyGoal, goal_id)
        if goal is None or int(goal.user_id) != int(user_id):
            return False
        goal.title = title
        return True
