from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.repositories.habit_templates import HabitTemplatesRepo
from lifeos_bot.database.repositories.habits import HabitsRepo
from lifeos_bot.database.repositories.schedule_template_events import ScheduleTemplateEventsRepo
from lifeos_bot.database.repositories.events import EventsRepo
from lifeos_bot.database.repositories.schedule_template_applied_days import ScheduleTemplateAppliedDaysRepo


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.templates = ScheduleTemplateEventsRepo(session)
        self.events = EventsRepo(session)
        self.applied_days = ScheduleTemplateAppliedDaysRepo(session)
        self.habit_templates = HabitTemplatesRepo(session)
        self.habits = HabitsRepo(session)

    async def list_schedule_template(self, user_id: int):
        return await self.templates.list_for_user(user_id)

    async def replace_schedule_template(self, user_id: int, items: list[tuple[str | None, str]]) -> None:
        await self.templates.replace_all(user_id, items)

    async def list_habit_template(self, user_id: int):
        return await self.habit_templates.list_for_user(user_id)

    async def replace_habit_template(self, user_id: int, titles: list[str]) -> None:
        await self.habit_templates.replace_all(user_id, titles)

    async def apply_schedule_template_seed_once(self, user_id: int, day: date) -> None:
        if await self.applied_days.is_applied(user_id, day):
            return

        existing = await self.events.list_for_day(user_id, day)
        existing_keys = {(e.time_from or "", str(e.title).strip()) for e in existing}

        items = await self.templates.list_for_user(user_id)
        for x in items:
            key = ((x.time_from or ""), str(x.title).strip())
            if key in existing_keys:
                continue
            await self.events.add(user_id, day, title=x.title, time_from=x.time_from, time_to=None)

        await self.applied_days.mark_applied(user_id, day)

    async def apply_habit_template(self, user_id: int) -> None:
        templates = await self.habit_templates.list_for_user(user_id)
        if not templates:
            return

        existing = await self.habits.list_habits_all(user_id)
        existing_titles = {str(h.title).strip().lower() for h in existing}
        for t in templates:
            title = str(t.title).strip()
            if not title:
                continue
            if title.lower() in existing_titles:
                continue
            await self.habits.add_habit(user_id, title)
            existing_titles.add(title.lower())

    async def apply_templates_for_day(self, user_id: int, day: date) -> None:
        await self.apply_schedule_template_seed_once(user_id, day)
        await self.apply_habit_template(user_id)
