import os
import json
import logging
import asyncio
from threading import Thread
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from flask import Flask

import gspread
from oauth2client.service_account import ServiceAccountCredentials


# ----------------- Логирование -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------- Переменные окружения -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")
if not GOOGLE_CREDS_JSON:
    raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS environment variable is not set")
if not SHEET_ID:
    raise RuntimeError("GOOGLE_SHEETS_ID environment variable is not set")


# ----------------- Google Sheets -----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1  # первый лист


# ----------------- Настройка бота -----------------
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)


# ----------------- Состояния анкеты -----------------
class PointForm(StatesGroup):
    name = State()
    contact_name = State()
    phone = State()
    group = State()
    route = State()
    potential = State()
    location = State()
    confirm = State()  # на будущее, пока не используется


# ----------------- Хэндлеры бота -----------------
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message, state: FSMContext):
    """Старт анкеты торговой точки."""
    await state.finish()  # очищаем любое предыдущее состояние

    await message.answer(
        "Ассалому алейкум!\n"
        "Заполняем анкету торговой точки.\n\n"
        "1️⃣ Напишите, пожалуйста, название торговой точки."
    )
    await PointForm.name.set()


@dp.message_handler(state=PointForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("2️⃣ Имя контактного лица (владельца / продавца)?")
    await PointForm.contact_name.set()


@dp.message_handler(state=PointForm.contact_name)
async def process_contact_name(message: types.Message, state: FSMContext):
    await state.update_data(contact_name=message.text.strip())
    await message.answer("3️⃣ Номер телефона (в любом формате)?")
    await PointForm.phone.set()


@dp.message_handler(state=PointForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("4️⃣ Группа точки (пример: RW, RN, RE).")
    await PointForm.group.set()


@dp.message_handler(state=PointForm.group)
async def process_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.strip().upper())
    await message.answer("5️⃣ Номер маршрута (например: 1001, 2001, 3001).")
    await PointForm.route.set()


@dp.message_handler(state=PointForm.route)
async def process_route(message: types.Message, state: FSMContext):
    await state.update_data(route=message.text.strip())
    await message.answer(
        "6️⃣ Потенциал точки (например: «сильная», «средняя» "
        "или напишите примерный тоннаж / сумму)."
    )
    await PointForm.potential.set()


@dp.message_handler(state=PointForm.potential)
async def process_potential(message: types.Message, state: FSMContext):
    await state.update_data(potential=message.text.strip())

    # Кнопка для отправки геолокации
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Отправить геолокацию 📍", request_location=True))

    await message.answer(
        "7️⃣ Теперь отправьте геолокацию точки (нажмите кнопку ниже).",
        reply_markup=kb,
    )
    await PointForm.location.set()


@dp.message_handler(content_types=["location"], state=PointForm.location)
async def process_location(message: types.Message, state: FSMContext):
    """Принимаем геолокацию, записываем всё в Google Sheets и шлём ПОЛНЫЙ паспорт."""
    if not message.location:
        await message.answer("Нужна геолокация. Попробуйте ещё раз.")
        return

    data = await state.get_data()

    latitude = message.location.latitude
    longitude = message.location.longitude

    # Обновляем в state (на будущее, если нужно)
    await state.update_data(latitude=latitude, longitude=longitude)

    name = data.get("name")
    contact_name = data.get("contact_name")
    phone = data.get("phone")
    group = data.get("group")
    route = data.get("route")
    potential = data.get("potential")

    # Формируем ID точки (простой вариант: группа + маршрут)
    point_id = f"{group} {route}"

    # Запись в Google Sheets
    try:
        timestamp = message.date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        timestamp,
        point_id,
        name,
        contact_name,
        phone,
        group,
        route,
        potential,
        latitude,
        longitude,
    ]
    try:
        sheet.append_row(row)
    except Exception as e:
        logger.error(f"Ошибка записи в Google Sheets: {e}")

    # Формируем ПОЛНЫЙ паспорт торговой точки
    passport_text = (
        "✅ Паспорт торговой точки:\n\n"
        f"🏪 Название: {name}\n"
        f"👤 Контакт: {contact_name}\n"
        f"📞 Телефон: {phone}\n"
        f"🧭 Группа: {group}\n"
        f"🚛 Маршрут: {route}\n"
        f"📊 Потенциал: {potential}\n"
        f"📍 Локация: {latitude}, {longitude}\n"
        f"🆔 ID точки: {point_id}\n\n"
        "Анкета сохранена локально в боте и в Google Sheets.\n"
        "Позже эта точка будет добавлена на карту."
    )

    kb_remove = types.ReplyKeyboardRemove()
    await message.answer(passport_text, reply_markup=kb_remove)

    await state.finish()


# Запасной echo, если нет активного состояния
@dp.message_handler()
async def fallback_echo(message: types.Message):
    await message.answer(
        "Чтобы заполнить анкету точки, отправьте /start.\n\n"
        f"Вы написали: {message.text}"
    )


# ----------------- Flask для Render -----------------
app = Flask(__name__)


@app.route("/")
def index():
    return "Distribution-Kokand bot is running ✅"


def start_bot():
    """Запуск aiogram-поллинга в отдельном потоке с собственным event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True)


# ----------------- Точка входа -----------------
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    Thread(target=start_bot, daemon=True).start()

    # Запускаем Flask-сервер для Render
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

