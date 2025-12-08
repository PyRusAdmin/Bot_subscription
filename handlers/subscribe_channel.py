import asyncio

from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, InviteHashExpiredError
from telethon.tl.functions.channels import JoinChannelRequest

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH, settings_db, SESSIONS_DIR


@router.callback_query(F.data == "subscribe_channel")
async def subscribe_channel(callback: CallbackQuery):
    """
    Обработчик подписки на канал

    Подписывает все аккаунты из папки sessions на целевой канал.
    Соблюдает заданный интервал между действиями.
    Отображает статистику выполнения операции.

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id

    # Читаем все .session файлы из папки (как в check_accounts)
    session_files = list(SESSIONS_DIR.glob("*.session"))

    if not session_files:
        await callback.message.answer("❌ Нет сессий в папке sessions/")
        await callback.answer()
        return

    if not settings_db.get("target_channel"):
        await callback.message.answer("❌ Администратор не установил целевой канал")
        await callback.answer()
        return

    target_channel = settings_db["target_channel"]
    interval = settings_db.get("interval", 5)

    msg = await callback.message.answer(
        f"🔄 Начинаю подписку на: {target_channel}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(session_files)}"
    )

    success = 0
    failed = 0

    for session_path in session_files:
        session_name = session_path.stem  # имя файла без .session

        client = TelegramClient(str(session_path), API_ID, API_HASH)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                raise Exception("Не авторизован")

            await client(JoinChannelRequest(target_channel))
            success += 1
            logger.success(f"Подписан: {session_name}")
            await msg.edit_text(
                msg.text + f"\n✅ {session_name} - подписан"
            )

        except FloodWaitError as e:
            logger.warning(f"FloodWait {session_name}: {e.seconds} сек")
            await msg.edit_text(
                msg.text + f"\n⏱ {session_name} - ожидание {e.seconds} сек"
            )
            await asyncio.sleep(e.seconds)
            failed += 1

        except (ChannelPrivateError, InviteHashExpiredError) as e:
            logger.warning(f"Канал недоступен {session_name}: {e}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - канал закрыт/ссылка недействительна"
            )
            failed += 1

        except Exception as e:
            failed += 1
            error_msg = str(e)[:50].replace("\n", " ")
            logger.error(f"Ошибка {session_name}: {error_msg}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - ошибка: {error_msg}"
            )

        finally:
            if client.is_connected():
                await client.disconnect()

        # Ждём интервал перед следующим аккаунтом
        await asyncio.sleep(interval)

    await msg.edit_text(
        msg.text + f"\n\n✅ Готово!\nУспешно: {success}\nОшибок: {failed}",
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await callback.answer()


def register_subscribe_channel():
    """
    Регистрирует обработчик подписки на канал.
    """
    router.callback_query.register(subscribe_channel)