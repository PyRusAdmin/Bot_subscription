
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.token import TokenValidationError
from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

from handlers.check_accounts import register_check_accounts_handlers
from handlers.handlers import register_core_handlers
from keyboards import main_keyboard, admin_keyboard
from states.states import UploadSession, AdminSettings
from system.system import router, accounts_db, ADMIN_IDS, SESSIONS_DIR, API_ID, API_HASH, settings_db, BOT_TOKEN






# Загрузка сессии
@router.callback_query(F.data == "upload_session")
async def upload_session_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки загрузки сессии

    Запускает процесс загрузки сессии и переходит в состояние ожидания файла
    Отображает инструкции пользователю

    :param callback: Объект callback-запроса
    :param state: Контекст состояния FSM
    :return: None
    """
    await callback.message.answer(
        "📤 Отправьте файл сессии (.session)\n\n"
        "Поддерживаются форматы: Telethon"
    )
    await state.set_state(UploadSession.waiting_for_session)
    await callback.answer()


@router.message(UploadSession.waiting_for_session, F.document)
async def process_session_upload(message: Message, state: FSMContext):
    """
    Обработчик загрузки файла сессии

    Принимает файл сессии, сохраняет его на диск и добавляет в базу данных.
    Поддерживает только файлы с расширением .session

    :param message: Объект сообщения с документом
    :param state: Контекст состояния FSM
    :return: None
    """
    user_id = message.from_user.id
    document = message.document

    if not document.file_name.endswith('.session'):
        await message.answer("❌ Пожалуйста, отправьте файл с расширением .session")
        return

    # Скачиваем файл
    file = await message.bot.download(document)
    session_path = os.path.join(SESSIONS_DIR, f"{user_id}_{document.file_name}")

    with open(session_path, 'wb') as f:
        f.write(file.read())

    # Сохраняем в базу
    accounts_db[user_id].append({
        "session": session_path,
        "filename": document.file_name,
        "status": "not_checked",
        "phone": "unknown"
    })

    await message.answer(
        f"✅ Сессия загружена: {document.file_name}\n\n"
        f"Используйте 'Проверить аккаунты' для проверки",
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await state.clear()


def register_upload_session_start():
    router.callback_query.register(upload_session_start)