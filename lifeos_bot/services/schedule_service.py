from __future__ import annotations

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.events import EventsRepo
from lifeos_bot.database.models import Event

class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EventsRepo(session)

    async def get_events_for_day(self, user_id: int, day: date) -> list[Event]:
        return await self.repo.list_for_day(user_id, day)

    async def add_event(self, user_id: int, day: date, title: str, time_from: str | None = None, time_to: str | None = None) -> Event:
        return await self.repo.add(user_id, day, title, time_from, time_to)

    async def update_event(self, event_id: int, title: str, time_from: str | None = None, time_to: str | None = None) -> None:
        await self.repo.update(event_id, title, time_from, time_to)

    async def update_event_for_user(
        self,
        user_id: int,
        event_id: int,
        title: str,
        time_from: str | None = None,
        time_to: str | None = None,
    ) -> bool:
        return await self.repo.update_for_user(user_id, event_id, title, time_from, time_to)

    async def delete_event(self, event_id: int) -> None:
        await self.repo.delete(event_id)

    async def delete_event_for_user(self, user_id: int, event_id: int) -> bool:
        return bool(await self.repo.delete_for_user(user_id, event_id))
