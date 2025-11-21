import os
import logging
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Ассалому алейкум!\n"
        "Distribution Kokand бот запущен и готов работать ✅"
    )

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

app = Flask(__name__)

@app.route("/")
def index():
    return "Distribution-Kokand bot is running ✅"

def start_bot():
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    Thread(target=start_bot, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
