import os

from aiogram import F
from aiogram.types import Message, CallbackQuery
from loguru import logger

from keyboards import main_keyboard
from system.system import router, accounts_db, ADMIN_IDS


@router.callback_query(F.data == "delete_session")
async def delete_session_start(callback: CallbackQuery):
    """
    Обработчик кнопки удаления сессии

    Запускает процесс удаления сессии и запрашивает у пользователя
    название файла сессии для удаления.

    Отображает инструкции по формату ввода.

    :param callback: Объект callback-запроса
    :return: None
    """
    await callback.message.answer(
        "🗑 Отправьте полное название сессии для удаления (например: session_name.session)"
    )
    await callback.answer()


@router.message(F.text)
async def process_delete_session(message: Message):
    """
    Обработчик удаления файла сессии

    Получает название сессии от пользователя, проверяет её наличие в базе данных,
    удаляет файл сессии из папки sessions и удаляет запись из базы данных.

    :param message: Объект сообщения с названием сессии
    :return: None
    """
    user_id = message.from_user.id
    session_name = message.text.strip()

    # Проверяем наличие сессий у пользователя
    if user_id not in accounts_db or not accounts_db[user_id]:
        await message.answer("У вас нет загруженных сессий")
        return

    # Ищем сессию по имени
    session_index = None
    session_info = None
    for i, acc in enumerate(accounts_db[user_id]):
        if acc["filename"] == session_name:
            session_index = i
            session_info = acc
            break

    if session_index is None:
        await message.answer(f"Сессия '{session_name}' не найдена. Проверьте правильность написания.")
        return

    # Удаляем файл сессии
    session_path = session_info["session"]
    try:
        if os.path.exists(session_path):
            os.remove(session_path)
            logger.info(f"Файл сессии удален: {session_path}")

        # Удаляем запись из базы данных
        accounts_db[user_id].pop(session_index)

        await message.answer(
            f"✅ Сессия '{session_name}' успешно удалена",
            reply_markup=main_keyboard(user_id in ADMIN_IDS)
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении сессии: {str(e)}")


def register_delete_session_handlers() -> None:
    """
    Регистрирует обработчики команд для удаления сессий

    Подключает обработчики команды delete_session к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(delete_session_start)
    router.message.register(process_delete_session)
