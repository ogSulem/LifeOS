from __future__ import annotations

from datetime import date
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery

from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_delete_message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.services.settings_service import SettingsService
from lifeos_bot.utils.date_manager import shift_day
from lifeos_bot.utils.renderer import render_dashboard

router = Router()


@router.callback_query(F.data.startswith("day:"))
async def change_day(call: CallbackQuery) -> None:
    if call.from_user is None:
        return
    delta_str = call.data.split(":", 1)[1]
    try:
        delta = int(delta_str)
    except ValueError:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = UsersRepo(session)
        user = await repo.get_or_create(call.from_user.id)
        new_day = date.today() if delta == 0 else shift_day(user.selected_date, delta)
        await repo.set_selected_date(user.id, new_day)
        await SettingsService(session).apply_templates_for_day(user.id, new_day)
        stats = await DashboardService(session).stats_for_day(user.id, new_day)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    view = render_dashboard(new_day, quote, dashboard_kb(new_day, tg_user_id=user.tg_user_id), stats)

    if call.message:
        await safe_edit_message_text(call.message, view.text, reply_markup=view.keyboard)
    await safe_answer_callback(call)


@router.callback_query(F.data == "nav:dashboard")
async def open_dashboard(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = UsersRepo(session)
        user = await repo.get_or_create(call.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)
    await safe_edit_message_text(call.message, view.text, reply_markup=view.keyboard)
    await safe_answer_callback(call)


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery) -> None:
    await safe_answer_callback(call)
