import json
from pathlib import Path

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from keyboards.keyboards import admin_keyboard
from states.states import AdminSettings
from system.system import router, ADMIN_IDS

# Путь к JSON файлу с настройками
SETTINGS_FILE = Path("data/settings.json")


def load_settings():
    """
    Загружает настройки из JSON файла
    
    :return: Словарь с настройками или пустой словарь
    """
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
    """
    Сохраняет настройки в JSON файл
    
    :param settings: Словарь с настройками
    :return: None
    """
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"Настройки сохранены: {settings}")
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")


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

    Сохраняет введенный канал в JSON файл
    Подтверждает успешную установку

    :param message: Объект сообщения с названием канала
    :param state: Контекст состояния FSM
    :return: None
    """
    channel = message.text.strip()

    # Загружаем текущие настройки из JSON
    settings = load_settings()

    # Обновляем целевой канал
    settings["target_channel"] = channel

    # Сохраняем в JSON файл
    save_settings(settings)

    await message.answer(
        f"✅ Канал установлен: {channel}",
        reply_markup=admin_keyboard()
    )
    await state.clear()


def register_handlers_set_channel():
    """
    Регистрирует обработчики установки канала
    """
    router.callback_query.register(set_channel_start)