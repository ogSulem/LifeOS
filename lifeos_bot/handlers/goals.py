from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from aiogram.types import CallbackQuery, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.services.goals_service import GoalsService
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.goals_kb import goals_input_kb, goals_kb

from lifeos_bot.utils.pagination import paginate_by_count

_GOALS_PER_PAGE = 5

router = Router()


class GoalsStates(StatesGroup):
    waiting_title = State()


@dataclass(frozen=True)
class GoalsScreen:
    text: str


def _render_goals(day: date, items: list[tuple[str, bool]]) -> GoalsScreen:
    header = f"<b>🎯 Цели</b>\n<b>Дата:</b> {day.strftime('%d.%m.%Y')}"
    if not items:
        body = "\n\nПока нет целей."
    else:
        lines: list[str] = []
        for i, (title, done) in enumerate(items):
            mark = "✅" if done else "⬜️"
            lines.append(f"{i + 1}. {mark} {title}")
        body = "\n\n" + "\n".join(lines)
    return GoalsScreen(text=header + body)


async def _load_goals_screen(tg_user_id: int) -> tuple[GoalsScreen, int, int, date]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)
        goals = await GoalsService(session).get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    view = _render_goals(user.selected_date, [(g.title, g.is_done) for g in goals])
    return view, user.dashboard_chat_id or 0, user.dashboard_message_id or 0, user.selected_date


async def _load_goals_for_day(tg_user_id: int) -> tuple[date, list[tuple[int, str, bool]]]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        goals = await GoalsService(session).get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    return user.selected_date, [(int(g.id), str(g.title), bool(g.is_done)) for g in goals]


@router.callback_query(F.data == "nav:goals")
async def open_goals(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    selected_date, goals = await _load_goals_for_day(call.from_user.id)

    view = _render_goals(selected_date, [(title, done) for _, title, done in goals])
    all_kb_data = [(goal_id, done, i + 1) for i, (goal_id, title, done) in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=0, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("goals:page:"))
async def goals_page(call: CallbackQuery, state: FSMContext) -> None:
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

    selected_date, goals = await _load_goals_for_day(call.from_user.id)

    view = _render_goals(selected_date, [(title, done) for _, title, done in goals])
    all_kb_data = [(goal_id, done, i + 1) for i, (goal_id, title, done) in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=page, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "goals:add")
async def add_goal_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.message is None:
        await safe_answer_callback(call)
        return
    await state.set_state(GoalsStates.waiting_title)
    await safe_edit_message_text(call.message, "Введите цель одним сообщением:", reply_markup=goals_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("goals:toggle:"))
async def toggle_goal(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 3:
        await safe_answer_callback(call)
        return
    goal_id_str = parts[2]
    page = 0
    if len(parts) >= 4:
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
    try:
        goal_id = int(goal_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        service = GoalsService(session)
        ok = await service.toggle_goal_for_user(user.id, goal_id)
        if not ok:
            await safe_answer_callback(call)
            return
        goals = await service.get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    view = _render_goals(user.selected_date, [(g.title, g.is_done) for g in goals])
    all_kb_data = [(int(g.id), bool(g.is_done), i + 1) for i, g in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=page, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("goals:delete:"))
async def delete_goal(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 3:
        await safe_answer_callback(call)
        return
    goal_id_str = parts[2]
    page = 0
    if len(parts) >= 4:
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
    try:
        goal_id = int(goal_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        service = GoalsService(session)
        ok = await service.delete_goal_for_user(user.id, goal_id)
        if not ok:
            await safe_answer_callback(call)
            return
        goals = await service.get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    view = _render_goals(user.selected_date, [(g.title, g.is_done) for g in goals])
    all_kb_data = [(int(g.id), bool(g.is_done), i + 1) for i, g in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=page, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "goals:back")
async def goals_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    selected_date, goals = await _load_goals_for_day(call.from_user.id)

    view = _render_goals(selected_date, [(title, done) for _, title, done in goals])
    all_kb_data = [(goal_id, done, i + 1) for i, (goal_id, title, done) in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=0, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.message(GoalsStates.waiting_title)
async def add_goal_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    titles = [t.strip() for t in raw.splitlines()]
    titles = [t for t in titles if t]
    if not titles:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        service = GoalsService(session)
        for title in titles:
            await service.add_goal(user.id, user.selected_date, title)
        goals = await service.get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    await state.clear()
    if user.dashboard_chat_id and user.dashboard_message_id:
        view = _render_goals(user.selected_date, [(g.title, g.is_done) for g in goals])
        all_kb_data = [(int(g.id), bool(g.is_done), i + 1) for i, g in enumerate(goals)]
        sliced = paginate_by_count(all_kb_data, page=0, per_page=_GOALS_PER_PAGE)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
        )


@router.callback_query(F.data.startswith("goals:move:"))
async def move_goal_to_tomorrow(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 3:
        await safe_answer_callback(call)
        return
    goal_id_str = parts[2]
    page = 0
    if len(parts) >= 4:
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
    try:
        goal_id = int(goal_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        service = GoalsService(session)
        ok = await service.move_goal_to_day_for_user(user.id, goal_id, user.selected_date, days_delta=1)
        if not ok:
            await safe_answer_callback(call)
            return
        goals = await service.get_goals_for_day(user.id, user.selected_date)
        await session.commit()

    view = _render_goals(user.selected_date, [(g.title, g.is_done) for g in goals])
    all_kb_data = [(int(g.id), bool(g.is_done), i + 1) for i, g in enumerate(goals)]
    sliced = paginate_by_count(all_kb_data, page=page, per_page=_GOALS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=goals_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)
