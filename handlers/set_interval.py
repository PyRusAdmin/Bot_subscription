# -*- coding: utf-8 -*-
import json
from pathlib import Path

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from keyboards.keyboards import admin_keyboard
from states.states import AdminSettings
from system.system import router, ADMIN_IDS

# Путь к JSON файлу с настройками — должен совпадать с другими модулями!
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


@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.answer("Отправьте интервал в секундах (например: 60)")
    await state.set_state(AdminSettings.waiting_for_interval)
    await callback.answer()


@router.message(AdminSettings.waiting_for_interval)
async def set_interval_process(message: Message, state: FSMContext):
    try:
        interval = int(message.text)
        if interval < 1:
            raise ValueError("Интервал должен быть больше 0")

        # Загружаем текущие настройки
        settings = load_settings()
        # Обновляем интервал
        settings["interval"] = interval
        # Сохраняем в JSON
        save_settings(settings)

        await message.answer(
            f"✅ Интервал установлен: {interval} сек",
            reply_markup=admin_keyboard()
        )
        await state.clear()

    except (ValueError, TypeError):
        await message.answer("❌ Укажите корректное число секунд (целое, больше 0)")
    except Exception as e:
        logger.error(f"Ошибка при установке интервала: {e}")
        await message.answer("❌ Произошла ошибка при сохранении настроек")


def set_interval_register_handler() -> None:
    router.callback_query.register(set_interval_start)