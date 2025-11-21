import os
import logging
import asyncio
import json
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from flask import Flask

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")

if not BOT_TOKEN or not GOOGLE_CREDS_JSON or not SHEET_ID:
    raise RuntimeError("Не заданы необходимые переменные окружения")

# Настройка Google Sheets доступ
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1  # используем первый лист

# Настройка бота
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

class PointForm(StatesGroup):
    name = State()
    contact_name = State()
    phone = State()
    group = State()
    route = State()
    potential = State()
    location = State()
    confirm = State()

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Ассалому алейкум!\n"
        "Заполняем анкету торговой точки.\n\n"
        "1️⃣ Напишите, пожалуйста, название торговой точки."
    )
    await PointForm.name.set()

@dp.message_handler(state=PointForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("2️⃣ Имя контактного лица (хозяин/продавец)?")
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
    await message.answer("5️⃣ Номер маршрута (например: 1001).")
    await PointForm.route.set()

@dp.message_handler(state=PointForm.route)
async def process_route(message: types.Message, state: FSMContext):
    await state.update_data(route=message.text.strip())
    await message.answer("6️⃣ Потенциал точки (например: сильная / средняя или сумма).")
    await PointForm.potential.set()

@dp.message_handler(state=PointForm.potential)
async def process_potential(message: types.Message, state: FSMContext):
    await state.update_data(potential=message.text.strip())
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Отправить геолокацию 📍", request_location=True))
    await message.answer(
        "7️⃣ Отправьте геолокацию точки (нажмите кнопку ниже).",
        reply_markup=kb
    )
    await PointForm.location.set()

@dp.message_handler(state=PointForm.location, content_types=["location"])
async def process_location(message: types.Message, state: FSMContext):
    if not message.location:
        await message.answer("Нужна геолокация. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    data.update({
        "latitude": message.location.latitude,
        "longitude": message.location.longitude
    })

    # Формируем ID точки (например: группа + маршрут)
    point_id = f"{data.get('group')} {data.get('route')}"

    # Запись в Google Sheets
    row = [
        message.date.strftime("%Y-%m-%d %H:%M:%S"),
        point_id,
        data.get("name"),
        data.get("contact_name"),
        data.get("phone"),
        data.get("group"),
        data.get("route"),
        data.get("potential"),
        data.get("latitude"),
        data.get("longitude")
    ]
    sheet.append_row(row)

    kb_remove = types.ReplyKeyboardRemove()
    await message.answer(
        f"✅ Паспорт торговой точки сформирован и записан.\n\n"
        f"ID точки: {point_id}",
        reply_markup=kb_remove
    )
    await state.finish()

@dp.message_handler()
async def fallback_echo(message: types.Message):
    await message.answer("Чтобы заполнить анкету точки — отправьте /start.")

app = Flask(__name__)

@app.route("/")
def index():
    return "Distribution-Kokand bot is running ✅"

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    Thread(target=start_bot, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
