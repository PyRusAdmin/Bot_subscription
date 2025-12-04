import asyncio
import os

# Конфигурация
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.token import TokenValidationError
from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

from handlers.handlers import register_handlers_send_log
# Клавиатуры
from keyboards import main_keyboard, admin_keyboard
from system.system import router, accounts_db, ADMIN_IDS, SESSIONS_DIR, API_ID, API_HASH, settings_db, BOT_TOKEN

logger.add("log/log.log", rotation="10 MB")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start

    Создает основное меню бота и приветствует пользователя,
    Регистрирует пользователя в базе данных, если его нет

    :param message: Объект сообщения от пользователя
    :return: None
    """
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
        "Поддерживаются форматы: Telethon, Pyrogram"
    )
    await state.set_state(UploadSession.waiting_for_session)
    await callback.answer()


@router.message(UploadSession.waiting_for_session, F.document)
async def process_session_upload(message: Message, state: FSMContext):
    """
    Обработчик загрузки файла сессии

    Принимает файл сессии, сохраняет его на диск и добавляет в базу данных
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


# Просмотр аккаунтов
@router.callback_query(F.data == "my_accounts")
async def show_accounts(callback: CallbackQuery):
    """
    Обработчик кнопки просмотра аккаунтов

    Отображает список всех загруженных пользователем аккаунтов
    Показывает статус, телефон и имя файла для каждого аккаунта

    :param callback: Объект callback-запроса
    :return: None
    """
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
    """
    Обработчик проверки аккаунтов

    Проверяет авторизацию каждого аккаунта пользователя
    Обновляет статусы аккаунтов в базе данных
    Отображает результаты проверки

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
    """
    Обработчик подписки на канал

    Подписывает все активные аккаунты пользователя на целевой канал
    Соблюдает заданный интервал между действиями
    Отображает статистику выполнения операции

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


# Админ настройки
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """
    Обработчик админ-панели

    Отображает текущие настройки бота
    Доступно только для пользователей из ADMIN_IDS
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


@router.callback_query(F.data == "set_channel")
async def set_channel_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик установки целевого канала

    Запускает процесс установки канала для подписки
    Переходит в состояние ожидания ввода канала
    Доступно только для администраторов

    :param callback: Объект callback-запроса
    :param state: Контекст состояния FSM
    :return: None
    """
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
    """
    Обработчик установки канала

    Сохраняет введенный канал в настройки
    Подтверждает успешную установку

    :param message: Объект сообщения с названием канала
    :param state: Контекст состояния FSM
    :return: None
    """
    settings_db["target_channel"] = message.text.strip()
    await message.answer(
        f"✅ Канал установлен: {settings_db['target_channel']}",
        reply_markup=admin_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик установки интервала

    Запускает процесс установки интервала между действиями
    Переходит в состояние ожидания ввода интервала
    Доступно только для администраторов

    :param callback: Объект callback-запроса
    :param state: Контекст состояния FSM
    :return: None
    """
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.answer("Отправьте интервал в секундах (например: 60)")
    await state.set_state(AdminSettings.waiting_for_interval)
    await callback.answer()


@router.message(AdminSettings.waiting_for_interval)
async def set_interval_process(message: Message, state: FSMContext):
    """
    Обработчик установки интервала

    Сохраняет введенный интервал в настройки
    Проверяет корректность значения (целое число > 0)
    Подтверждает успешную установку

    :param message: Объект сообщения с интервалом в секундах
    :param state: Контекст состояния FSM
    :return: None
    """
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
async def main():
    """
    Основная функция запуска бота

    Инициализирует бота, диспетчер и регистрирует обработчики
    Запускает polling для получения обновлений
    Обрабатывает ошибки валидации токена
    """
    # Проверка загрузки переменных окружения
    if not all([BOT_TOKEN, API_ID, API_HASH]):
        raise ValueError("❌ Не все переменные окружения загружены. Проверьте файл .env")

    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)

        register_handlers_send_log()

        logger.success("🤖 Бот запущен...")
        await dp.start_polling(bot)
    except TokenValidationError:
        logger.error("❌ Неверный токен API")


if __name__ == "__main__":
    asyncio.run(main())
