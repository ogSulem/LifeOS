from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import ScheduleTemplateEvent


class ScheduleTemplateEventsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[ScheduleTemplateEvent]:
        res = await self.session.execute(
            select(ScheduleTemplateEvent)
            .where(ScheduleTemplateEvent.user_id == user_id)
            .order_by(ScheduleTemplateEvent.time_from.asc().nulls_last(), ScheduleTemplateEvent.id.asc())
        )
        return list(res.scalars().all())

    async def add(
        self,
        user_id: int,
        title: str,
        time_from: str | None,
    ) -> ScheduleTemplateEvent:
        evt = ScheduleTemplateEvent(user_id=user_id, title=title, time_from=time_from)
        self.session.add(evt)
        await self.session.flush()
        return evt

    async def replace_all(self, user_id: int, items: list[tuple[str | None, str]]) -> None:
        await self.session.execute(delete(ScheduleTemplateEvent).where(ScheduleTemplateEvent.user_id == user_id))
        for time_from, title in items:
            self.session.add(ScheduleTemplateEvent(user_id=user_id, title=title, time_from=time_from))
        await self.session.flush()

    async def delete(self, template_event_id: int) -> None:
        await self.session.execute(delete(ScheduleTemplateEvent).where(ScheduleTemplateEvent.id == template_event_id))

    async def delete_for_user(self, user_id: int, template_event_id: int) -> int:
        res = await self.session.execute(
            delete(ScheduleTemplateEvent).where(
                ScheduleTemplateEvent.id == template_event_id,
                ScheduleTemplateEvent.user_id == user_id,
            )
        )
        return int(res.rowcount or 0)
