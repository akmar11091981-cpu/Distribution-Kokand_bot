import logging
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Логирование
logging.basicConfig(level=logging.INFO)

# Токен берём из переменной окружения (BOT_TOKEN на Render)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is not set")

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ---------- Состояния анкеты ----------
class PointForm(StatesGroup):
    location = State()
    address = State()
    owner_name = State()
    owner_phone = State()
    seller_phone = State()
    point_format = State()
    assortment = State()
    suppliers = State()
    brands = State()
    logistics = State()


# ---------- /start ----------
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    text = (
        "Ассалому алейкум!\n\n"
        "Этот бот собирает данные по торговым точкам.\n\n"
        "Чтобы добавить новую точку, отправьте команду:\n"
        "<b>/newpoint</b>\n\n"
        "Для отмены анкеты в любой момент: /cancel"
    )
    await message.answer(text)


# ---------- /newpoint ----------
@dp.message_handler(commands=["newpoint"])
async def cmd_newpoint(message: types.Message, state: FSMContext):
    await PointForm.location.set()
    await message.answer(
        "1️⃣ Отправьте геолокацию точки.\n\n"
        "Нажмите 📎 → «Геопозиция» и выберите точку."
    )


# ---------- Шаг 1: Геолокация ----------
@dp.message_handler(content_types=["location"], state=PointForm.location)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )
    await PointForm.address.set()
    await message.answer("2️⃣ Введите короткий адрес / ориентир (улица, махалля, ориентир).")


@dp.message_handler(state=PointForm.location)
async def process_location_wrong(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте именно <b>геолокацию</b>, а не текст.")


# ---------- Шаг 2: Адрес ----------
@dp.message_handler(state=PointForm.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await PointForm.owner_name.set()
    await message.answer("3️⃣ Введите ФИО владельца.")


# ---------- Шаг 3: ФИО владельца ----------
@dp.message_handler(state=PointForm.owner_name)
async def process_owner_name(message: types.Message, state: FSMContext):
    await state.update_data(owner_name=message.text.strip())
    await PointForm.owner_phone.set()
    await message.answer("4️⃣ Телефон владельца (например: +99890xxxxxxx).")


# ---------- Шаг 4: Телефон владельца ----------
@dp.message_handler(state=PointForm.owner_phone)
async def process_owner_phone(message: types.Message, state: FSMContext):
    await state.update_data(owner_phone=message.text.strip())
    await PointForm.seller_phone.set()
    await message.answer(
        "5️⃣ Телефон продавца.\n"
        "Если владелец и продавец один человек — напишите: <b>тот же</b>."
    )


# ---------- Шаг 5: Телефон продавца ----------
@dp.message_handler(state=PointForm.seller_phone)
async def process_seller_phone(message: types.Message, state: FSMContext):
    await state.update_data(seller_phone=message.text.strip())

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Магазин", "Ишлабо чиқариш", "Қурувчи")

    await PointForm.point_format.set()
    await message.answer("6️⃣ Выберите формат точки:", reply_markup=keyboard)


# ---------- Шаг 6: Формат точки ----------
@dp.message_handler(state=PointForm.point_format)
async def process_point_format(message: types.Message, state: FSMContext):
    fmt = message.text.strip()
    if fmt not in ["Магазин", "Ишлабо чиқариш", "Қурувчи"]:
        await message.answer("Выберите один из вариантов: Магазин / Ишлабо чиқариш / Қурувчи.")
        return

    await state.update_data(point_format=fmt)

    await PointForm.assortment.set()
    await message.answer(
        "7️⃣ Укажите ассортимент через запятую.\n"
        "Например: цемент, арматура, газоблок, рейка, шифер, сантехника, провода",
        reply_markup=types.ReplyKeyboardRemove(),
    )


# ---------- Шаг 7: Ассортимент ----------
@dp.message_handler(state=PointForm.assortment)
async def process_assortment(message: types.Message, state: FSMContext):
    await state.update_data(assortment=message.text.strip())
    await PointForm.suppliers.set()
    await message.answer("8️⃣ У кого точка сейчас закупается? Напишите 1–2 основных поставщика.")


# ---------- Шаг 8: Закупки ----------
@dp.message_handler(state=PointForm.suppliers)
async def process_suppliers(message: types.Message, state: FSMContext):
    await state.update_data(suppliers=message.text.strip())
    await PointForm.brands.set()
    await message.answer("9️⃣ Какие бренды стоят на полке? (через запятую).")


# ---------- Шаг 9: Бренды ----------
@dp.message_handler(state=PointForm.brands)
async def process_brands(message: types.Message, state: FSMContext):
    await state.update_data(brands=message.text.strip())

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Газель", "Газель, 10т", "10т, 20т", "Газель, 10т, 20т, 30т")

    await PointForm.logistics.set()
    await message.answer(
        "🔟 Для каких машин есть подъезд?\n"
        "Можете выбрать вариант или написать свой (Газель, 10т, 20т, 30т).",
        reply_markup=keyboard,
    )


# ---------- Шаг 10: Логистика + итог ----------
@dp.message_handler(state=PointForm.logistics)
async def process_logistics(message: types.Message, state: FSMContext):
    await state.update_data(logistics=message.text.strip())
    data = await state.get_data()

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    # Отправляем локацию обратно
    if latitude and longitude:
        await message.answer_location(latitude=latitude, longitude=longitude)
        maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
    else:
        maps_url = None

    summary = (
        "<b>Новая торговая точка:</b>\n\n"
        f"📍 Геолокация: {latitude}, {longitude}\n"
        + (f"🌍 <a href=\"{maps_url}\">Открыть в Google Maps</a>\n\n" if maps_url else "\n")
        + f"🏠 Адрес: {data.get('address')}\n\n"
        f"👤 Владелец: {data.get('owner_name')}\n"
        f"📞 Тел. владельца: {data.get('owner_phone')}\n"
        f"📞 Тел. продавца: {data.get('seller_phone')}\n\n"
        f"🏪 Формат точки: {data.get('point_format')}\n"
        f"📦 Ассортимент: {data.get('assortment')}\n\n"
        f"🔍 Закупается у: {data.get('suppliers')}\n"
        f"🏷 Бренды: {data.get('brands')}\n\n"
        f"🚚 Логистика (подъезд): {data.get('logistics')}\n"
    )

    await message.answer("✅ Точка сохранена (пока в виде сообщения).")
    await message.answer(summary, reply_markup=types.ReplyKeyboardRemove())

    await state.finish()


# ---------- /cancel ----------
@dp.message_handler(commands=["cancel"], state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Анкету отменили.", reply_markup=types.ReplyKeyboardRemove())


# ---------- Запуск ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)