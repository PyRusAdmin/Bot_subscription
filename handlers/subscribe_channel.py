# -*- coding: utf-8 -*-
import asyncio
import json
import re
from pathlib import Path

from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    InviteHashExpiredError,
    UsernameNotOccupiedError,
    UsernameInvalidError
)
from telethon.tl.functions.channels import JoinChannelRequest

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH, SESSIONS_DIR

# Путь к JSON файлу с настройками
SETTINGS_FILE = Path("data/settings.json")


def load_settings():
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        return {}


def save_settings(settings: dict):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"Настройки сохранены: {settings}")
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")


def extract_channel_identifier(channel_input: str) -> str:
    """
    Извлекает идентификатор канала из различных форматов ввода

    Поддерживаемые форматы:
    - https://t.me/channel_name
    - t.me/channel_name
    - @channel_name
    - channel_name
    - https://t.me/joinchat/XXXXX (invite links)
    - https://t.me/+XXXXX (new invite links)

    :param channel_input: Строка с каналом в любом формате
    :return: Очищенный идентификатор канала
    """
    channel_input = channel_input.strip()

    # Проверка на invite link (joinchat или +)
    if 'joinchat/' in channel_input or '/+' in channel_input:
        # Возвращаем всю ссылку для invite links
        return channel_input

    # Извлекаем username из URL
    # Паттерн: https://t.me/username или t.me/username
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', channel_input)
    if match:
        return match.group(1)

    # Если начинается с @, убираем его
    if channel_input.startswith('@'):
        return channel_input[1:]

    # Иначе возвращаем как есть
    return channel_input


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

    # Читаем все .session файлы из папки
    session_files = list(SESSIONS_DIR.glob("*.session"))

    if not session_files:
        await callback.message.answer("❌ Нет сессий в папке sessions/")
        await callback.answer()
        return

    # Загружаем настройки из JSON
    settings = load_settings()

    target_channel = settings.get("target_channel")
    if not target_channel:
        await callback.message.answer("❌ Администратор не установил целевой канал")
        await callback.answer()
        return

    # Извлекаем чистый идентификатор канала
    channel_identifier = extract_channel_identifier(target_channel)

    interval = settings.get("interval", 5)  # По умолчанию 5 секунд

    msg = await callback.message.answer(
        f"🔄 Начинаю подписку на: {target_channel}\n"
        f"Идентификатор: {channel_identifier}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(session_files)}"
    )

    success = 0
    failed = 0
    channel_not_found = False

    for session_path in session_files:
        session_name = session_path.stem  # имя файла без .session

        client = TelegramClient(str(session_path), API_ID, API_HASH)

        try:
            await client.connect()

            # if not await client.is_user_authorized():
            #     raise Exception("Не авторизован")

            # Используем очищенный идентификатор канала
            await client(JoinChannelRequest(channel_identifier))
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

        except (UsernameNotOccupiedError, UsernameInvalidError) as e:
            logger.error(f"Неверный username канала {session_name}: {e}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - канал не найден (неверный username)"
            )
            failed += 1
            channel_not_found = True
            # Прерываем цикл, т.к. канал не существует
            break

        # except Exception as e:
        #     failed += 1
        #     error_msg = str(e)[:50].replace("\n", " ")
        #     logger.error(f"Ошибка {session_name}: {error_msg}")
        #     await msg.edit_text(
        #         msg.text + f"\n❌ {session_name} - ошибка: {error_msg}"
        #     )

        finally:
            if client.is_connected():
                await client.disconnect()

        # Ждём интервал перед следующим аккаунтом
        await asyncio.sleep(interval)

    # Формируем финальное сообщение
    final_text = msg.text + f"\n\n✅ Готово!\nУспешно: {success}\nОшибок: {failed}"

    if channel_not_found:
        final_text += (
            f"\n\n⚠️ ВНИМАНИЕ: Канал '{channel_identifier}' не найден!\n"
            f"Проверьте правильность username канала.\n"
            f"Возможно, канал:\n"
            f"• Не существует\n"
            f"• Имеет другое имя\n"
            f"• Является приватным (используйте invite-ссылку)"
        )

    await msg.edit_text(
        final_text,
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await callback.answer()


def register_subscribe_channel() -> None:
    """
    Регистрирует обработчики команд для подписки на канал

    Подключает обработчик команды subscribe_channel к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(subscribe_channel)
