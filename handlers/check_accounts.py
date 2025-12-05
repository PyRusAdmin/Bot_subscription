from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient

from keyboards import main_keyboard
from system.system import router, accounts_db, ADMIN_IDS, API_ID, API_HASH


@router.callback_query(F.data == "check_accounts")
async def check_accounts(callback: CallbackQuery) -> None:
    """
    Обработчик проверки аккаунтов, расположенных в папке sessions.

    Проверяет авторизацию каждого аккаунта пользователя.
    Обновляет статусы аккаунтов в базе данных.
    Отображает результаты проверки.
    Добавляет логирование состояния аккаунтов.

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id
    accounts = accounts_db.get(user_id, [])

    if not accounts:
        await callback.message.answer("У вас нет загруженных аккаунтов")
        await callback.answer()
        return

    msg = await callback.message.answer("🔄 Проверяю аккаунты...")

    for acc in accounts:
        try:
            session_name = acc["session"].replace('.session', '')
            client = TelegramClient(session_name, API_ID, API_HASH)

            await client.connect()

            if await client.is_user_authorized():
                me = await client.get_me()
                acc["status"] = "active"
                acc["phone"] = me.phone or "unknown"
                status = f"✅ {acc['filename']} - активен ({me.phone})"
                logger.info(f"Аккаунт {acc['filename']} активен")
            else:
                acc["status"] = "unauthorized"
                status = f"❌ {acc['filename']} - не авторизован"
                logger.warning(f"Аккаунт {acc['filename']} не авторизован")

            await client.disconnect()
            await msg.edit_text(msg.text + f"\n{status}")

        except Exception as e:
            acc["status"] = "error"
            await msg.edit_text(msg.text + f"\n❌ {acc['filename']} - ошибка: {str(e)[:50]}")

    await msg.edit_text(
        msg.text + "\n\n✅ Проверка завершена!",
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await callback.answer()


def register_check_accounts_handlers() -> None:
    """
    Регистрирует обработчики команд для проверки аккаунтов

    Подключает обработчик команды /check_accounts к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(check_accounts)
