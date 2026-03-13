from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from aiogram.types import CallbackQuery, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.services.gratitude_service import GratitudeService
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.gratitude_kb import gratitude_input_kb, gratitude_kb

from lifeos_bot.utils.pagination import paginate_by_chars

router = Router()


class GratitudeStates(StatesGroup):
    waiting_text = State()


@dataclass(frozen=True)
class GratitudeScreen:
    text: str


def _render_gratitude(day: date, items: list[str], page: int) -> tuple[GratitudeScreen, int, int]:
    header = f"<b>🙏 Благодарности</b>\n<b>Дата:</b> {day.strftime('%d.%m.%Y')}"
    if not items:
        body = "\n\nПока нет записей."
        return GratitudeScreen(text=header + body), 0, 1

    lines = [f"{i + 1}. {t}" for i, t in enumerate(items)]
    sliced = paginate_by_chars(lines, page, header=header + "\n\n")
    body = "\n\n" + "\n".join(sliced.items)
    return GratitudeScreen(text=header + body), sliced.page, sliced.total_pages


async def _load_gratitude_screen(tg_user_id: int, page: int) -> tuple[GratitudeScreen, int, int]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)
        items = await GratitudeService(session).get_gratitude_for_day(user.id, user.selected_date)
        await session.commit()

    return _render_gratitude(user.selected_date, [x.text for x in items], page)


@router.callback_query(F.data == "nav:gratitude")
async def open_gratitude(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    view, page, total_pages = await _load_gratitude_screen(call.from_user.id, page=0)
    show_clear = "Пока нет записей." not in view.text
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=gratitude_kb(page=page, total_pages=total_pages, show_clear=show_clear),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("gratitude:page:"))
async def gratitude_page(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    page_str = call.data.split(":", 2)[2]
    try:
        page = int(page_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    view, page, total_pages = await _load_gratitude_screen(call.from_user.id, page=page)
    show_clear = "Пока нет записей." not in view.text
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=gratitude_kb(page=page, total_pages=total_pages, show_clear=show_clear),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "gratitude:add")
async def add_gratitude_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.set_state(GratitudeStates.waiting_text)
    await safe_edit_message_text(call.message, "Введите благодарность одним сообщением:", reply_markup=gratitude_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "gratitude:back")
async def add_gratitude_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    view, page, total_pages = await _load_gratitude_screen(call.from_user.id, page=0)
    show_clear = "Пока нет записей." not in view.text
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=gratitude_kb(page=page, total_pages=total_pages, show_clear=show_clear),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "gratitude:clear")
async def clear_gratitude(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        await GratitudeService(session).clear_gratitude(user.id, user.selected_date)
        await session.commit()

    view, page, total_pages = _render_gratitude(user.selected_date, [], page=0)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=gratitude_kb(page=page, total_pages=total_pages, show_clear=False),
    )
    await safe_answer_callback(call, "Очищено")


@router.message(GratitudeStates.waiting_text)
async def add_gratitude_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    raw = message.text or ""
    await safe_delete_message(message)

    texts = [t.strip() for t in raw.splitlines()]
    texts = [t for t in texts if t]
    if not texts:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        service = GratitudeService(session)
        for text in texts:
            await service.add_gratitude(user.id, user.selected_date, text)
        items = await service.get_gratitude_for_day(user.id, user.selected_date)
        await session.commit()

    await state.clear()
    if user.dashboard_chat_id and user.dashboard_message_id:
        view, page, total_pages = _render_gratitude(user.selected_date, [x.text for x in items], page=0)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=gratitude_kb(page=page, total_pages=total_pages, show_clear=True),
        )
