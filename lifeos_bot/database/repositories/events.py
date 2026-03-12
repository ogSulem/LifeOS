from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Event


class EventsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_day(self, user_id: int, day: date) -> list[Event]:
        res = await self.session.execute(
            select(Event)
            .where(Event.user_id == user_id, Event.day == day)
            .order_by(Event.time_from.asc().nulls_last(), Event.id.asc())
        )
        return list(res.scalars().all())

    async def add(
        self,
        user_id: int,
        day: date,
        title: str,
        time_from: str | None = None,
        time_to: str | None = None,
    ) -> Event:
        event = Event(user_id=user_id, day=day, title=title, time_from=time_from, time_to=time_to)
        self.session.add(event)
        await self.session.flush()
        return event

    async def update(
        self,
        event_id: int,
        title: str,
        time_from: str | None = None,
        time_to: str | None = None,
    ) -> None:
        event = await self.session.get(Event, event_id)
        if event is None:
            return
        event.title = title
        event.time_from = time_from
        event.time_to = time_to

    async def update_for_user(
        self,
        user_id: int,
        event_id: int,
        title: str,
        time_from: str | None = None,
        time_to: str | None = None,
    ) -> bool:
        event = await self.session.get(Event, event_id)
        if event is None or int(event.user_id) != int(user_id):
            return False
        event.title = title
        event.time_from = time_from
        event.time_to = time_to
        return True

    async def delete(self, event_id: int) -> None:
        await self.session.execute(delete(Event).where(Event.id == event_id))

    async def delete_for_user(self, user_id: int, event_id: int) -> int:
        res = await self.session.execute(delete(Event).where(Event.id == event_id, Event.user_id == user_id))
        return int(res.rowcount or 0)

    async def delete_for_day_for_user(self, user_id: int, day: date) -> int:
        res = await self.session.execute(delete(Event).where(Event.user_id == user_id, Event.day == day))
        return int(res.rowcount or 0)
