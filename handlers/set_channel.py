# -*- coding: utf-8 -*-

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.keyboards import admin_keyboard
from states.states import AdminSettings
from system.system import router, ADMIN_IDS
from utilit.utilit import load_settings, save_settings


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


def register_handlers_set_channel() -> None:
    """
    Регистрирует обработчики команд для установки канала

    Подключает обработчики команды set_channel к роутеру бота.
    Вызывается при инициализации бота в основном файле.

    :return: None
    """
    router.callback_query.register(set_channel_start)
