import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest
import json

# Конфигурация
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Токен вашего бота
API_ID = 12345  # Ваш API ID от my.telegram.org
API_HASH = "your_api_hash"  # Ваш API Hash
ADMIN_IDS = [123456789]  # ID администраторов

# Директории
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Хранилище данных
accounts_db = {}  # {user_id: [{"session": "path", "phone": "phone", "status": "active"}]}
settings_db = {"target_channel": None, "interval": 60}  # Настройки подписки

# FSM States
class UploadSession(StatesGroup):
    waiting_for_session = State()

class AdminSettings(StatesGroup):
    waiting_for_channel = State()
    waiting_for_interval = State()

# Роутер
router = Router()

# Клавиатуры
def main_keyboard(is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="📤 Загрузить сессию", callback_data="upload_session")],
        [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="my_accounts")],
        [InlineKeyboardButton(text="✅ Проверить аккаунты", callback_data="check_accounts")],
        [InlineKeyboardButton(text="➕ Подписаться на канал", callback_data="subscribe_channel")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Настройки (Админ)", callback_data="admin_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Установить канал", callback_data="set_channel")],
        [InlineKeyboardButton(text="⏱ Установить интервал", callback_data="set_interval")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# Команды
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if user_id not in accounts_db:
        accounts_db[user_id] = []

    is_admin = user_id in ADMIN_IDS
    await message.answer(
        f"👋 Добро пожаловать!\n\n"
        f"Этот бот помогает управлять Telegram аккаунтами.\n\n"
        f"Выберите действие:",
        reply_markup=main_keyboard(is_admin)
    )

# Загрузка сессии
@router.callback_query(F.data == "upload_session")
async def upload_session_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📤 Отправьте файл сессии (.session)\n\n"
        "Поддерживаются форматы: Telethon, Pyrogram"
    )
    await state.set_state(UploadSession.waiting_for_session)
    await callback.answer()

@router.message(UploadSession.waiting_for_session, F.document)
async def process_session_upload(message: Message, state: FSMContext):
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

# Просмотр аккаунтов
@router.callback_query(F.data == "my_accounts")
async def show_accounts(callback: CallbackQuery):
    user_id = callback.from_user.id
    accounts = accounts_db.get(user_id, [])

    if not accounts:
        await callback.message.answer("У вас нет загруженных аккаунтов")
        await callback.answer()
        return

    text = "📋 Ваши аккаунты:\n\n"
    for idx, acc in enumerate(accounts, 1):
        status_emoji = "✅" if acc["status"] == "active" else "❓" if acc["status"] == "not_checked" else "❌"
        text += f"{idx}. {status_emoji} {acc['filename']}\n"
        text += f"   Телефон: {acc['phone']}\n"
        text += f"   Статус: {acc['status']}\n\n"

    await callback.message.answer(text, reply_markup=main_keyboard(user_id in ADMIN_IDS))
    await callback.answer()

# Проверка аккаунтов
@router.callback_query(F.data == "check_accounts")
async def check_accounts(callback: CallbackQuery):
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
            else:
                acc["status"] = "unauthorized"
                status = f"❌ {acc['filename']} - не авторизован"

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

# Подписка на канал
@router.callback_query(F.data == "subscribe_channel")
async def subscribe_channel(callback: CallbackQuery):
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

# Админ настройки
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
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

@router.callback_query(F.data == "set_channel")
async def set_channel_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.answer(
        "Отправьте username или ссылку на канал\n"
        "Например: @channel или https://t.me/channel"
    )
    await state.set_state(AdminSettings.waiting_for_channel)
    await callback.answer()

@router.message(AdminSettings.waiting_for_channel)
async def set_channel_process(message: Message, state: FSMContext):
    settings_db["target_channel"] = message.text.strip()
    await message.answer(
        f"✅ Канал установлен: {settings_db['target_channel']}",
        reply_markup=admin_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.answer("Отправьте интервал в секундах (например: 60)")
    await state.set_state(AdminSettings.waiting_for_interval)
    await callback.answer()

@router.message(AdminSettings.waiting_for_interval)
async def set_interval_process(message: Message, state: FSMContext):
    try:
        interval = int(message.text)
        if interval < 1:
            raise ValueError
        settings_db["interval"] = interval
        await message.answer(
            f"✅ Интервал установлен: {interval} сек",
            reply_markup=admin_keyboard()
        )
        await state.clear()
    except:
        await message.answer("❌ Укажите корректное число секунд")

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_keyboard(callback.from_user.id in ADMIN_IDS)
    )
    await callback.answer()

# Запуск бота
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())