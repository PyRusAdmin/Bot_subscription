# -*- coding: utf-8 -*-
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery
from aiogram.utils.token import TokenValidationError
from loguru import logger

from handlers.check_accounts import register_check_accounts_handlers
from handlers.delete_session import register_delete_session_handlers
from handlers.handlers import register_core_handlers
from handlers.my_accounts import register_show_accounts
from handlers.set_channel import register_handlers_set_channel
from handlers.set_interval import set_interval_register_handler
from handlers.subscribe_channel import register_subscribe_channel
from handlers.upload_session_start import register_upload_session_start
from keyboards.keyboards import main_keyboard, admin_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH, settings_db, BOT_TOKEN

logger.add("log/log.log", rotation="10 MB")


# Админ настройки
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """
    Обработчик админ-панели

    Отображает текущие настройки бота
    Доступно только для пользователей из ADMIN_IDS.
    Предоставляет меню для изменения настроек

    :param callback: Объект callback-запроса
    :return: None
    """
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    text = (
        f"⚙️ Настройки администратора\n\n"
        f"Целевой канал: {settings_db['target_channel'] or 'не установлен'}\n"
        f"Интервал: {settings_db['interval']} сек"
    )

    await callback.message.answer(text, reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """
    Обработчик возврата в главное меню

    Отображает основное меню бота
    Завершает текущую операцию и возвращает пользователя в главное меню

    :param callback: Объект callback-запроса
    :return: None
    """
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_keyboard(callback.from_user.id in ADMIN_IDS)
    )
    await callback.answer()


# Запуск бота
async def main() -> None:
    """
    Основная функция запуска бота

    Инициализирует бота, диспетчер и регистрирует обработчики.
    Запускает polling для получения обновлений.
    Обрабатывает ошибки валидации токена.

    :return: None
    """
    # Проверка загрузки переменных окружения
    if not all([BOT_TOKEN, API_ID, API_HASH]):
        raise ValueError("❌ Не все переменные окружения загружены. Проверьте файл .env")

    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)

        register_upload_session_start()
        register_check_accounts_handlers()
        register_core_handlers()
        register_delete_session_handlers()

        register_subscribe_channel()

        register_handlers_set_channel()

        set_interval_register_handler()

        register_show_accounts()

        logger.success("🤖 Бот запущен...")
        await dp.start_polling(bot)
    except TokenValidationError:
        logger.error("❌ Неверный токен API")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
