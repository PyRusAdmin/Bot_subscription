import shutil
from datetime import datetime
from pathlib import Path

from aiogram import F
from aiogram.types import CallbackQuery
from loguru import logger
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, UserDeactivatedError, UserDeactivatedBanError, \
    PhoneNumberBannedError

from database.database import Account
from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, API_ID, API_HASH

# Настройки путей
SESSIONS_DIR = Path("sessions")
DEAD_SESSIONS_DIR = Path("dead_sessions")
SESSIONS_DIR.mkdir(exist_ok=True)
DEAD_SESSIONS_DIR.mkdir(exist_ok=True)


@router.callback_query(F.data == "check_accounts")
async def check_accounts(callback: CallbackQuery) -> None:
    """
    Обработчик проверки аккаунтов

    Сканирует папку sessions, проверяет все найденные аккаунты,
    переименовывает файлы и сохраняет результаты в базу данных.

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id

    # Сканируем папку sessions
    session_files = scan_sessions_folder()

    if not session_files:
        await callback.message.answer(
            "❌ В папке sessions не найдено файлов сессий",
            reply_markup=main_keyboard(user_id in ADMIN_IDS)
        )
        await callback.answer()
        return

    # Отправляем сообщение о начале проверки
    msg = await callback.message.answer(
        f"🔄 Найдено файлов: {len(session_files)}\n"
        f"Начинаю проверку...\n"
    )

    # Запускаем проверку аккаунтов
    await check_user_accounts(user_id, session_files, msg)

    # Итоговая статистика
    # final_text = ("Проверка завершена!")
    await msg.edit_text(
        msg.text + "Проверка завершена!",
        reply_markup=main_keyboard(user_id in ADMIN_IDS)
    )
    await callback.answer()


def scan_sessions_folder() -> list:
    """
    Сканирует папку sessions на наличие .session файлов

    :return: Список путей к файлам сессий
    """
    session_files = []

    for file in SESSIONS_DIR.iterdir():
        if file.suffix == '.session' and file.is_file():
            session_files.append(file)
            logger.info(f"Найден файл сессии: {file.name}")

    logger.info(f"Всего найдено файлов сессий: {len(session_files)}")
    return session_files


async def check_user_accounts(user_id: int, session_files: list, msg) -> None:
    """
    Проверяет все аккаунты из списка файлов сессий

    Для каждого аккаунта:
    1. Подключается к Telegram
    2. Получает информацию об аккаунте
    3. Переименовывает файл в формате {account_id}_{phone}.session
    4. Сохраняет данные в базу Peewee
    5. Перемещает невалидные аккаунты в папку dead_sessions

    :param user_id: ID пользователя
    :param session_files: Список файлов сессий для проверки
    :param msg: Объект сообщения для отображения прогресса
    :return: Словарь со статистикой
    """
    logger.info(f"Проверка аккаунта... {session_files}")
    for session_path in session_files:

        logger.info(f"Проверка аккаунта... {session_path}")

        try:
            logger.info(f"[{len(session_files)}] Проверка: {session_path}")

            # Создаем клиент Telethon
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()

            # Получаем информацию об аккаунте
            me = await client.get_me()
            logger.info(f"Данные аккаунта {me}")

            # Проверяем авторизацию
            if not await client.is_user_authorized():
                logger.warning(f"Аккаунт {session_path} не авторизован")

                # Сохраняем в БД как неавторизованный
                await save_account_to_db(
                    user_id=user_id,
                    session_file=str(session_path),
                    original_filename=session_path,
                    status='unauthorized',
                    error_message='Требуется авторизация'
                )

                await update_message(msg, f"❌ {session_path} - не авторизован")
                await client.disconnect()
                continue

            # Получаем информацию об аккаунте
            me = await client.get_me()

            # Проверяем, что аккаунт не забанен
            if not me:
                logger.error(f"Не удалось получить информацию об аккаунте {session_path}")

                await move_to_dead(session_path)
                await update_message(msg, f"💀 {session_path} - мёртвый аккаунт")
                await client.disconnect()
                continue

            # Извлекаем данные
            account_id = me.id
            phone = me.phone or "unknown"
            username = me.username
            first_name = me.first_name
            last_name = me.last_name

            # Переименовываем файл в формат {account_id}_{phone}.session
            new_filename = f"{account_id}_{phone}.session"
            new_path = SESSIONS_DIR / new_filename

            # Если файл с таким именем уже существует, удаляем старый
            if new_path.exists() and new_path != session_path:
                logger.warning(f"Файл {new_filename} уже существует, удаляем дубликат")
                session_path.unlink()
            elif new_path != session_path:
                # Переименовываем файл и связанные файлы
                rename_session_files(session_path, new_path)
                logger.info(f"Переименован: {session_path} -> {new_filename}")

            # Сохраняем в БД
            await save_account_to_db(
                user_id=user_id,
                phone=phone,
                account_id=account_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                session_file=str(new_path),
                original_filename=session_path,
                status='active'
            )

            status_text = f"✅ {session_path} -> {new_filename}"
            if username:
                status_text += f" (@{username})"

            await update_message(msg, status_text)
            logger.info(f"Аккаунт {phone} (ID: {account_id}) успешно проверен")

            await client.disconnect()

        except (AuthKeyUnregisteredError, UserDeactivatedError,
                UserDeactivatedBanError, PhoneNumberBannedError) as e:
            # Аккаунт забанен или деактивирован
            logger.error(f"Аккаунт {session_path} мёртвый: {type(e).__name__}")

            await save_account_to_db(
                user_id=user_id,
                session_file=str(session_path),
                original_filename=session_path,
                status='dead',
                error_message=f'{type(e).__name__}: {str(e)}'
            )

            # Перемещаем в dead_sessions
            await move_to_dead(session_path)

            await update_message(msg, f"💀 {session_path} - мёртвый ({type(e).__name__})")

            # try:
            await client.disconnect()
            # except:
            #     pass

        except Exception as e:
            # Другие ошибки
            logger.error(f"Ошибка при проверке {session_path}: {str(e)}")

            await save_account_to_db(
                user_id=user_id,
                session_file=str(session_path),
                original_filename=session_path,
                status='error',
                error_message=str(e)[:500]
            )

            await update_message(msg, f"⚠️ {session_path} - ошибка: {str(e)[:30]}")

            # try:
            await client.disconnect()
            # except:
            #     pass


def rename_session_files(old_path: Path, new_path: Path) -> None:
    """
    Переименовывает файл сессии и связанные с ним файлы

    Telethon создает дополнительные файлы (.session-journal),
    которые тоже нужно переименовать.

    :param old_path: Старый путь к файлу
    :param new_path: Новый путь к файлу
    :return: None
    """
    # Переименовываем основной файл
    old_path.rename(new_path)

    # Переименовываем связанные файлы (если есть)
    for suffix in ['-journal', '-wal', '-shm']:
        old_related = old_path.parent / f"{old_path.name}{suffix}"
        if old_related.exists():
            new_related = new_path.parent / f"{new_path.name}{suffix}"
            old_related.rename(new_related)
            logger.debug(f"Переименован связанный файл: {old_related.name} -> {new_related.name}")


async def move_to_dead(session_path: Path) -> None:
    """
    Перемещает файл сессии в папку dead_sessions

    :param session_path: Путь к файлу сессии
    :return: None
    """
    try:
        dead_path = DEAD_SESSIONS_DIR / session_path.name

        # Если файл уже существует в dead_sessions, добавляем timestamp
        if dead_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dead_path = DEAD_SESSIONS_DIR / f"{session_path.stem}_{timestamp}{session_path.suffix}"

        shutil.move(str(session_path), str(dead_path))
        logger.info(f"Перемещён в dead_sessions: {session_path.name}")

        # Перемещаем связанные файлы
        for suffix in ['-journal', '-wal', '-shm']:
            related_file = session_path.parent / f"{session_path.name}{suffix}"
            if related_file.exists():
                dead_related = DEAD_SESSIONS_DIR / f"{dead_path.name}{suffix}"
                shutil.move(str(related_file), str(dead_related))

    except Exception as e:
        logger.error(f"Ошибка при перемещении файла в dead_sessions: {e}")


async def save_account_to_db(user_id: int, session_file: str,
                             original_filename: str, status: str,
                             phone: str = None, account_id: int = None,
                             username: str = None, first_name: str = None,
                             last_name: str = None, error_message: str = None) -> None:
    """
    Сохраняет или обновляет информацию об аккаунте в базе данных

    :param user_id: ID пользователя
    :param session_file: Путь к файлу сессии
    :param original_filename: Оригинальное имя файла
    :param status: Статус аккаунта
    :param phone: Номер телефона
    :param account_id: ID аккаунта в Telegram
    :param username: Username
    :param first_name: Имя
    :param last_name: Фамилия
    :param error_message: Сообщение об ошибке
    :return: None
    """
    try:
        # Проверяем, существует ли аккаунт
        account = Account.get_or_none(
            (Account.user_id == user_id) &
            (Account.session_file == session_file)
        )

        if account:
            # Обновляем существующий
            account.phone = phone or account.phone
            account.account_id = account_id or account.account_id
            account.username = username or account.username
            account.first_name = first_name or account.first_name
            account.last_name = last_name or account.last_name
            account.status = status
            account.error_message = error_message
            account.last_checked = datetime.now()
            account.save()
            logger.debug(f"Обновлён аккаунт в БД: {phone or original_filename}")
        else:
            # Создаём новый
            Account.create(
                user_id=user_id,
                phone=phone,
                account_id=account_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                session_file=session_file,
                original_filename=original_filename,
                status=status,
                error_message=error_message
            )
            logger.debug(f"Создан новый аккаунт в БД: {phone or original_filename}")

    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}")


async def update_message(msg, new_line: str) -> None:
    """
    Обновляет сообщение, добавляя новую строку

    :param msg: Объект сообщения
    :param new_line: Новая строка для добавления
    :return: None
    """
    try:
        current_text = msg.text or ""
        # Ограничиваем размер сообщения (Telegram limit ~4096 символов)
        lines = current_text.split('\n')
        if len(lines) > 50:  # Оставляем последние 50 строк
            lines = lines[:2] + lines[-48:]  # Заголовок + последние строки
            current_text = '\n'.join(lines)

        await msg.edit_text(current_text + f"\n{new_line}")
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")


def register_check_accounts_handlers() -> None:
    """
    Регистрирует обработчики команд для проверки аккаунтов

    Подключает обработчик команды /check_accounts к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(check_accounts)
