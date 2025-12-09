from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.keyboards import admin_keyboard
from states.states import AdminSettings
from system.system import router, ADMIN_IDS, settings_db


@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик установки интервала

    Запускает процесс установки интервала между действиями
    Переходит в состояние ожидания ввода интервала
    Доступно только для администраторов

    :param callback: Объект callback-запроса
    :param state: Контекст состояния FSM
    :return: None
    """
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.answer("Отправьте интервал в секундах (например: 60)")
    await state.set_state(AdminSettings.waiting_for_interval)
    await callback.answer()


@router.message(AdminSettings.waiting_for_interval)
async def set_interval_process(message: Message, state: FSMContext):
    """
    Обработчик установки интервала

    Сохраняет введенный интервал в настройки
    Проверяет корректность значения (целое число > 0)
    Подтверждает успешную установку

    :param message: Объект сообщения с интервалом в секундах
    :param state: Контекст состояния FSM
    :return: None
    """
    try:
        interval = int(message.text)
        if interval < 1:
            raise ValueError
        settings_db["interval"] = interval
        await message.answer(
            f"✅ Интервал установлен: {interval} сек",
            reply_markup=admin_keyboard()
        )
        await state.clear()
    except:
        await message.answer("❌ Укажите корректное число секунд")


def set_interval_register_handler():
    router.callback_query.register(set_interval_start)
