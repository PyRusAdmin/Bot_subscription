import asyncio
import os

# Конфигурация
import dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.token import TokenValidationError
from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

# Роутер
router = Router()


dotenv.load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_IDS = eval(os.getenv('ADMIN_IDS'))  # Преобразуем строку в список


# Директории
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Хранилище данных
accounts_db = {}  # {user_id: [{"session": "path", "phone": "phone", "status": "active"}]}
settings_db = {"target_channel": None, "interval": 60}  # Настройки подписки