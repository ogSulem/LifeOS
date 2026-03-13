from __future__ import annotations

from dataclasses import dataclass

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from aiogram.types import CallbackQuery, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.services.life_goals_service import LifeGoalsService
from lifeos_bot.keyboards.life_goals_kb import life_categories_kb, life_category_kb, life_input_kb

from lifeos_bot.utils.pagination import paginate_by_chars, paginate_by_count

_LIFE_CATS_PER_PAGE = 5
_LIFE_GOALS_PER_PAGE = 5

router = Router()


class LifeGoalsStates(StatesGroup):
    waiting_category_title = State()
    waiting_goal_title = State()


@dataclass(frozen=True)
class LifeCatsScreen:
    text: str


@dataclass(frozen=True)
class LifeGoalsScreen:
    text: str


def _render_categories(categories: list[str]) -> LifeCatsScreen:
    header = "<b>🧭 Жизненные цели</b>\n\n<b>Категории</b>"
    if not categories:
        body = "\n\nПока нет категорий. Добавьте первую."
    else:
        body = "\n\n" + "\n".join([f"{i + 1}. {t}" for i, t in enumerate(categories)])
    return LifeCatsScreen(text=header + body)


def _render_category(
    title: str,
    goals: list[tuple[str, bool]],
    page: int,
) -> tuple[LifeGoalsScreen, int, int, list[int]]:
    header = f"<b>🧭 {title}</b>\n\n<b>Цели</b>"
    if not goals:
        body = "\n\nПока нет целей."
        return LifeGoalsScreen(text=header + body), 0, 1, []

    sliced = paginate_by_count(goals, page=page, per_page=_LIFE_GOALS_PER_PAGE)

    lines: list[str] = []
    nums: list[int] = []
    start_num = sliced.page * _LIFE_GOALS_PER_PAGE
    for i, (t, done) in enumerate(sliced.items):
        num = start_num + i + 1
        nums.append(num)
        mark = "✅" if done else "⬜️"
        lines.append(f"{num}. {mark} {t}")

    # Keep rendering safe in Telegram limits
    text_slice = paginate_by_chars(lines, page=0, header=header + "\n\n")
    body = "\n\n" + "\n".join(text_slice.items)

    return LifeGoalsScreen(text=header + body), sliced.page, sliced.total_pages, nums


async def _load_categories(tg_user_id: int) -> tuple[LifeCatsScreen, list[tuple[int, str]]]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        cats = await LifeGoalsService(session).get_categories(user.id)
        await session.commit()

    return _render_categories([c.title for c in cats]), [(c.id, c.title) for c in cats]


async def _load_categories_page(tg_user_id: int, page: int) -> tuple[LifeCatsScreen, list[tuple[int, str]], int, int]:
    view, cats = await _load_categories(tg_user_id)
    sliced = paginate_by_count(cats, page=page, per_page=_LIFE_CATS_PER_PAGE)
    return view, sliced.items, sliced.page, sliced.total_pages


async def _load_category_screen(
    tg_user_id: int,
    category_id: int,
    page: int,
) -> tuple[LifeGoalsScreen, int, list[tuple[int, bool, int]], int, int] | None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        service = LifeGoalsService(session)
        cat = await service.get_category(category_id)
        if cat is None or cat.user_id != user.id:
            return None
        goals = await service.get_goals(category_id)
        await session.commit()

    view, page, total_pages, nums = _render_category(cat.title, [(g.title, g.is_done) for g in goals], page)
    sliced_goals = paginate_by_count(goals, page=page, per_page=_LIFE_GOALS_PER_PAGE)
    kb_items = [(int(g.id), bool(g.is_done), nums[i]) for i, g in enumerate(sliced_goals.items) if i < len(nums)]
    return view, cat.id, kb_items, page, total_pages


@router.callback_query(F.data == "nav:life_goals")
async def open_life_goals(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    view, cats, page, total_pages = await _load_categories_page(call.from_user.id, page=0)
    await safe_edit_message_text(call.message, view.text, reply_markup=life_categories_kb(cats, page=page, total_pages=total_pages))
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("life:cat_delete:"))
async def delete_category(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = (call.data or "").split(":")
    if len(parts) < 4:
        await safe_answer_callback(call)
        return
    try:
        category_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        ok = await LifeGoalsService(session).delete_category_for_user(user.id, category_id)
        if not ok:
            await session.commit()
            await safe_answer_callback(call)
            return
        await session.commit()

    view, cats, page, total_pages = await _load_categories_page(call.from_user.id, page=page)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_categories_kb(cats, page=page, total_pages=total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("life_cats:page:"))
async def life_categories_page(call: CallbackQuery, state: FSMContext) -> None:
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

    view, cats, page, total_pages = await _load_categories_page(call.from_user.id, page=page)
    await safe_edit_message_text(call.message, view.text, reply_markup=life_categories_kb(cats, page=page, total_pages=total_pages))
    await safe_answer_callback(call)


@router.callback_query(F.data == "life:cat_add")
async def add_category_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.set_state(LifeGoalsStates.waiting_category_title)
    await safe_edit_message_text(call.message, "Введите название категории одним сообщением (например: `Здоровье`):", reply_markup=life_input_kb("life:cats_back"))
    await safe_answer_callback(call)


@router.callback_query(F.data == "life:cats_back")
async def add_category_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    view, cats, page, total_pages = await _load_categories_page(call.from_user.id, page=0)
    await safe_edit_message_text(call.message, view.text, reply_markup=life_categories_kb(cats, page=page, total_pages=total_pages))
    await safe_answer_callback(call)


@router.message(LifeGoalsStates.waiting_category_title)
async def add_category_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    title = (message.text or "").strip()
    await safe_delete_message(message)
    if not title:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        await LifeGoalsService(session).add_category(user.id, title)
        await session.commit()

    await state.clear()
    view, cats = await _load_categories(message.from_user.id)
    if user.dashboard_chat_id and user.dashboard_message_id:
        sliced = paginate_by_count(cats, page=0, per_page=_LIFE_CATS_PER_PAGE)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=life_categories_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
        )


