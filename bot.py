import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# ================= CONFIGURE =================
BOT_TOKEN = "8929627170:AAHck-M6w2XNVLtKs5F2aGUilIZBKkBDjh0"  # Bu yerga Telegram Bot Tokeningizni qo'ying
ADMIN_ID = 8929627170
WORKER_URL = "https://purple-star-e411.abrorovbehruz167-fe8.workers.dev"

ADMIN_SECRET_CODE = "123"
ADMIN_LOGIN = "abrorov_behruzjon"
ADMIN_PASSWORD = "19810330@"
# =============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# DB Sozlamalari
conn = sqlite3.connect("bot_database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    question TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    correct_option TEXT
)
""")
conn.commit()

# FSM Holatlari
class AdminAuth(StatesGroup):
    waiting_for_code = State()
    waiting_for_login = State()
    waiting_for_pass = State()

class AddTest(StatesGroup):
    waiting_for_subject = State()
    waiting_for_question = State()
    waiting_for_options = State()
    waiting_for_correct = State()

class Broadcast(StatesGroup):
    waiting_for_message = State()

# Tugmalar
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Fanlar"), KeyboardButton(text="📝 Testlar")],
            [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="🔐 Admin Panel")]
        ],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Test qo'shish")],
            [KeyboardButton(text="📢 Yangilik tarqatish")],
            [KeyboardButton(text="⬅️ Bosh menyu")]
        ],
        resize_keyboard=True
    )

# /start buyrug'i
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    await message.answer("Xush kelibsiz! MaktabHub AI botiga marhamat.", reply_markup=main_keyboard())

# Admin Paneliga Kirish
@dp.message(F.text == "🔐 Admin Panel")
async def admin_panel_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminAuth.waiting_for_code)
    await message.answer("Admin panelga kirish uchun maxsus kodni kiriting:", reply_markup=ReplyKeyboardRemove())

@dp.message(AdminAuth.waiting_for_code)
async def check_code(message: types.Message, state: FSMContext):
    if message.text == ADMIN_SECRET_CODE:
        await state.set_state(AdminAuth.waiting_for_login)
        await message.answer("Kod to'g'ri! Endi loginni kiriting:")
    else:
        await state.clear()
        await message.answer("Xato kod! Bosh menyuga qaytildingiz.", reply_markup=main_keyboard())

@dp.message(AdminAuth.waiting_for_login)
async def check_login(message: types.Message, state: FSMContext):
    if message.text == ADMIN_LOGIN:
        await state.set_state(AdminAuth.waiting_for_pass)
        await message.answer("Login to'g'ri! Endi parolni kiriting:")
    else:
        await state.clear()
        await message.answer("Xato login! Bosh menyuga qaytildingiz.", reply_markup=main_keyboard())

@dp.message(AdminAuth.waiting_for_pass)
async def check_pass(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await state.clear()
        await message.answer("Muvaffaqiyatli kirdingiz! Admin bo'limiga xush kelibsiz.", reply_markup=admin_keyboard())
    else:
        await state.clear()
        await message.answer("Xato parol! Bosh menyuga qaytildingiz.", reply_markup=main_keyboard())

@dp.message(F.text == "⬅️ Bosh menyu")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=main_keyboard())

# --- TEST QO'SHISH BO'LIMI ---
@dp.message(F.text == "➕ Test qo'shish")
async def add_test_start(message: types.Message, state: FSMContext):
    await state.set_state(AddTest.waiting_for_subject)
    await message.answer("Fanni kiriting (masalan: Matematika):")

@dp.message(AddTest.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await state.set_state(AddTest.waiting_for_question)
    await message.answer("Savolni kiriting:")

@dp.message(AddTest.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    await state.update_data(question=message.text)
    await state.set_state(AddTest.waiting_for_options)
    await message.answer("Variantlarni kiriting (Format: A variant, B variant, C variant):\n\n<i>Masalan: 4, 5, 6</i>", parse_mode="HTML")

@dp.message(AddTest.waiting_for_options)
async def process_options(message: types.Message, state: FSMContext):
    options = message.text.split(",")
    if len(options) < 3:
        await message.answer("Iltimos, kamida 3 ta variantni vergul bilan ajratib yozing! Masalan: A, B, C")
        return
    await state.update_data(opt_a=options[0].strip(), opt_b=options[1].strip(), opt_c=options[2].strip())
    await state.set_state(AddTest.waiting_for_correct)
    await message.answer("To'g'ri javob variantini yozing (A, B yoki C):")

@dp.message(AddTest.waiting_for_correct)
async def process_correct(message: types.Message, state: FSMContext):
    correct = message.text.upper().strip()
    if correct not in ["A", "B", "C"]:
        await message.answer("Faqat A, B yoki C harfini yuboring!")
        return
    
    data = await state.get_data()
    cursor.execute("""
    INSERT INTO tests (subject, question, option_a, option_b, option_c, correct_option)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (data['subject'], data['question'], data['opt_a'], data['opt_b'], data['opt_c'], correct))
    conn.commit()
    
    await state.clear()
    await message.answer("✅ Test muvaffaqiyatli saqlandi va faol holatga keltirildi!", reply_markup=admin_keyboard())

# --- YANGILIK TARQATISH BO'LIMI ---
@dp.message(F.text == "📢 Yangilik tarqatish")
async def broadcast_start(message: types.Message, state: FSMContext):
    await state.set_state(Broadcast.waiting_for_message)
    await message.answer("Barcha foydalanuvchilarga yuboriladigan xabar/yangilik matnini kiriting:")

@dp.message(Broadcast.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext):
    msg_text = message.text
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    count = 0
    await message.answer("Xabar tarqatish boshlandi...")
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 <b>YANGILIK:</b>\n\n{msg_text}", parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await state.clear()
    await message.answer(f"✅ Xabar muvaffaqiyatli {count} ta foydalanuvchiga yetkazildi!", reply_markup=admin_keyboard())

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())