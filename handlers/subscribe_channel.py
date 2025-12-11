# -*- coding: utf-8 -*-
import asyncio
import re
import sqlite3

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import (FloodWaitError, ChannelPrivateError, InviteHashExpiredError, UsernameNotOccupiedError,
                             UsernameInvalidError, FrozenMethodInvalidError)
from telethon.tl.functions.channels import JoinChannelRequest

from keyboards.keyboards import main_keyboard
from system.system import API_ID, API_HASH
from system.system import router, ADMIN_IDS, SESSIONS_DIR
from utilit.telegram_client import safe_disconnect
from utilit.utilit import load_settings


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
    """
    Обработчик подписки на канал

    Подписывает все аккаунты из папки sessions на целевой канал.
    Соблюдает заданный интервал между действиями.
    Отображает статистику выполнения операции.

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id

    # Загружаем настройки из JSON
    settings = load_settings()

    target_channel = settings.get("target_channel")
    if not target_channel:
        await callback.message.answer("❌ Администратор не установил целевой канал")
        await callback.answer()
        return

    # Извлекаем чистый идентификатор канала
    channel_identifier = extract_channel_identifier(target_channel)

    logger.info(f"Подписка на канал: {target_channel}")

    interval = settings.get("interval", 5)

    # Получаем список всех сессий
    session_files = list(SESSIONS_DIR.glob("*.session"))

    if not session_files:
        await callback.message.answer("❌ Не найдено ни одной сессии")
        await callback.answer()
        return

    # Создаем начальное сообщение
    msg = await callback.message.answer(
        f"🔄 Начинаю подписку на: {target_channel}\n"
        f"Идентификатор: {channel_identifier}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(session_files)}"
    )

    success = 0
    failed = 0
    db_errors = 0
    channel_not_found = False

    for session_file in session_files:
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
                await msg.edit_text(
                    msg.text + f"\n⚠️ {session_name} - не авторизован"
                )
                failed += 1
                await safe_disconnect(client, session_name)
                continue

            me = await client.get_me()
            logger.info(f"Обрабатывается аккаунт: {me.username or me.id}")

            # Попытка подписки
            await client(JoinChannelRequest(channel_identifier))
            success += 1
            logger.success(f"Подписан: {session_name}")
            await msg.edit_text(
                msg.text + f"\n✅ {session_name} - подписан"
            )

        except ValueError as e:
            error_msg = str(e).lower()
            if "already in the channel" in error_msg or "already in" in error_msg:
                logger.info(f"Аккаунт {session_name} уже подписан")
                await msg.edit_text(
                    msg.text + f"\n✔️ {session_name} - уже подписан"
                )
                success += 1
            elif "no user has" in error_msg or "username" in error_msg:
                logger.error(f"Канал не найден для {session_name}: {e}")
                await msg.edit_text(
                    msg.text + f"\n❌ {session_name} - канал не найден"
                )
                failed += 1
                channel_not_found = True
            else:
                logger.error(f"Ошибка для {session_name}: {e}")
                await msg.edit_text(
                    msg.text + f"\n❌ {session_name} - ошибка: {type(e).__name__}"
                )
                failed += 1

        except UsernameNotOccupiedError:
            logger.error(f"Канал не найден для {session_name}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - канал не найден"
            )
            failed += 1
            channel_not_found = True

        except UsernameInvalidError:
            logger.error(f"Неверный username канала для {session_name}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - неверный username канала"
            )
            failed += 1
            channel_not_found = True

        except FrozenMethodInvalidError:
            logger.error(f"Аккаунт {session_name} заморожен")
            await msg.edit_text(
                msg.text + f"\n🧊 {session_name} - заморожен"
            )
            failed += 1

        except FloodWaitError as e:
            logger.warning(f"FloodWait {session_name}: {e.seconds} сек")
            await msg.edit_text(
                msg.text + f"\n⏱ {session_name} - ожидание {e.seconds} сек"
            )
            await asyncio.sleep(e.seconds)
            # Повторная попытка после ожидания
            try:
                await client(JoinChannelRequest(channel_identifier))
                success += 1
                logger.success(f"Подписан после ожидания: {session_name}")
                await msg.edit_text(
                    msg.text + f"\n✅ {session_name} - подписан (после ожидания)"
                )
            except Exception as retry_error:
                logger.error(f"Ошибка после FloodWait для {session_name}: {retry_error}")
                await msg.edit_text(
                    msg.text + f"\n❌ {session_name} - ошибка после ожидания"
                )
                failed += 1

        except (ChannelPrivateError, InviteHashExpiredError) as e:
            logger.warning(f"Канал недоступен для {session_name}: {e}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - доступ запрещён"
            )
            failed += 1

        except sqlite3.DatabaseError as e:
            logger.error(f"Ошибка БД для {session_name}: {e}")
            await msg.edit_text(
                msg.text + f"\n💾 {session_name} - повреждена база данных"
            )
            failed += 1
            db_errors += 1
            # НЕ пытаемся отключиться в finally, так как БД повреждена
            if client and client.is_connected():
                try:
                    # Принудительно закрываем только сетевое соединение
                    if hasattr(client, '_sender') and client._sender:
                        await client._sender.disconnect()
                except:
                    pass
            client = None  # Обнуляем, чтобы finally не пытался отключиться

            # Ждём интервал перед следующим аккаунтом даже при ошибке БД
            if session_file != session_files[-1]:
                await asyncio.sleep(interval)
            continue

        except Exception as e:
            logger.exception(f"Неожиданная ошибка для {session_name}: {e}")
            await msg.edit_text(
                msg.text + f"\n❌ {session_name} - ошибка: {type(e).__name__}"
            )
            failed += 1

        finally:
            await safe_disconnect(client, session_name)

        # Ждём интервал перед следующим аккаунтом
        if session_file != session_files[-1]:  # Не ждать после последнего
            await asyncio.sleep(interval)

    # Формируем финальное сообщение
    final_text = (
        f"🔄 Подписка на: {target_channel}\n"
        f"Идентификатор: {channel_identifier}\n"
        f"Интервал: {interval} сек\n"
        f"Аккаунтов: {len(session_files)}\n\n"
        f"✅ Готово!\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}"
    )

    if db_errors > 0:
        final_text += f"\n💾 Повреждённых сессий: {db_errors}"

    if channel_not_found:
        final_text += (
            f"\n\n⚠️ ВНИМАНИЕ: Канал '{channel_identifier}' не найден!\n"
            f"Проверьте правильность username канала."
        )

    await msg.edit_text(
        final_text,
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )

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
