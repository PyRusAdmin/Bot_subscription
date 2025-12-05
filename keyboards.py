from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard(is_admin=False) -> InlineKeyboardMarkup:
    """
    Создает главную клавиатуру бота для пользователя

    Отображает основные функции бота:
    - Загрузка сессии
    - Просмотр аккаунтов
    - Проверка аккаунтов
    - Подписка на канал
    - Удаление сессии

    Для администраторов добавляет кнопку настроек

    :param is_admin: Флаг, указывающий, является ли пользователь администратором
    :return: Объект InlineKeyboardMarkup с сформированной клавиатурой
    """
    buttons = [
        [InlineKeyboardButton(text="📤 Загрузить сессию", callback_data="upload_session")],
        [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="my_accounts")],
        [InlineKeyboardButton(text="✅ Проверить аккаунты", callback_data="check_accounts")],
        [InlineKeyboardButton(text="➕ Подписаться на канал", callback_data="subscribe_channel")],
        [InlineKeyboardButton(text="🗑 Удалить сессию", callback_data="delete_session")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Настройки (Админ)", callback_data="admin_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру администратора бота

    Отображает функции управления ботом:
    - Установка целевого канала
    - Установка интервала между действиями
    - Возврат в главное меню

    Кнопки соответствуют командам, доступным только администраторам

    :return: Объект InlineKeyboardMarkup с админ-клавиатурой
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Установить канал", callback_data="set_channel")],
        [InlineKeyboardButton(text="⏱ Установить интервал", callback_data="set_interval")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
