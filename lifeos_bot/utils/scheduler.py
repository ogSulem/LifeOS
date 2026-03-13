from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot

from sqlalchemy import select

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.models import Subscription, User
from lifeos_bot.keyboards.tracking_kb import day_rating_kb, morning_kb
from lifeos_bot.utils.telegram_safe import safe_send_message


_scheduler: AsyncIOScheduler | None = None


MORNING_AT = time(hour=6, minute=0)
EVENING_AT = time(hour=22, minute=0)


async def start_scheduler(bot: Bot) -> None:
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")

    _scheduler.add_job(
        _tick,
        trigger="interval",
        seconds=60,
        args=[bot],
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()


async def _tick(bot: Bot) -> None:
    try:
        await _morning_tick(bot)
        await _evening_tick(bot)
    except Exception:
        logging.exception("Scheduler tick failed")


def _local_now(user_tz: str) -> datetime:
    try:
        tz = ZoneInfo(user_tz)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz=tz)


def _in_minute_window(now: datetime, target: time) -> bool:
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    t0 = day_start.replace(hour=target.hour, minute=target.minute)
    t1 = t0 + timedelta(minutes=5)
    return t0 <= now < t1


async def _morning_tick(bot: Bot) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        res = await session.execute(
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                User.dashboard_chat_id.is_not(None),
                User.dashboard_message_id.is_not(None),
                Subscription.is_active.is_(True),
            )
        )
        users = list(res.scalars().all())

        for user in users:
            now = _local_now(user.tz)
            if not _in_minute_window(now, MORNING_AT):
                continue
            day = now.date()
            if user.last_morning_prompt_day == day:
                continue

            sent = await safe_send_message(
                bot,
                chat_id=int(user.dashboard_chat_id),
                text="☀️ Доброе утро. Во сколько вы встали?",
                reply_markup=morning_kb(),
            )
            if sent is None:
                continue

            user.last_morning_prompt_day = day

        await session.commit()


async def _evening_tick(bot: Bot) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        res = await session.execute(
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                User.dashboard_chat_id.is_not(None),
                User.dashboard_message_id.is_not(None),
                Subscription.is_active.is_(True),
            )
        )
        users = list(res.scalars().all())

        for user in users:
            now = _local_now(user.tz)
            if not _in_minute_window(now, EVENING_AT):
                continue
            day = now.date()
            if user.last_evening_prompt_day == day:
                continue

            sent = await safe_send_message(
                bot,
                chat_id=int(user.dashboard_chat_id),
                text="Оцените день",
                reply_markup=day_rating_kb(),
            )
            if sent is None:
                continue

            user.last_evening_prompt_day = day

        await session.commit()


async def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return

    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        logging.exception("Failed to shutdown scheduler")
    _scheduler = None
