# -*- coding: utf-8 -*-
import csv
import json

from loguru import logger

from system.system import SETTINGS_FILE


def writes_data_to_csv_file(csv_data):
    """Записывает данные в CSV файл"""

    # Записываем данные в accounts.csv
    with open('accounts.csv', mode='w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(csv_data)


def load_settings():
    """
    Загружает настройки из JSON файла

    :return: Словарь с настройками или пустой словарь
    """
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
    """
    Сохраняет настройки в JSON файл

    :param settings: Словарь с настройками
    :return: None
    """
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"Настройки сохранены: {settings}")
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")
