from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message, safe_send_message

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.tracking_kb import day_rating_kb, morning_kb, sleep_kb
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.tracking_service import TrackingService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.utils.renderer import render_dashboard

from pathlib import Path

router = Router()


def _is_admin(tg_user_id: int) -> bool:
    return settings.admin_id is not None and tg_user_id == settings.admin_id


async def _rerender_dashboard(tg_user_id: int, bot) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    if not user.dashboard_chat_id or not user.dashboard_message_id:
        return

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    dash = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)

    await safe_bot_edit_message_text(
        bot=bot,
        chat_id=user.dashboard_chat_id,
        message_id=user.dashboard_message_id,
        text=dash.text,
        reply_markup=dash.keyboard,
    )


@router.message(Command("morning"))
async def morning_command(message: Message) -> None:
    await safe_send_message(
        message.bot,
        chat_id=message.chat.id,
        text="☀️ Доброе утро. Во сколько вы встали?",
        reply_markup=morning_kb(),
    )
    await safe_delete_message(message)


@router.callback_query(F.data == "admin:test:morning")
async def admin_test_morning(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await safe_send_message(
        call.bot,
        chat_id=call.message.chat.id,
        text="☀️ Доброе утро. Во сколько вы встали?",
        reply_markup=morning_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "track:wakeup")
async def morning_wakeup(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        try:
            tz = ZoneInfo(user.tz)
        except Exception:
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz=tz)
        day_local = now_local.date()
        await UsersRepo(session).set_selected_date(user.id, day_local)
        await TrackingService(session).track_wakeup(
            user.id,
            day_local,
            now_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
        )
        await session.commit()

    await safe_delete_message(call.message)

    await _rerender_dashboard(call.from_user.id, call.bot)
    await safe_answer_callback(call)


@router.message(Command("evening"))
async def evening_command(message: Message) -> None:
    await safe_send_message(
        message.bot,
        chat_id=message.chat.id,
        text="Оцените день",
        reply_markup=day_rating_kb(),
    )
    await safe_delete_message(message)


@router.callback_query(F.data == "admin:test:night")
async def admin_test_night(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await safe_send_message(
        call.bot,
        chat_id=call.message.chat.id,
        text="Оцените день",
        reply_markup=day_rating_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("track:rate:"))
async def evening_rate(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    rating = int(call.data.split(":", 2)[2])

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        try:
            tz = ZoneInfo(user.tz)
        except Exception:
            tz = ZoneInfo("UTC")
        day_local = datetime.now(tz=tz).date()
        await UsersRepo(session).set_selected_date(user.id, day_local)
        await TrackingService(session).track_rating(user.id, day_local, rating)
        await session.commit()

    await safe_delete_message(call.message)

    await _rerender_dashboard(call.from_user.id, call.bot)
    await safe_send_message(call.bot, chat_id=call.message.chat.id, text="🌙 Спокойной ночи", reply_markup=sleep_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "track:sleep")
async def evening_sleep(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        try:
            tz = ZoneInfo(user.tz)
        except Exception:
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz=tz)
        day_local = now_local.date()
        await UsersRepo(session).set_selected_date(user.id, day_local)
        await TrackingService(session).track_sleep(
            user.id,
            day_local,
            now_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
        )
        await session.commit()

    await safe_delete_message(call.message)

    await _rerender_dashboard(call.from_user.id, call.bot)
    await safe_answer_callback(call)
