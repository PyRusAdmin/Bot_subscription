# -*- coding: utf-8 -*-
import asyncio
import re
import sqlite3

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger

from telethon import TelegramClient
from telethon import functions, types
from telethon.errors import (AuthKeyUnregisteredError, ChannelPrivateError, ChannelsTooMuchError, FloodWaitError,
                             InviteHashExpiredError, InviteHashInvalidError, InviteRequestSentError,
                             SessionPasswordNeededError, UsernameInvalidError)
from telethon.errors import (UsernameNotOccupiedError,
                             FrozenMethodInvalidError)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from keyboards.keyboards import main_keyboard
from system.system import API_ID, API_HASH
from system.system import router, ADMIN_IDS, SESSIONS_DIR
from utilit.telegram_client import safe_disconnect
from utilit.utilit import load_settings


def extract_channel_id(link):
    """Сокращает ссылку с https://t.me/+yjqd0uZQETc4NGEy до yjqd0uZQETc4NGEy"""
    # Проверяем, начинается ли ссылка с 'https://t.me/'
    if link.startswith('https://t.me/'):
        return link[len('https://t.me/'):]
    # Если ссылка начинается просто с 't.me/', удалим 't.me/'
    elif link.startswith('t.me/'):
        return link[len('t.me/'):]
    # В остальных случаях возвращаем None
    else:
        return None


