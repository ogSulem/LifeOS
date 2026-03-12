from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.payments import PaymentsRepo
from lifeos_bot.database.repositories.subscriptions import SubscriptionsRepo
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.payments_kb import buy_subscription_kb, yookassa_payment_kb
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.payment_service import PaymentService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.utils.renderer import render_dashboard

from pathlib import Path

router = Router()


@router.callback_query(F.data == "nav:payments")
async def open_payments(call: CallbackQuery) -> None:
    if call.message is None:
        await safe_answer_callback(call)
        return
    await safe_edit_message_text(
        call.message,
        "<b>Подписка</b>\n\nОткройте оплату и активируйте подписку.",
        reply_markup=buy_subscription_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "pay:buy")
async def buy_subscription(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        await safe_answer_callback(call, "ЮKassa не настроена", show_alert=True)
        return

    amount_rub = 1 if settings.admin_id and call.from_user.id == settings.admin_id else settings.price_month

    service = PaymentService()
    created = await service.create_subscription_payment(
        amount_rub=amount_rub,
        description=f"LifeOS Assistant subscription for tg_user_id={call.from_user.id}",
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        await PaymentsRepo(session).create_attempt(
            user_id=user.id,
            provider_payment_id=created.payment_id,
            amount_rub=amount_rub,
            status=created.status,
        )
        await session.commit()

    await safe_edit_message_text(
        call.message,
        "<b>Подписка</b>\n\n1) Нажмите «Оплатить»\n2) После оплаты нажмите «Проверить оплату».",
        reply_markup=yookassa_payment_kb(created.confirmation_url, created.payment_id),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("pay:check:"))
async def check_payment(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    payment_id = call.data.split(":", 2)[2]
    if not payment_id:
        await safe_answer_callback(call)
        return

    service = PaymentService()
    status = await service.get_payment_status(payment_id)

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        payments_repo = PaymentsRepo(session)
        attempt = await payments_repo.get_by_provider_payment_id(payment_id)
        if attempt is None or int(attempt.user_id) != int(user.id):
            await session.commit()
            await safe_answer_callback(call, "Этот платёж не привязан к вашему аккаунту", show_alert=True)
            return

        await payments_repo.set_status(payment_id, status)
        if status == "succeeded":
            await SubscriptionsRepo(session).activate_by_user_id(user.id, days=30)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    if status == "succeeded" and user.dashboard_chat_id and user.dashboard_message_id:
        data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
        quote = QuoteService(data_path).get_quote_of_day()
        view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)
        await safe_bot_edit_message_text(
            bot=call.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=view.keyboard,
        )
        await safe_answer_callback(call, "Подписка активирована")
        return

    await safe_answer_callback(call, f"Статус платежа: {status}")
