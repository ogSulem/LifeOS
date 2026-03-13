from __future__ import annotations

import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.analytics_kb import analytics_kb
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.ai_service import AIService
from lifeos_bot.services.analytics_service import AnalyticsService
from lifeos_bot.utils.renderer import render_dashboard
from lifeos_bot.services.quote_service import QuoteService

from lifeos_bot.config import settings

from pathlib import Path

router = Router()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyticsView:
    text: str


def _format_time_msk(dt) -> str:
    if dt is None:
        return ""
    tz_msk = ZoneInfo("Europe/Moscow")
    tz_utc = ZoneInfo("UTC")
    try:
        return dt.replace(tzinfo=tz_utc).astimezone(tz_msk).strftime("%H:%M")
    except Exception:
        return dt.strftime("%H:%M")


async def _render_analytics_text(user_id: int, snapshot) -> AnalyticsView:
    goals_pct = 0
    if snapshot.goals_total:
        goals_pct = int((snapshot.goals_done / snapshot.goals_total) * 100)

    text = (
        f"<b>📊 Аналитика — {snapshot.period_title}</b>\n"
        f"<b>Период:</b> {snapshot.date_from.strftime('%d.%m.%Y')} → {snapshot.date_to.strftime('%d.%m.%Y')}\n\n"
        f"<b>🎯 Цели:</b> {snapshot.goals_done}/{snapshot.goals_total} ({goals_pct}%)\n"
        f"<b>⚡ Привычки:</b> выполнено {snapshot.habits_done} (всего активных {snapshot.habits_total})\n"
        f"<b>💭 Мысли:</b> {snapshot.thoughts}\n"
        f"<b>🙏 Благодарности:</b> {snapshot.gratitude}\n"
        f"<b>📅 События:</b> {snapshot.events}\n"
    )

    if snapshot.wakeup_at or snapshot.sleep_at:
        text += "\n<b>Сон</b>\n"
        if snapshot.wakeup_at:
            text += f"- Подъем: {_format_time_msk(snapshot.wakeup_at)}\n"
        if snapshot.sleep_at:
            text += f"- Сон: {_format_time_msk(snapshot.sleep_at)}\n"

    if snapshot.day_rating is not None:
        text += "\n<b>📝 День</b>\n"
        if snapshot.day_rating is not None:
            try:
                day_rating = max(0, min(5, int(snapshot.day_rating)))
            except (TypeError, ValueError):
                day_rating = 0
            text += f"- Оценка дня: {'⭐' * day_rating}\n"

    text += f"\n<b>Ревью</b>\nФактическое выполнение целей: {goals_pct}%\n"

    session_maker = get_session_maker()
    async with session_maker() as session:
        timeline = await AnalyticsService(session).get_timeline(user_id, snapshot.date_from, snapshot.date_to)
        await session.commit()

    ai_service = AIService(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        enabled=settings.openrouter_enabled,
    )
    try:
        ai_advice, is_ai = await ai_service.get_coach_recommendation_with_source(
            user_id=user_id,
            snapshot=snapshot,
            timeline=timeline,
        )
    except Exception:
        logger.exception("AI coach recommendation failed (user_id=%s)", user_id)
        ai_advice = "AI-коуч сейчас недоступен."
        is_ai = True

    if not is_ai:
        ai_advice = f"{ai_advice}\n(не нейросеть)"

    text += f"\n<b>AI-коуч</b>\n{ai_advice}\n"

    return AnalyticsView(text=text)


async def _get_snapshot(tg_user_id: int, mode: str):
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)
        service = AnalyticsService(session)
        if mode == "week":
            snap = await service.snapshot_week(user.id, user.selected_date)
        elif mode == "month":
            snap = await service.snapshot_month(user.id, user.selected_date)
        else:
            snap = await service.snapshot_day(user.id, user.selected_date)
        await session.commit()
    return user, snap


@router.callback_query(F.data == "nav:analytics")
async def open_analytics(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    user, snap = await _get_snapshot(call.from_user.id, mode="day")
    await state.update_data(analytics_mode="day")
    view = await _render_analytics_text(user_id=user.id, snapshot=snap)
    await safe_edit_message_text(call.message, view.text, reply_markup=analytics_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("analytics:"))
async def switch_analytics(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    if not call.data:
        await safe_answer_callback(call)
        return
    parts = call.data.split(":", 1)
    if len(parts) != 2:
        await safe_answer_callback(call)
        return
    mode = parts[1]
    if mode not in {"day", "week", "month", "ai"}:
        await safe_answer_callback(call)
        return

    if mode == "ai":
        data = await state.get_data()
        current_mode = data.get("analytics_mode")
        if current_mode not in {"day", "week", "month"}:
            current_mode = "day"

        user, snap = await _get_snapshot(call.from_user.id, mode=str(current_mode))
        view = await _render_analytics_text(user_id=user.id, snapshot=snap)
        await safe_edit_message_text(call.message, view.text, reply_markup=analytics_kb())
        await safe_answer_callback(call)
        return

    await state.update_data(analytics_mode=mode)
    user, snap = await _get_snapshot(call.from_user.id, mode=mode)
    view = await _render_analytics_text(user_id=user.id, snapshot=snap)
    await safe_edit_message_text(call.message, view.text, reply_markup=analytics_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "analytics:back")
async def close_analytics(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    dash = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)
    await safe_edit_message_text(call.message, dash.text, reply_markup=dash.keyboard)
    await safe_answer_callback(call)
