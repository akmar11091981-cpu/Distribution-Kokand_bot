import os
import logging
import asyncio
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from flask import Flask

logging.basicConfig(level=logging.INFO)

# ----------------- Настройка бота -----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

# FSM-хранилище в памяти (для шагов анкеты)
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
    confirm = State()

# ----------------- Хэндлеры -----------------

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()  # на всякий случай чистим прошлое состояние
    await message.answer(
        "Ассалому алейкум!\n"
        "Заполняем анкету торговой точки.\n\n"
        "1️⃣ Напишите, пожалуйста, *название торговой точки*.",
        parse_mode="Markdown"
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
    await message.answer(
        "4️⃣ Группа точки (пример: *RW*, *RN*, *RE*).\n"
        "Напишите буквы группы.",
        parse_mode="Markdown"
    )
    await PointForm.group.set()

@dp.message_handler(state=PointForm.group)
async def process_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.strip().upper())
    await message.answer(
        "5️⃣ Номер маршрута (пример: *1001*, *2001*, *3001*).\n"
        "Напишите только цифры.",
        parse_mode="Markdown"
    )
    await PointForm.route.set()

@dp.message_handler(state=PointForm.route)
async def process_route(message: types.Message, state: FSMContext):
    await state.update_data(route=message.text.strip())
    await message.answer(
        "6️⃣ Потенциал точки (например: ‘сильная’, ‘средняя’, "
        "или напишите сумму/тоннаж как понимаете)."
    )
    await PointForm.potential.set()

@dp.message_handler(state=PointForm.potential)
async def process_potential(message: types.Message, state: FSMContext):
    await state.update_data(potential=message.text.strip())

    # Кнопка для отправки геолокации
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Отправить геолокацию 📍", request_location=True))

    await message.answer(
        "7️⃣ Теперь отправьте, пожалуйста, геолокацию точки.\n"
        "Нажмите кнопку ниже.",
        reply_markup=kb
    )
    await PointForm.location.set()

@dp.message_handler(content_types=["location"], state=PointForm.location)
async def process_location(message: types.Message, state: FSMContext):
    if not message.location:
        await message.answer("Нужна именно геолокация. Попробуйте ещё раз.")
        return

    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )

    data = await state.get_data()
    kb_remove = types.ReplyKeyboardRemove()

    text = (
        "✅ Паспорт торговой точки:\n\n"
        f"🏪 Название: {data.get('name')}\n"
        f"👤 Контакт: {data.get('contact_name')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"🧭 Группа: {data.get('group')}\n"
        f"🚛 Маршрут: {data.get('route')}\n"
        f"📊 Потенциал: {data.get('potential')}\n"
        f"📍 Локация: {data.get('latitude')}, {data.get('longitude')}\n\n"
        "Анкета сохранена локально в боте.\n"
        "Позже мы добавим отправку в Google Sheets и карту."
    )

    await message.answer(text, reply_markup=kb_remove)
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
    """Запускаем aiogram-поллинг в отдельном потоке с собственным event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True)

# ----------------- Точка входа -----------------

if __name__ == "__main__":
    Thread(target=start_bot, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

