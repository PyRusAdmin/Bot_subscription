# -*- coding: utf-8 -*-
import csv
from pathlib import Path

from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, SESSIONS_DIR
from utilit.telegram_client import validate_session, get_string_session
from utilit.utilit import writes_data_to_csv_file


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

    status_msg = await callback.message.answer("Начинаю проверку аккаунтов. Это может занять некоторое время...")

    # Собираем данные для записи в CSV
    csv_data = [['Название аккаунта', 'Статус', 'Номер телефона']]

    for path in list(SESSIONS_DIR.glob("*.session")):
        await validate_session(path, csv_data)

    writes_data_to_csv_file(csv_data)  # Записываем в accounts.csv

    # Сначала переименовываем все авторизованные сессии по номеру телефона
    for row in csv_data[1:]:  # Пропускаем заголовок
        account_name = row[0]
        phone_number = row[2]

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
            new_path = SESSIONS_DIR / "bad" / f"{phone_number}.session"
            if new_path.exists():
                new_path.unlink()  # удаляем существующий файл
            session_file.rename(new_path)
            logger.info(f"Перемещён файл сессии в bad: {session_file} -> {new_path}")
        elif status == 'Не авторизован' or status == 'Заблокирован' or status == 'Требуется пароль 2FA':
            # Удаляем другие проблемные сессии
            session_file.unlink()
            logger.info(f"Удалён файл сессии: {session_file}")

    await save_sessions_to_csv()  # Сохраняем все сессии в accounts_string.csv
    delete_session_files(".")  # Удаляем все .session файлы

    await status_msg.edit_text(
        text="Проверка завершена! Результаты сохранены в accounts.csv и неавторизованные сессии удалены",
        reply_markup=main_keyboard(True))


def delete_session_files(directory: str = ".") -> int:
    """Удаляет все .session файлы"""
    deleted_count = 0
    path = Path(directory)

    for session_file in path.glob("*.session"):
        try:
            session_file.unlink()
            logger.info(f"🗑️ Удален: {session_file}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении {session_file}: {e}")

    logger.info(f"✅ Удалено файлов: {deleted_count}")
    # return deleted_count


async def save_sessions_to_csv():
    # Путь к директории с сессиями
    SESSIONS_DIR = Path("sessions")

    # Собираем данные для записи в CSV
    csv_data = [['Название аккаунта', 'Session String']]

    # Проходим по всем .session файлам в папке sessions
    for session_file in SESSIONS_DIR.glob("*.session"):
        session_name = session_file.stem  # Имя файла без расширения
        session_string = await get_string_session(session_name=session_name)
        csv_data.append([session_name, session_string])

    # Записываем в CSV файл
    with open('accounts_string.csv', mode='w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(csv_data)

    print("✅ Все сессии сохранены в accounts_string.csv")


def register_check_accounts_handlers():
    """
    Регистрирует обработчики команд проверки аккаунтов.
    
    Добавляет callback-обработчик для проверки сессий Telegram.
    """
    router.callback_query.register(check_accounts)
