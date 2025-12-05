# Конфигурация
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.types import Message

from keyboards.keyboards import main_keyboard
from system.system import router, accounts_db, ADMIN_IDS


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start

    Создает основное меню бота и приветствует пользователя.
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


# Команды
@router.message(Command("log"))
async def send_log(message: Message) -> None:
    """
    Обработчик команды /log для получения логов бота

    Позволяет администраторам получить текущий файл логов бота.
    Проверяет права доступа по ID пользователя.
    Отправляет логи как документ с подписью.

    :param message: Объект сообщения от пользователя
    :return: None
    """
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return

    log_file = FSInputFile("log/log.log")
    try:
        await message.answer_document(log_file, caption="📄 Логи бота")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить логи: {str(e)}")


def register_core_handlers() -> None:
    """
    Регистрирует основные обработчики команд бота

    Подключает обработчики команд /start и /log к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.message.register(send_log)  # Отправляет логи бота по запросу администратора, прописанного в .env файле
    router.message.register(cmd_start)  # Отправляет основное меню бота по команде /start
