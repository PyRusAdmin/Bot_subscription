import os

# Установка зависимостей
os.system("pip install -r requirements.txt")

# Создание необходимых директорий
sessions_dir = "sessions"
if not os.path.exists(sessions_dir):
    os.makedirs(sessions_dir)
    print(f"📁 Создана директория: {sessions_dir}")
else:
    print(f"📁 Директория {sessions_dir} уже существует")

log_dir = "log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print(f"📁 Создана директория: {log_dir}")
else:
    print(f"📁 Директория {log_dir} уже существует")

print("✅ Установка завершена!")