async def checking_links(client, link) -> None:
    """
    Проверка ссылок на подписку

    :param client: Клиент Telegram
    :param link: Ссылка на подписку
    """
    try:
        if link.startswith("https://t.me/+"):
            # Извлекаем хэш из ссылки на приглашение
            link_hash = link.split("+")[-1]
            try:
                result = await client(functions.messages.CheckChatInviteRequest(hash=link_hash))
                if isinstance(result, types.ChatInvite):
                    logger.info(
                        f"Ссылка валидна: {link}, Название группы: {result.title}, "
                        f"Количество участников: {result.participants_count}, "
                        f"Мега-группа: {'Да' if result.megagroup else 'Нет'}, Описание: {result.about or 'Нет описания'}")
                    try:
                        logger.info(f"Подписка на группу / канал по ссылке приглашению {link}")
                        try:
                            await client(ImportChatInviteRequest(link_hash))
                        except InviteHashInvalidError:
                            logger.info("Запрос на вступление уже отправлен. Ожидайте одобрения.")
                    except InviteHashExpiredError:
                        logger.info("Ссылка на приглашение устарела или недействительна.")
                        try:
                            await client(ImportChatInviteRequest(link_hash))
                            logger.info(f"Подписка на группу / канал по ссылке приглашению {link_hash}")
                        except InviteHashInvalidError:
                            logger.info("Запрос на вступление уже отправлен. Ожидайте одобрения.")
                elif isinstance(result, types.ChatInviteAlready):
                    logger.info(f"Вы уже состоите в группе: {link}, Название группы: {result.chat.title}")
            except FloodWaitError as e:
                logger.info(f"Слишком частые запросы. Подождите {e.seconds} секунд.", level="error")

        elif link.startswith("https://t.me/"):
            username = link.split("/")[-1]
            try:
                result = await client(functions.contacts.ResolveUsernameRequest(username=username))
                chat = result.chats[0] if result.chats else None
                if chat:
                    logger.info(
                        f"Публичная группа/канал: {link}, Название: {chat.title}, "
                        f"Количество участников: {chat.participants_count if hasattr(chat, 'participants_count') else 'Неизвестно'}, "
                        f"Мега-группа: {'Да' if getattr(chat, 'megagroup', False) else 'Нет'}")
                    logger.info(f"Подписка на группу / канал по ссылке {link}")
                    try:
                        await client(JoinChannelRequest(link))
                    except ChannelsTooMuchError:
                        logger.info("Превышено максимальное количество каналов для пользователя.")
                else:
                    logger.info(f"Не удалось найти публичный чат: {link}")
            except UsernameInvalidError:
                logger.error(f"Неверная ссылка: {link}. Переводим в формат https://t.me/...")
                parts = link.rstrip("/").split("/")
                link = parts[-2] if len(parts) >= 2 else None
                result = await client(functions.contacts.ResolveUsernameRequest(username=link))
                chat = result.chats[0] if result.chats else None
                if chat:
                    logger.info(
                        f"Публичная группа/канал: {link}, Название: {chat.title}, "
                        f"Количество участников: {chat.participants_count if hasattr(chat, 'participants_count') else 'Неизвестно'}, "
                        f"Мега-группа: {'Да' if getattr(chat, 'megagroup', False) else 'Нет'}")
                else:
                    logger.info(f"Не удалось найти публичный чат: {link}")
        else:
            try:
                result = await client(functions.messages.CheckChatInviteRequest(hash=link))
                if isinstance(result, types.ChatInvite):
                    logger.info(
                        f"Ссылка валидна: {link}, Название группы: {result.title}, "
                        f"Количество участников: {result.participants_count}, "
                        f"Мега-группа: {'Да' if result.megagroup else 'Нет'}, "
                        f"Описание: {result.about or 'Нет описания'}")
                    await client(JoinChannelRequest(link))
                elif isinstance(result, types.ChatInviteAlready):
                    logger.info(f"Вы уже состоите в группе: {link}, Название группы: {result.chat.title}")
            except FloodWaitError as e:
                logger.info(f"Слишком частые запросы. Подождите {e.seconds} секунд.", level="error")
            except InviteHashExpiredError:
                logger.info(f"Повторная проверка ссылки: {link}")
                try:
                    result = await client(functions.contacts.ResolveUsernameRequest(username=link))
                    chat = result.chats[0] if result.chats else None
                    if chat:
                        logger.info(
                            f"Публичная группа/канал: {link}, Название: {chat.title}, "
                            f"Количество участников: {chat.participants_count if hasattr(chat, 'participants_count') else 'Неизвестно'}, "
                            f"Мега-группа: {'Да' if getattr(chat, 'megagroup', False) else 'Нет'}")
                    else:
                        logger.info(f"Не удалось найти публичный чат: {link}")
                except UsernameInvalidError:
                    logger.error(f"Неверная ссылка: {link}. Переводим в формат https://t.me/...")
                    username = link.split("@")[-1]
                    logger.info(f"Ссылка после перевода: {username}")
                    result = await client(functions.contacts.ResolveUsernameRequest(username=username))
                    chat = result.chats[0] if result.chats else None
                    if chat:
                        logger.info(
                            f"Публичная группа/канал: {link}, Название: {chat.title}, "
                            f"Количество участников: {chat.participants_count if hasattr(chat, 'participants_count') else 'Неизвестно'}, "
                            f"Мега-группа: {'Да' if getattr(chat, 'megagroup', False) else 'Нет'}")
                    else:
                        logger.info(f"Не удалось найти публичный чат: {link}")

            except AuthKeyUnregisteredError:
                logger.warning(f"Мёртвый аккаунт")
                await asyncio.sleep(2)
            except SessionPasswordNeededError:
                logger.warning(f"Требуется пароль 2FA")
                await asyncio.sleep(2)

    except FloodWaitError as e:
        logger.info(f"Слишком частые запросы. Подождите {e.seconds} секунд.", level="error")
    except InviteRequestSentError:
        logger.info("Запрос на вступление уже отправлен. Ожидайте одобрения.")
    except AuthKeyUnregisteredError:
        logger.info("Сессия недействительна или аккаунт удалён.")
        await asyncio.sleep(2)
    except SessionPasswordNeededError:
        logger.info("Требуется двухфакторная аутентификация (2FA).")
        await asyncio.sleep(2)


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
        return channel_input

    # Специальная обработка для канала vkysno_i_prossto
    if 'vkysno_i_prossto' in channel_input:
        return 'vkysno_i_prossto'

    # Извлекаем username из URL
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', channel_input)
    if match:
        return match.group(1)

    # Если начинается с @, убираем его
    if channel_input.startswith('@'):
        return channel_input[1:]

    return channel_input


