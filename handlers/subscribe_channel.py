import asyncio

from aiogram import F
from aiogram.types import CallbackQuery
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

from keyboards.keyboards import main_keyboard
from system.system import router, accounts_db, ADMIN_IDS, API_ID, API_HASH, settings_db


# Подписка на канал
@router.callback_query(F.data == "subscribe_channel")
async def subscribe_channel(callback: CallbackQuery):
    """
    Обработчик подписки на канал

    Подписывает все активные аккаунты пользователя на целевой канал.
    Соблюдает заданный интервал между действиями.
    Отображает статистику выполнения операции.

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id
    accounts = [acc for acc in accounts_db.get(user_id, []) if acc["status"] == "active"]

    if not accounts:
        await callback.message.answer("❌ Нет активных аккаунтов для подписки")
        await callback.answer()
        return

    if not settings_db["target_channel"]:
        await callback.message.answer("❌ Администратор не установил целевой канал")
        await callback.answer()
        return

    target_channel = settings_db["target_channel"]
    interval = settings_db["interval"]

    msg = await callback.message.answer(
        f"🔄 Начинаю подписку на: {target_channel}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(accounts)}"
    )

    success = 0
    failed = 0

    for acc in accounts:
        try:
            session_name = acc["session"].replace('.session', '')
            client = TelegramClient(session_name, API_ID, API_HASH)

            await client.connect()

            if await client.is_user_authorized():
                await client(JoinChannelRequest(target_channel))
                success += 1
                await msg.edit_text(
                    msg.text + f"\n✅ {acc['filename']} - подписан"
                )

            await client.disconnect()
            await asyncio.sleep(interval)

        except FloodWaitError as e:
            await msg.edit_text(
                msg.text + f"\n⏱ {acc['filename']} - ожидание {e.seconds} сек"
            )
            await asyncio.sleep(e.seconds)
            failed += 1
        except Exception as e:
            failed += 1
            await msg.edit_text(
                msg.text + f"\n❌ {acc['filename']} - ошибка: {str(e)[:30]}"
            )

    await msg.edit_text(
        msg.text + f"\n\n✅ Готово!\nУспешно: {success}\nОшибок: {failed}",
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await callback.answer()


def register_subscribe_channel():
    router.callback_query.register(subscribe_channel)
