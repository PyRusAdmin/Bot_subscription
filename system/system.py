import os
from pathlib import Path

import dotenv
from aiogram import Router

# Создание основного роутера для бота
router = Router()

# Загрузка переменных окружения из .env файла
dotenv.load_dotenv()

# Конфигурационные переменные из .env файла
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_IDS = eval(os.getenv('ADMIN_IDS'))  # Преобразуем строку в список

# Директории
SESSIONS_DIR = "sessions"
# Создание директории для сессий, если она не существует
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Хранилище данных
accounts_db = {}
settings_db = {"target_channel": None, "interval": 60}

# Директория для хранения сессий Telethon
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)
