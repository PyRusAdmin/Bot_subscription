# -*- coding: utf-8 -*-
from loguru import logger
from telethon.errors import (AuthKeyDuplicatedError)
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from system.system import API_ID, API_HASH


async def client_connect_string_session(session_name: str) -> TelegramClient | None:
    """
    Подключение к Telegram аккаунту через StringSession
    :param session_name: Имя аккаунта для подключения (файл .session)
    """
    # Создаем клиент, используя StringSession и вашу строку
    client = TelegramClient(StringSession(session_name), api_id=API_ID, api_hash=API_HASH,
                            system_version="4.16.30-vxCUSTOM")
    try:
        await client.connect()

        if not await client.is_user_authorized():
            logger.error("❌ Сессия недействительна или аккаунт не авторизован!")
            try:
                await client.disconnect()
            except ValueError:
                logger.error("❌ Сессия недействительна или аккаунт не авторизован!")
            return None  # Не возвращаем клиента

        me = await client.get_me()
        phone = me.phone or ""
        logger.info(f"🧾 Аккаунт: | ID: {me.id} | Phone: {phone}")
        # await app_logger.log_and_display(message=f"🧾 Аккаунт: | ID: {me.id} | Phone: {phone}")
        return client

    except AuthKeyDuplicatedError:
        logger.error(
            "❌ AuthKeyDuplicatedError: Повторный ввод ключа авторизации (на данный момент сеесия используется в другом месте)")
        await client.disconnect()
        return None  # Не возвращаем клиента


async def get_string_session(session_name) -> None:
    client = TelegramClient(session=session_name, api_id=API_ID, api_hash=API_HASH,
                            system_version="4.16.30-vxCUSTOM")
    await client.connect()
    logger.info(f"✨ STRING SESSION: {StringSession.save(client.session)}")
    session_string = StringSession.save(client.session)
    logger.info(f"✨ STRING SESSION: {session_string}")
    await client.disconnect()
    client = TelegramClient(StringSession(session_string), api_id=API_ID, api_hash=API_HASH,
                            system_version="4.16.30-vxCUSTOM")
    await client.connect()
    me = await client.get_me()
    # try:
    phone = me.phone or ""
    logger.info(f"🧾 Аккаунт: | ID: {me.id} | Phone: {phone}")
    await client.disconnect()