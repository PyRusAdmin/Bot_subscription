from pathlib import Path

# Директория для хранения сессий Telethon
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

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
    """
    Обработчик проверки всех .session файлов
    
    Проверяет доступ к аккаунтам Telegram через Telethon клиент.
    Доступно только для администраторов.
    
    Args:
        callback (CallbackQuery): Объект callback-запроса от пользователя
    
    Returns:
        None
    """
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


async def validate_session(path: Path):
    """
    Проверяет валидность одной сессии Telegram.
    
    Подключается к аккаунту через Telethon и проверяет его состояние.
    Логирует результат проверки (живой/мёртвый/ошибка).
    
    Args:
        path (Path): Путь к файлу сессии .session
    
    Returns:
        None
    
    Raises:
        Exception: При ошибках подключения или других неожиданных проблемах
    """
    logger.info(f"Проверка: {path.name}")
    client = TelegramClient(str(path), API_ID, API_HASH)

    try:
        await client.connect()

        me = await client.get_me()
        logger.info(me)

        if me is None:
            logger.warning(f"Аккаунт {path.name} не авторизован")
        else:
            logger.info(me)
            phone = me.phone or "unknown"

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
    """
    Регистрирует обработчики команд проверки аккаунтов.
    
    Добавляет callback-обработчик для проверки сессий Telegram.
    """
    router.callback_query.register(check_accounts)
