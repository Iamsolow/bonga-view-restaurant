import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, add_menu_item, get_menu_items, add_expense_item, get_expense_items, record_transaction, get_detailed_report, get_recent_transactions, delete_transaction

TOKEN = "8030107480:AAGUqoobi8j2UA4s3Ieu7JhfRl1ojA2TRx4"
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

class RestaurantStates(StatesGroup):
    waiting_for_menu_name = State()
    waiting_for_menu_price = State()
    waiting_for_income_amount = State()
    waiting_for_income_qty = State()
    waiting_for_exp_item_name = State()
    waiting_for_exp_unit = State()
    waiting_for_exp_amount = State()
    waiting_for_exp_quantity = State()

def main_menu():
    kb = [[KeyboardButton(text="💰 ገቢ መመዝገቢያ"), KeyboardButton(text="💸 ወጪ መመዝገቢያ")],[KeyboardButton(text="📦 ስቶር/ዝርዝር"), KeyboardButton(text="📊 ሪፖርት")],[KeyboardButton(text="🗑️ ሂሳብ ሰርዝ")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def back_home_btn():
    return InlineKeyboardButton(text="🏠 ወደ ዋናው ሜኑ ተመለስ", callback_data="go_home")

@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    await message.answer("እንኳን ወደ ሬስቶራንት ሂሳብ መቆጣጠሪያ ቦት በሰላም መጡ!", reply_markup=main_menu())

@dp.callback_query(F.data == "go_home")
async def go_home(callback: types.CallbackQuery, state: FSMContext):
    if state: await state.clear()
    await callback.message.answer("ዋና ሜኑ፦", reply_markup=main_menu())
    await callback.answer()

# --- INCOME & EXPENSE (Omitted for brevity, keep existing logic) ---
# [Keep income/expense logic from previous version...]

@dp.message(F.text == "💰 ገቢ መመዝገቢያ")
async def income_menu(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🍺 መጠጥ", callback_data="inc:መጠጥ")],[InlineKeyboardButton(text="☕ ሻይ ቡና", callback_data="inc:ሻይ ቡና")],[InlineKeyboardButton(text="🍲 ምግብ", callback_data="inc:ምግብ")],[back_home_btn()]])
    await message.answer("የገቢውን አይነት ይምረጡ፦", reply_markup=builder)

@dp.callback_query(F.data.startswith("inc:"))
async def select_income_item(callback: types.CallbackQuery):
    category = callback.data.split(":")[1]
    items = get_menu_items(category)
    buttons = [[InlineKeyboardButton(text=f"{item[0]}", callback_data=f"selinc:{category}:{item[0]}:{item[1]}")] for item in items]
    buttons.append([InlineKeyboardButton(text="➕ አዲስ የሽያጭ ዝርዝር መዝግብ", callback_data=f"addmenu:{category}")])
    buttons.append([back_home_btn()])
    await callback.message.edit_text(f"የ{category} የሽያጭ ዝርዝር፦", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("selinc:"))
async def record_income_start(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":")
    await state.update_data(cat=data[1], item=data[2], def_price=data[3], unit="ቁጥር")
    await state.set_state(RestaurantStates.waiting_for_income_amount)
    await callback.message.answer(f"የ{data[2]} ዋጋ ያስገቡ (መደበኛ: {data[3]} ብር)፦")

@dp.message(RestaurantStates.waiting_for_income_amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    try:
        await state.update_data(amount=float(message.text))
        await state.set_state(RestaurantStates.waiting_for_income_qty)
        await message.answer("ብዛቱን ያስገቡ፦")
    except ValueError: await message.answer("ቁጥር ብቻ ያስገቡ!")

@dp.message(RestaurantStates.waiting_for_income_qty)
async def process_income_qty(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        data = await state.get_data()
        record_transaction('income', data['cat'], data['item'], data['amount'] * qty, qty, "ቁጥር")
        await message.answer(f"✅ የ{data['item']} ሽያጭ ተመዝግቧል (ጠቅላላ: {data['amount'] * qty} ብር)።", reply_markup=main_menu())
        await state.clear()
    except ValueError: await message.answer("ቁጥር ብቻ ያስገቡ!")

@dp.callback_query(F.data.startswith("addmenu:"))
async def add_menu_start(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cat=callback.data.split(":")[1])
    await state.set_state(RestaurantStates.waiting_for_menu_name)
    await callback.message.answer("የአዲሱ ሽያጭ ስም ያስገቡ (ለምሳሌ፦ ጥብስ)፦")

@dp.message(RestaurantStates.waiting_for_menu_name)
async def add_menu_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RestaurantStates.waiting_for_menu_price)
    await message.answer(f"የ{message.text} መደበኛ መሸጫ ዋጋ ያስገቡ፦")

@dp.message(RestaurantStates.waiting_for_menu_price)
async def add_menu_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        data = await state.get_data()
        add_menu_item(data['name'], data['cat'], price)
        await message.answer(f"✅ {data['name']} ተመዝግቧል። አሁን ሽያጩን መመዝገብ ይችላሉ። የሽያጭ ዋጋውን ያስገቡ፦")
        await state.update_data(item=data['name'], def_price=price, unit="ቁጥር")
        await state.set_state(RestaurantStates.waiting_for_income_amount)
    except ValueError: await message.answer("ቁጥር ብቻ ያስገቡ!")

@dp.message(F.text == "💸 ወጪ መመዝገቢያ")
async def expense_menu(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🍺 መጠጥ ወጪ", callback_data="exp:መጠጥ")],[InlineKeyboardButton(text="☕ ሻይ ቡና ወጪ", callback_data="exp:ሻይ ቡና")],[InlineKeyboardButton(text="🍲 ምግብ ወጪ", callback_data="exp:ምግብ")],[back_home_btn()]])
    await message.answer("የወጪውን አይነት ይምረጡ፦", reply_markup=builder)

@dp.callback_query(F.data.startswith("exp:"))
async def select_exp_item(callback: types.CallbackQuery):
    category = callback.data.split(":")[1]
    items = get_expense_items(category)
    buttons = [[InlineKeyboardButton(text=f"{item[0]} (ስቶር: {item[1]} {item[2]})", callback_data=f"selexp:{category}:{item[0]}:{item[2]}")] for item in items]
    buttons.append([InlineKeyboardButton(text="➕ አዲስ የወጪ/ስቶር ዝርዝር (ለምሳሌ፦ ጤፍ)", callback_data=f"addexp:{category}")])
    buttons.append([back_home_btn()])
    await callback.message.edit_text(f"የ{category} የወጪ ዝርዝር፦", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("selexp:"))
async def record_expense_start(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":")
    await state.update_data(cat=data[1], item=data[2], unit=data[3])
    await state.set_state(RestaurantStates.waiting_for_exp_amount)
    await callback.message.answer(f"ለ{data[2]} የወጣው ጠቅላላ ብር ያስገቡ፦")

@dp.message(RestaurantStates.waiting_for_exp_amount)
async def process_exp_amount(message: types.Message, state: FSMContext):
    try:
        await state.update_data(amount=float(message.text))
        await state.set_state(RestaurantStates.waiting_for_exp_quantity)
        data = await state.get_data()
        await message.answer(f"የገዙት የ{data['item']} ብዛት/መጠን ({data['unit']}) ስንት ነው?፦")
    except ValueError: await message.answer("ቁጥር ብቻ ያስገቡ!")

@dp.message(RestaurantStates.waiting_for_exp_quantity)
async def process_exp_qty(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        data = await state.get_data()
        record_transaction('expense', data['cat'], data['item'], data['amount'], qty, data['unit'])
        await message.answer(f"✅ የ{data['item']} ወጪ ተመዝግቧል።", reply_markup=main_menu())
        await state.clear()
    except ValueError: await message.answer("ቁጥር ብቻ ያስገቡ!")

@dp.callback_query(F.data.startswith("addexp:"))
async def add_exp_start(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cat=callback.data.split(":")[1])
    await state.set_state(RestaurantStates.waiting_for_exp_item_name)
    await callback.message.answer("የአዲሱ ወጪ እቃ ስም ያስገቡ (ለምሳሌ፦ ጤፍ)፦")

@dp.message(RestaurantStates.waiting_for_exp_item_name)
async def add_exp_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RestaurantStates.waiting_for_exp_unit)
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ኪሎ", callback_data="unit:ኪሎ"), InlineKeyboardButton(text="ሊትር", callback_data="unit:ሊትር")],[InlineKeyboardButton(text="ቁጥር", callback_data="unit:ቁጥር")]])
    await message.answer(f"የ{message.text} መለኪያ ይምረጡ፦", reply_markup=builder)

@dp.callback_query(F.data.startswith("unit:"))
async def add_exp_unit(callback: types.CallbackQuery, state: FSMContext):
    unit = callback.data.split(":")[1]
    data = await state.get_data()
    add_expense_item(data['name'], data['cat'], unit)
    await state.update_data(item=data['name'], unit=unit)
    await state.set_state(RestaurantStates.waiting_for_exp_amount)
    await callback.message.answer(f"✅ {data['name']} ተመዝግቧል። አሁን ለ{data['name']} የወጣውን ጠቅላላ ብር ያስገቡ፦")

@dp.message(F.text == "🗑️ ሂሳብ ሰርዝ")
async def show_recent_for_delete(message: types.Message):
    recent = get_recent_transactions(15)
    if not recent: await message.answer("ምንም የተመዘገበ ሂሳብ የለም።"); return
    buttons = [[InlineKeyboardButton(text=f"{'💰' if t[1] == 'income' else '💸'} {t[3]}: {t[4]} ብር ({t[7][11:16]})", callback_data=f"del:{t[0]}")] for t in recent]
    buttons.append([back_home_btn()])
    await message.answer("🗑️ ለመሰረዝ የሚፈልጉትን ሂሳብ ይምረጡ፦", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("del:"))
async def delete_item(callback: types.CallbackQuery, state: FSMContext):
    delete_transaction(callback.data.split(":")[1])
    await callback.answer("✅ ሂሳቡ ተሰርዟል!")
    await callback.message.edit_text("✅ ሂሳቡ በተሳካ ሁኔታ ተሰርዟል።")
    await asyncio.sleep(1)
    await go_home(callback, state)

@dp.message(F.text == "📦 ስቶር/ዝርዝር")
async def view_store(message: types.Message):
    msg = "📦 አሁን ያለው ስቶር (Inventory)፦\n\n"
    for cat in ["መጠጥ", "ሻይ ቡና", "ምግብ"]:
        items = get_expense_items(cat); msg += f"🔹 **{cat}**፦\n"
        for n, q, u in items: msg += f"   - {n}: {q} {u}\n"
        if not items: msg += "   ምንም እቃ የለም\n"
        msg += "\n"
    await message.answer(msg)

# --- REFINED REPORTS ---
@dp.message(F.text == "📊 ሪፖርት")
async def report_period_menu(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📅 የዛሬ", callback_data="repper:rep_daily")],[InlineKeyboardButton(text="📅 የሳምንት", callback_data="repper:rep_weekly")],[InlineKeyboardButton(text="📅 የወር", callback_data="repper:rep_monthly")],[back_home_btn()]])
    await message.answer("የሪፖርት ጊዜ ይምረጡ፦", reply_markup=builder)

@dp.callback_query(F.data.startswith("repper:"))
async def report_type_menu(callback: types.CallbackQuery):
    period = callback.data.split(":")[1]
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🍲 የምግብ ብቻ", callback_data=f"reptype:{period}:ምግብ")],[InlineKeyboardButton(text="🍺 የመጠጥ ብቻ", callback_data=f"reptype:{period}:መጠጥ")],[InlineKeyboardButton(text="☕ የሻይ ቡና ብቻ", callback_data=f"reptype:{period}:ሻይ ቡና")],[InlineKeyboardButton(text="📊 ሁሉንም", callback_data=f"reptype:{period}:ALL")],[back_home_btn()]])
    await callback.message.edit_text("የሪፖርት አይነት ይምረጡ፦", reply_markup=builder)

@dp.callback_query(F.data.startswith("reptype:"))
async def show_final_report(callback: types.CallbackQuery):
    _, period, r_type = callback.data.split(":")
    data = get_detailed_report(period)
    msg = f"📊 ዝርዝር ሪፖርት ({r_type})\n\n"
    total_inc, total_exp = 0, 0
    days_data = {}
    for t_type, cat, name, amount, qty, unit, day in data:
        if r_type != "ALL" and cat != r_type: continue
        if day not in days_data: days_data[day] = {"መጠጥ": {"inc": [], "exp": []}, "ሻይ ቡና": {"inc": [], "exp": []}, "ምግብ": {"inc": [], "exp": []}}
        u = unit if unit else ""
        if t_type == 'income':
            days_data[day][cat]["inc"].append(f"  • {name}: {amount} ብር ({qty} {u})")
            total_inc += amount
        else:
            days_data[day][cat]["exp"].append(f"  • {name}: {amount} ብር ({qty} {u})")
            total_exp += amount

    found = False
    for day, cats in sorted(days_data.items(), reverse=True):
        day_msg = f"📅 **ቀን፦ {day}**\n"
        day_has_data = False
        for cat, vals in cats.items():
            if vals["inc"] or vals["exp"]:
                day_msg += f"  🔹 {cat}፦\n"
                if vals["inc"]: day_msg += "    🔸 ገቢ፦\n" + "\n".join(vals["inc"]) + "\n"
                if vals["exp"]: day_msg += "    🔸 ወጪ፦\n" + "\n".join(vals["exp"]) + "\n"
                day_has_data = True
        if day_has_data:
            msg += day_msg + "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            found = True
    
    if not found: msg += "ምንም መረጃ የለም።"
    else: msg += f"💰 **ጠቅላላ ትርፍ፦ {total_inc - total_exp} ብር**"
    await callback.message.answer(msg)

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
