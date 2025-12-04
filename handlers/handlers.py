# Конфигурация
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from system.system import ADMIN_IDS, router


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


def register_handlers_send_log() -> None:
    """
    Регистрирует обработчики команд для модуля логов

    Подключает обработчик команды /log к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.message.register(send_log)  # Отправляет логи бота по запросу администратора, прописанного в .env файле
