# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from keyboards.keyboards import main_keyboard
from states.states import DeleteSession
from system.system import router, ADMIN_IDS


@router.callback_query(F.data == "delete_session")
async def delete_session_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки удаления сессии

    Запускает процесс удаления сессии и запрашивает у пользователя
    название файла сессии для удаления.

    Отображает инструкции по формату ввода.

    :param callback: Объект callback-запроса
    :param state: Объект состояния FSM
    :return: None
    """
    await callback.message.answer(
        "🗑 Отправьте полное название сессии для удаления (например: session_name.session)"
    )

    await state.set_state(DeleteSession.waiting_for_session)
    await callback.answer()


@router.message(DeleteSession.waiting_for_session, F.text)
async def process_delete_session(message: Message, state: FSMContext):
    """
    Обработчик удаления файла сессии

    Получает название сессии от пользователя, проверяет её наличие в базе данных,
    удаляет файл сессии из папки sessions и удаляет запись из базы данных.

    :param message: Объект сообщения с названием сессии
    :param state: Объект состояния FSM
    :return: None
    """
    user_id = message.from_user.id
    session_name = message.text
    logger.info(f"Удаление сессии пользователем: {session_name}")

    try:
        file_path = f"sessions/{session_name}"
        os.remove(file_path)
        await message.answer(
            f"✅ Сессия '{session_name}' успешно удалена",
            reply_markup=main_keyboard(user_id in ADMIN_IDS)
        )
    except FileNotFoundError:
        await message.answer(f"Сессия '{session_name}' не найдена. Проверьте правильность написания.")

    await state.clear()


def register_delete_session_handlers() -> None:
    """
    Регистрирует обработчики команд для удаления сессий

    Подключает обработчики команды delete_session к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(delete_session_start)
    router.message.register(process_delete_session)
