# -*- coding: utf-8 -*-
import io

from aiogram import F
from aiogram.types import CallbackQuery, BufferedInputFile

from keyboards.keyboards import main_keyboard
from system.system import router, ADMIN_IDS, SESSIONS_DIR


@router.callback_query(F.data == "my_accounts")
async def send_session_files_list(callback: CallbackQuery):
    """
    Отправляет список всех .session файлов в виде TXT-файла.
    Без подключения к Telegram — только имена файлов.
    Доступно только администраторам.
    """
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Доступ запрещён", show_alert=True)

    session_files = sorted(SESSIONS_DIR.glob("*.session"))
    if not session_files:
        await callback.message.answer("Нет сессий в папке sessions/")
        return await callback.answer()

    # Формируем текст: по одному имени файла на строку
    lines = ["📋 Список .session файлов:\n"]
    for path in session_files:
        lines.append(path.name)

    file_content = "\n".join(lines).encode("utf-8")
    bio = io.BytesIO(file_content)
    bio.name = "список_сессий.txt"

    document = BufferedInputFile(bio.getvalue(), filename="список_сессий.txt")
    await callback.message.answer_document(
        document=document,
        caption="📁 Вот список всех ваших .session файлов.",
        reply_markup=main_keyboard(True)
    )
    await callback.answer()


def register_show_accounts():
    router.callback_query.register(send_session_files_list)
