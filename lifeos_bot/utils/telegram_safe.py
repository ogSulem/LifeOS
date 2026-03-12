from __future__ import annotations

import logging
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message


def _is_not_modified(err: TelegramBadRequest) -> bool:
    return "message is not modified" in str(err).lower()


async def safe_edit_message_text(message: Message, text: str, **kwargs: Any) -> bool:
    try:
        await message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return False
        logging.exception("Failed to edit message text")
        return False
    except Exception:
        logging.exception("Failed to edit message text")
        return False


async def safe_bot_edit_message_text(bot: Any, chat_id: int, message_id: int, text: str, **kwargs: Any) -> bool:
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return False
        logging.exception("Failed to bot.edit_message_text")
        return False
    except Exception:
        logging.exception("Failed to bot.edit_message_text")
        return False


async def safe_delete_message(message: Message) -> bool:
    try:
        await message.delete()
        return True
    except Exception:
        logging.debug("Failed to delete message", exc_info=True)
        return False


async def safe_answer_callback(call: CallbackQuery, text: str | None = None, show_alert: bool = False) -> None:
    try:
        await call.answer(text or "", show_alert=show_alert)
    except Exception:
        logging.debug("Failed to answer callback", exc_info=True)


async def safe_send_message(bot: Any, chat_id: int, text: str, **kwargs: Any) -> Message | None:
    try:
        return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception:
        logging.exception("Failed to send message")
        return None