@router.callback_query(F.data.startswith("life:cat:"))
async def open_category(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()
    cat_id_str = call.data.split(":", 2)[2]
    try:
        cat_id = int(cat_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    loaded = await _load_category_screen(call.from_user.id, cat_id, page=0)
    if loaded is None:
        await safe_answer_callback(call, "Категория не найдена", show_alert=True)
        return

    view, category_id, kb_goals, page, total_pages = loaded
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
    )
    await state.update_data(active_category_id=category_id)
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("lifegoals:"))
async def life_goals_page(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 4:
        await safe_answer_callback(call)
        return
    try:
        category_id = int(parts[1])
        page = int(parts[3])
    except ValueError:
        await safe_answer_callback(call)
        return

    loaded = await _load_category_screen(call.from_user.id, category_id, page=page)
    if loaded is None:
        await safe_answer_callback(call)
        return
    view, category_id, kb_goals, page, total_pages = loaded
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
    )
    await state.update_data(active_category_id=category_id)
    await safe_answer_callback(call)


@router.callback_query(F.data == "life:back_to_cats")
async def back_to_categories(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    view, cats, page, total_pages = await _load_categories_page(call.from_user.id, page=0)
    await safe_edit_message_text(call.message, view.text, reply_markup=life_categories_kb(cats, page=page, total_pages=total_pages))
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("life:goal_add:"))
async def add_goal_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    try:
        category_id = int(call.data.split(":", 2)[2])
    except ValueError:
        await safe_answer_callback(call)
        return
    await state.update_data(active_category_id=category_id)
    await state.set_state(LifeGoalsStates.waiting_goal_title)
    await safe_edit_message_text(
        call.message,
        "Введите цели одним сообщением — по одной на строку.\n\nПример:\n`Выучить английский до B2`\n`Сделать 10 подтягиваний`\n`Наладить сон`",
        reply_markup=life_input_kb("life:goal_back"),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "life:goal_back")
async def add_goal_back(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    category_id = data.get("active_category_id")
    if not isinstance(category_id, int):
        await safe_answer_callback(call)
        return

    loaded = await _load_category_screen(call.from_user.id, category_id, page=0)
    if loaded is None:
        await safe_answer_callback(call)
        return
    view, category_id, kb_goals, page, total_pages = loaded
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
    )
    await safe_answer_callback(call)


@router.message(LifeGoalsStates.waiting_goal_title)
async def add_goal_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    titles = [x.strip() for x in raw.splitlines()]
    titles = [x for x in titles if x]
    if not titles:
        return

    data = await state.get_data()
    category_id = data.get("active_category_id")
    if not isinstance(category_id, int):
        await state.clear()
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        service = LifeGoalsService(session)
        cat = await service.get_category(category_id)
        if cat is None or cat.user_id != user.id:
            await state.clear()
            return
        for title in titles:
            await service.add_goal(category_id, title)
        await session.commit()

    await state.clear()
    loaded = await _load_category_screen(message.from_user.id, category_id, page=0)
    if loaded is None:
        await state.clear()
        return
    view, _, kb_goals, page, total_pages = loaded
    if user.dashboard_chat_id and user.dashboard_message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
        )


@router.callback_query(F.data.startswith("life:goal_toggle:"))
async def toggle_life_goal(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 5:
        await safe_answer_callback(call)
        return
    try:
        goal_id = int(parts[2])
        category_id = int(parts[3])
        page = int(parts[4])
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        service = LifeGoalsService(session)
        cat = await service.get_category(category_id)
        if cat is None or cat.user_id != user.id:
            await safe_answer_callback(call)
            return
        ok = await service.toggle_goal_for_user(user.id, category_id, goal_id)
        if not ok:
            await safe_answer_callback(call)
            return
        await session.commit()

    loaded = await _load_category_screen(call.from_user.id, category_id, page=page)
    if loaded is None:
        await safe_answer_callback(call)
        return
    view, category_id, kb_goals, page, total_pages = loaded
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("life:goal_delete:"))
async def delete_life_goal(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 5:
        await safe_answer_callback(call)
        return
    try:
        goal_id = int(parts[2])
        category_id = int(parts[3])
        page = int(parts[4])
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        service = LifeGoalsService(session)
        cat = await service.get_category(category_id)
        if cat is None or cat.user_id != user.id:
            await safe_answer_callback(call)
            return
        ok = await service.delete_goal_for_user(user.id, category_id, goal_id)
        if not ok:
            await safe_answer_callback(call)
            return
        await session.commit()

    loaded = await _load_category_screen(call.from_user.id, category_id, page=page)
    if loaded is None:
        await safe_answer_callback(call)
        return
    view, category_id, kb_goals, page, total_pages = loaded
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=life_category_kb(category_id, kb_goals, page=page, total_pages=total_pages),
    )
    await safe_answer_callback(call)
