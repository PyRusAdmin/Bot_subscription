from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard(is_admin=False):
    """
    Главная клавиатура бота (пользователя)
    :param is_admin:
    :return: InlineKeyboardMarkup
    """
    buttons = [
        [InlineKeyboardButton(text="📤 Загрузить сессию", callback_data="upload_session")],
        [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="my_accounts")],
        [InlineKeyboardButton(text="✅ Проверить аккаунты", callback_data="check_accounts")],
        [InlineKeyboardButton(text="➕ Подписаться на канал", callback_data="subscribe_channel")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Настройки (Админ)", callback_data="admin_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard():
    """
    Клавиатура для администратора бота. ID админа берется из .env файла
    :return: InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Установить канал", callback_data="set_channel")],
        [InlineKeyboardButton(text="⏱ Установить интервал", callback_data="set_interval")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
