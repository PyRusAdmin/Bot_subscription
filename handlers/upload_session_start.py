# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.keyboards import main_keyboard
from states.states import UploadSession
from system.system import router, accounts_db, ADMIN_IDS, SESSIONS_DIR


# Загрузка сессии
@router.callback_query(F.data == "upload_session")
async def upload_session_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки загрузки сессии

    Запускает процесс загрузки сессии и переходит в состояние ожидания файла.
    Отображает инструкции пользователю по формату загружаемого файла.

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
async def process_session_upload(message: Message, state: FSMContext) -> None:
    """
    Обработчик загрузки файла сессии

    Принимает файл сессии в формате Telethon (.session),
    сохраняет его на диск в папку sessions и добавляет информацию в базу данных.
    Проверяет корректность формата файла перед сохранением.

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


def register_upload_session_start() -> None:
    """
    Регистрирует обработчики команд для загрузки сессий

    Подключает обработчики команды upload_session к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(upload_session_start)