@router.callback_query(F.data == "subscribe_channel")
async def subscribe_channel(callback: CallbackQuery):
    user_id = callback.from_user.id

    settings = load_settings()
    target_channel = settings.get("target_channel")
    if not target_channel:
        await callback.message.answer("❌ Администратор не установил целевой канал")
        await callback.answer()
        return

    channel_input = target_channel.strip()
    logger.info(f"Подписка на канал: {channel_input}")

    interval = settings.get("interval", 5)
    session_files = list(SESSIONS_DIR.glob("*.session"))

    if not session_files:
        await callback.message.answer("❌ Не найдено ни одной сессии")
        await callback.answer()
        return

    # Определяем тип ссылки
    is_invite_link = False
    invite_hash = None
    username = None

    if '/joinchat/' in channel_input or '/+' in channel_input:
        is_invite_link = True
        # Извлекаем хеш: всё после последнего '/'
        invite_hash = channel_input.split('/')[-1]
        # Убираем возможный '+' в начале (для /+xxxx → xxxx)
        if invite_hash.startswith('+'):
            invite_hash = invite_hash[1:]
    else:
        # Публичный канал: извлекаем юзернейм
        username = extract_channel_identifier(channel_input)

    msg = await callback.message.answer(
        f"🔄 Начинаю подписку на: {channel_input}\n"
        f"Тип: {'Приглашение' if is_invite_link else 'Публичный канал'}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(session_files)}"
    )

    success = 0
    failed = 0
    db_errors = 0
    channel_not_found = False

    for i, session_file in enumerate(session_files):
        session_name = session_file.stem
        client = None

        try:
            client = TelegramClient(
                session=f"sessions/{session_name}",
                api_id=API_ID,
                api_hash=API_HASH,
                system_version="4.16.30-vxCUSTOM"
            )
            await client.connect()

            if not await client.is_user_authorized():
                logger.warning(f"Аккаунт {session_name} не авторизован")
                await msg.edit_text(msg.text + f"\n⚠️ {session_name} - не авторизован")
                failed += 1
                continue

            me = await client.get_me()
            logger.info(f"Обрабатывается аккаунт: {me.username or me.id}")

            if is_invite_link:
                # Попытка присоединиться по хешу приглашения
                try:
                    await client(ImportChatInviteRequest(invite_hash))
                    success += 1
                    logger.success(f"✅ Присоединился по приглашению: {session_name}")
                    await msg.edit_text(msg.text + f"\n✅ {session_name} - подписался (приглашение)")
                except InviteRequestSentError:
                    success += 1  # Считаем успешным, запрос отправлен
                    logger.info(f"📨 Запрос на вступление отправлен: {session_name}")
                    await msg.edit_text(msg.text + f"\n📨 {session_name} - запрос отправлен")
                except InviteHashExpiredError:
                    failed += 1
                    logger.error(f"💀 Приглашение устарело: {session_name}")
                    await msg.edit_text(msg.text + f"\n❌ {session_name} - приглашение недействительно")
                except InviteHashInvalidError:
                    failed += 1
                    logger.error(f"📛 Неверный хеш приглашения: {session_name}")
                    await msg.edit_text(msg.text + f"\n❌ {session_name} - неверная ссылка")
                except FloodWaitError as e:
                    logger.warning(f"⏱ FloodWait {e.seconds} сек для {session_name}")
                    await msg.edit_text(msg.text + f"\n⏱ {session_name} - ждём {e.seconds} сек")
                    await asyncio.sleep(e.seconds)
                    # Повтор после ожидания
                    try:
                        await client(ImportChatInviteRequest(invite_hash))
                        success += 1
                        await msg.edit_text(msg.text + f"\n✅ {session_name} - подписался (после FloodWait)")
                    except Exception as retry_e:
                        failed += 1
                        logger.error(f"❌ Ошибка после FloodWait: {retry_e}")
                        await msg.edit_text(msg.text + f"\n❌ {session_name} - ошибка после ожидания")

            else:
                # Публичный канал — используем JoinChannelRequest
                try:
                    await client(JoinChannelRequest(username))
                    success += 1
                    logger.success(f"✅ Подписан на публичный канал: {session_name}")
                    await msg.edit_text(msg.text + f"\n✅ {session_name} - подписался")
                except ValueError as e:
                    if "already in" in str(e).lower():
                        success += 1
                        await msg.edit_text(msg.text + f"\n✔️ {session_name} - уже подписан")
                    elif "no user has" in str(e).lower() or "username not found" in str(e).lower():
                        failed += 1
                        channel_not_found = True
                        await msg.edit_text(msg.text + f"\n❌ {session_name} - канал не найден")
                    else:
                        raise
                except UsernameNotOccupiedError:
                    failed += 1
                    channel_not_found = True
                    await msg.edit_text(msg.text + f"\n❌ {session_name} - username не занят")
                except UsernameInvalidError:
                    failed += 1
                    channel_not_found = True
                    await msg.edit_text(msg.text + f"\n❌ {session_name} - неверный username")
                except FloodWaitError as e:
                    await msg.edit_text(msg.text + f"\n⏱ {session_name} - FloodWait {e.seconds} сек")
                    await asyncio.sleep(e.seconds)
                    try:
                        await client(JoinChannelRequest(username))
                        success += 1
                        await msg.edit_text(msg.text + f"\n✅ {session_name} - подписался (после ожидания)")
                    except Exception as retry_e:
                        failed += 1
                        logger.error(f"❌ Ошибка после FloodWait: {retry_e}")
                        await msg.edit_text(msg.text + f"\n❌ {session_name} - ошибка после ожидания")
                except ChannelPrivateError:
                    failed += 1
                    await msg.edit_text(msg.text + f"\n🔒 {session_name} - канал приватный (требуется приглашение)")

        except sqlite3.DatabaseError as e:
            db_errors += 1
            failed += 1
            logger.error(f"💾 Ошибка БД: {session_name} — {e}")
            await msg.edit_text(msg.text + f"\n💾 {session_name} - повреждена сессия")
            if client and client.is_connected():
                try:
                    if hasattr(client, '_sender') and client._sender:
                        await client._sender.disconnect()
                except:
                    pass
            client = None
        except FrozenMethodInvalidError:
            failed += 1
            await msg.edit_text(msg.text + f"\n🧊 {session_name} - аккаунт заморожен")
        except Exception as e:
            failed += 1
            logger.exception(f"💥 Неожиданная ошибка для {session_name}: {e}")
            await msg.edit_text(msg.text + f"\n💥 {session_name} - критическая ошибка")

        finally:
            await safe_disconnect(client, session_name)

        # Интервал между аккаунтами (кроме последнего)
        if i < len(session_files) - 1:
            await asyncio.sleep(interval)

    # Финальное сообщение
    final_text = (
        f"✅ Подписка завершена!\n\n"
        f"Цель: {channel_input}\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}"
    )
    if db_errors:
        final_text += f"\n💾 Повреждённых сессий: {db_errors}"
    if channel_not_found and not is_invite_link:
        final_text += f"\n\n⚠️ Канал '{username}' не найден! Проверьте username."

    await msg.edit_text(final_text, reply_markup=main_keyboard(user_id in ADMIN_IDS))
    try:
        await callback.answer()
    except TelegramBadRequest:
        logger.error("Callback устарел")


def register_subscribe_channel() -> None:
    """
    Регистрирует обработчики команд для подписки на канал

    Подключает обработчик команды subscribe_channel к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(subscribe_channel)
