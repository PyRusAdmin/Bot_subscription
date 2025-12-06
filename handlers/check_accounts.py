from pathlib import Path

from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    UserDeactivatedError,
    PhoneNumberBannedError,
)

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH

SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


@router.callback_query(F.data == "check_accounts")
async def check_accounts(callback: CallbackQuery):
    """Проверка всех .session файлов"""
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Доступ запрещён", show_alert=True)

    session_files = list(SESSIONS_DIR.glob("*.session"))
    if not session_files:
        await callback.message.answer("Нет сессий в папке sessions/")
        return await callback.answer()

    status_msg = await callback.message.answer(
        f"Начинаю проверку {len(session_files)} сессий..."
    )

    for path in session_files:
        await validate_session(path)

    await status_msg.edit_text("Проверка завершена!", reply_markup=main_keyboard(True))
    # await callback.answer()


async def validate_session(path: Path):
    """Проверка одной .session"""
    logger.info(f"Проверка: {path.name}")
    client = TelegramClient(str(path), API_ID, API_HASH)

    try:
        await client.connect()

        me = await client.get_me()
        logger.info(me)

        if me is None:
            logger.warning(f"Аккаунт {path.name} не авторизован")

        # if not await client.is_user_authorized():
        # raise AuthKeyUnregisteredError()
        # logger.warning("Не авторизован")

        me = await client.get_me()
        phone = me.phone or "unknown"
        new_path = SESSIONS_DIR / f"{me.id}_{phone}.session"

        if path != new_path:
            new_path.unlink(missing_ok=True)
            path.rename(new_path)

        logger.success(f"Живой: +{phone} ({me.id})")

    except (AuthKeyUnregisteredError,
            UserDeactivatedError,
            PhoneNumberBannedError,
            SessionPasswordNeededError):
        logger.warning(f"Мёртвый: {path.name}")

    except Exception as e:
        logger.error(f"Ошибка {path.name}: {e}")

    finally:
        if client.is_connected():
            await client.disconnect()


def register_check_accounts_handlers():
    router.callback_query.register(check_accounts)
