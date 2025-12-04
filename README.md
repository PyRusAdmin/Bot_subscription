# Bot Subscription

Этот бот помогает управлять Telegram-аккаунтами и автоматически подписываться на каналы.

## Настройка

Для работы бота необходимо создать файл `.env` в корне проекта со следующими параметрами:

```
BOT_TOKEN=YOUR_BOT_TOKEN
API_ID=12345
API_HASH=your_api_hash
ADMIN_IDS=[123456789]
```

Где:
- `BOT_TOKEN` — токен вашего бота от [@BotFather](https://t.me/BotFather)
- `API_ID` и `API_HASH` — данные от [my.telegram.org](https://my.telegram.org)
- `ADMIN_IDS` — список ID администраторов в формате Python-списка

После создания файла `.env` запустите бот с помощью команды:

```bash
python main.py
```