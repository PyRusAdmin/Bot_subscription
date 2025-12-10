# -*- coding: utf-8 -*-
from pathlib import Path
import csv
from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import (SessionPasswordNeededError, AuthKeyUnregisteredError, UserDeactivatedError,
                             PhoneNumberBannedError)

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH, SESSIONS_DIR


@router.callback_query(F.data == "check_accounts")
async def check_accounts(callback: CallbackQuery):
    """
    Обработчик проверки всех .session файлов
    
    Проверяет доступ к аккаунтам Telegram через Telethon клиент.
    Доступно только для администраторов.
    
    :param callback:Объект callback-запроса от пользователя
    :return: None
    """
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Доступ запрещён", show_alert=True)

    session_files = list(SESSIONS_DIR.glob("*.session"))
    if not session_files:
        await callback.message.answer("Нет сессий в папке sessions/")
        return await callback.answer()

    status_msg = await callback.message.answer(
        f"Начинаю проверку {len(session_files)} сессий..."
    )

    # Собираем данные для записи в CSV
    csv_data = [['Название аккаунта', 'Статус', 'Номер телефона']]

    for path in session_files:
        await validate_session(path, csv_data)

    # Записываем данные в accounts.csv
    with open('accounts.csv', mode='w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(csv_data)

    # Создаем папку для проблемных сессий
    bad_sessions_dir = SESSIONS_DIR / "bad"
    bad_sessions_dir.mkdir(exist_ok=True)
    
    # Сначала переименовываем все авторизованные сессии по номеру телефона
    for row in csv_data[1:]:  # Пропускаем заголовок
        account_name = row[0]
        phone_number = row[2]
        status = row[1]
        
        # Пропускаем строки без номера телефона
        if not phone_number:
            continue
            
        session_file = SESSIONS_DIR / f"{account_name}.session"
        new_session_file = SESSIONS_DIR / f"{phone_number}.session"
        
        if session_file.exists() and session_file != new_session_file:
            if new_session_file.exists():
                logger.warning(f"Файл сессии {new_session_file} уже существует, удаляю старый файл {session_file}")
                session_file.unlink()
            else:
                session_file.rename(new_session_file)
                logger.info(f"Переименован файл сессии: {session_file} -> {new_session_file}")

    # Теперь обрабатываем проблемные сессии
    for row in csv_data[1:]:  # Пропускаем заголовок
        account_name = row[0]
        phone_number = row[2] if row[2] else account_name
        status = row[1]
        session_file = SESSIONS_DIR / f"{phone_number}.session"  # используем новое имя
        
        if not session_file.exists():
            continue
            
        if "The authorization key (session file) was used under two different IP addresses simultaneously" in status:
            # Перемещаем в папку bad
            new_path = bad_sessions_dir / f"{phone_number}.session"
            if new_path.exists():
                new_path.unlink()  # удаляем существующий файл
            session_file.rename(new_path)
            logger.info(f"Перемещён файл сессии в bad: {session_file} -> {new_path}")
        elif status == 'Не авторизован' or status == 'Заблокирован' or status == 'Требуется пароль 2FA':
            # Удаляем другие проблемные сессии
            session_file.unlink()
            logger.info(f"Удалён файл сессии: {session_file}")

    await status_msg.edit_text(
        "Проверка завершена! Результаты сохранены в accounts.csv и неавторизованные сессии удалены",
        reply_markup=main_keyboard(True))


async def validate_session(path: Path, csv_data: list):
    """
    Проверяет валидность одной сессии Telegram.
    
    Подключается к аккаунту через Telethon и проверяет его состояние.
    Логирует результат проверки (живой/мёртвый/ошибка).
    Добавляет результат в csv_data.
    
    :param path: Путь к файлу сессии .session
    :param csv_data: Список для добавления данных о статусе аккаунта
    :return: None
    """
    logger.info(f"Проверка: {path.name}")
    client = TelegramClient(str(path), API_ID, API_HASH)

    try:
        await client.connect()

        me = await client.get_me()
        logger.info(me)

        if me is None:
            logger.warning(f"Аккаунт {path.name} не авторизован")
            csv_data.append([path.stem, 'Не авторизован', ''])
        else:
            logger.success(f"Живой: +{me.phone or 'unknown'} ({me.id})")
            csv_data.append([path.stem, 'Авторизован', me.phone])

    except (AuthKeyUnregisteredError,
            UserDeactivatedError,
            PhoneNumberBannedError):
        logger.warning(f"Мёртвый: {path.name}")
        csv_data.append([path.stem, 'Заблокирован', ''])

    except SessionPasswordNeededError:
        logger.warning(f"Требуется пароль 2FA: {path.name}")
        csv_data.append([path.stem, 'Требуется пароль 2FA', ''])

    except Exception as e:
        logger.error(f"Ошибка {path.name}: {e}")
        csv_data.append([path.stem, f'Ошибка: {str(e)}', ''])

    finally:
        if client.is_connected():
            await client.disconnect()


def register_check_accounts_handlers():
    """
    Регистрирует обработчики команд проверки аккаунтов.
    
    Добавляет callback-обработчик для проверки сессий Telegram.
    """
    router.callback_query.register(check_accounts)
