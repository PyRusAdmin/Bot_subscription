import os

# Конфигурация
import dotenv
from aiogram import Router

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
