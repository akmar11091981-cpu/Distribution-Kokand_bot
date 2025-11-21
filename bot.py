import os
import logging
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask

# Логирование
logging.basicConfig(level=logging.INFO)

# Берём токен из переменной окружения BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --------- Хэндлеры Telegram-бота ---------

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Ассалому алейкум, Акмалхон!\n\n"
        "Бот DistributionKokand запущен и работает ✅\n"
        "Пока тут тестовый режим. Потом добавим анкету торговых точек."
    )


@dp.message_handler()
async def echo(message: types.Message):
    # Временно простой echo — для проверки,
    # что бот жив и видит сообщения.
    await message.answer(f"Ты написал: {message.text}")


# --------- Flask-сервер для Render (порт) ---------

app = Flask(__name__)

@app.route("/")
def index():
    return "DistributionKokand bot is running ✅"


def start_bot():
    """Запуск aiogram-поллинга в отдельном потоке."""
    logging.info("Starting Telegram bot polling...")
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    # Запускаем Telegram-бота в фоне
    t = Thread(target=start_bot, daemon=True)
    t.start()

    # Render даёт порт через переменную PORT
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Starting Flask health server on port {port}...")
    app.run(host="0.0.0.0", port=port)
