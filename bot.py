import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

import storage
import ai
import parser as deal_parser

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# ─── Клавиатура ───────────────────────────────────────────────
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛒 Новый список"), KeyboardButton("🏷️ Найти акции")],
        [KeyboardButton("💰 Замены для экономии"), KeyboardButton("🏠 Что есть дома")],
        [KeyboardButton("🗑️ Очистить список"), KeyboardButton("❓ Помощь")],
        [KeyboardButton("📖 Все рецепты"), KeyboardButton("🥕 Что приготовить?")],
        [KeyboardButton("📋 История покупок")]
    ],
    resize_keyboard=True
)

# ─── /start ───────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    is_new = user.get("requests_today", 0) == 0 and not user.get("history")

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Онбординг для новых пользователей
    if is_new:
        welcome_text = (
            f"Привет, {name}! Я Личный Шеф — твой AI помощник на кухне.\n\n"
            "Что умею:\n"
            "🍲 Составить список покупок по рецепту\n"
            "🔥 Посчитать калории и КБЖУ\n"
            "🏷️ Найти акции в Магните и Пятёрочке\n"
            "🥕 Предложить блюда из того что есть дома\n"
            "💰 Найти дешёвые замены продуктов\n\n"
            "Попробуй прямо сейчас — нажми одну из кнопок:"
        )
        inline_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍲 Борщ на 4 человека", callback_data="quick_borsh"),
                InlineKeyboardButton("🍝 Карбонара на 2", callback_data="quick_pasta"),
            ],
            [
                InlineKeyboardButton("🥕 Что из холодильника?", callback_data="quick_fridge"),
                InlineKeyboardButton("📖 Все рецепты", callback_data="quick_recipes"),
            ],
            [
                InlineKeyboardButton("🚀 Pro план — 299₽/мес", callback_data="quick_pro"),
            ]
        ])
        await update.message.reply_text(
            welcome_text,
            reply_markup=inline_kb
        )
    else:
        # Для вернувшихся пользователей
        await update.message.reply_text(
            f"С возвращением, {name}! 👋\n\n"
            "Чем могу помочь?",
            reply_markup=MAIN_KEYBOARD
        )

# ─── /help ────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Напиши что хочешь приготовить:\n"
        "   <i>«борщ на 4 человека»</i>\n\n"
        "2. Скажи что есть дома через кнопку <b>🏠 Что есть дома</b>\n"
        "   или прямо в чате: <i>«дома есть яйца и масло»</i>\n\n"
        "3. Нажми <b>🏷️ Найти акции</b> — покажу где дешевле\n\n"
        "4. Нажми <b>💰 Замены для экономии</b> — предложу аналоги\n\n"
        "5. <b>🗑️ Очистить список</b> — начать заново\n\n"
        "Можно просто писать как другу — я всё пойму! 😊",
        parse_mode=ParseMode.HTML,
        reply_markup=MAIN_KEYBOARD
    )

# ─── Очистить список ──────────────────────────────────────────
async def clear_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage.clear_list(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ Список очищен! Начнём заново?\nНапиши что хочешь приготовить.",
        reply_markup=MAIN_KEYBOARD
    )

# ─── Что есть дома ────────────────────────────────────────────
async def set_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_home"] = True
    await update.message.reply_text(
        "🏠 Напиши что есть дома через запятую:\n\n"
        "<i>Например: яйца, масло, соль, перец, лук</i>",
        parse_mode=ParseMode.HTML
    )

# ─── Найти акции ──────────────────────────────────────────────
async def find_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    
    # Собираем последний список из истории
    history = user.get("history", [])
    if not history:
        await update.message.reply_text(
            "Сначала составь список покупок! Напиши что хочешь приготовить 🍲"
        )
        return
    
    await update.message.reply_text("🔍 Ищу акции в магазинах...")
    
    # Берём последний ответ бота с списком
    last_bot_reply = ""
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_bot_reply = msg["content"]
            break
    
    # Извлекаем продукты
    items = ai.parse_items_from_reply(last_bot_reply)
    
    if not items:
        await update.message.reply_text("Не смог определить продукты из списка. Попробуй составить список заново.")
        return
    
    # Ищем акции
    deals = deal_parser.find_deals_for_items(items)
    message = deal_parser.format_deals_message(deals)
    
    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=MAIN_KEYBOARD)

# ─── Замены для экономии ──────────────────────────────────────
async def get_substitutions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await update.message.reply_text(
            "Сначала составь список покупок! Напиши что хочешь приготовить 🍲"
        )
        return
    
    await update.message.reply_text("💭 Думаю над заменами...")
    
    last_bot_reply = ""
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_bot_reply = msg["content"]
            break
    
    result = ai.get_substitutions(last_bot_reply)
    await update.message.reply_text(result, reply_markup=MAIN_KEYBOARD)

# ─── Главный обработчик сообщений ─────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Кнопки
    if text == "🛒 Новый список":
        storage.clear_list(user_id)
        await update.message.reply_text(
            "Отлично! Что будем готовить?\n\n"
            "<i>Напиши рецепт и количество человек, например:\n"
            "«борщ и котлеты на 3 человека»</i>",
            parse_mode=ParseMode.HTML
        )
        return
    elif text == "🏷️ Найти акции":
        await find_deals(update, context)
        return
    elif text == "💰 Замены для экономии":
        await get_substitutions(update, context)
        return
    elif text == "📋 История покупок":
        await show_history(update, context)
        return
    elif text == "📖 Все рецепты":
        menu = ai.get_recipe_menu()
        await update.message.reply_text(menu, parse_mode=ParseMode.HTML, reply_markup=MAIN_KEYBOARD)
        return
    elif text == "🥕 Что приготовить?":
        context.user_data["waiting_for_fridge"] = True
        await update.message.reply_text(
            "🥕 Напиши что есть у тебя дома через запятую:\n\n"
            "<i>Например: яйца, картошка, лук, сметана, курица</i>\n\n"
            "Я предложу 5 блюд которые можно приготовить!",
            parse_mode=ParseMode.HTML
        )
        return
    elif text == "🏠 Что есть дома":
        await set_home(update, context)
        return
    elif text == "🗑️ Очистить список":
        await clear_list(update, context)
        return
    elif text == "❓ Помощь":
        await help_cmd(update, context)
        return
    
    # Ожидаем список продуктов для подбора блюд
    if context.user_data.get("waiting_for_fridge"):
        context.user_data["waiting_for_fridge"] = False
        await update.message.chat.send_action("typing")
        result = await ai.suggest_dishes(text)
        await update.message.reply_text(result, parse_mode=ParseMode.HTML, reply_markup=MAIN_KEYBOARD)
        return

    # Ожидаем ввод того что есть дома
    if context.user_data.get("waiting_for_home"):
        context.user_data["waiting_for_home"] = False
        items = [item.strip() for item in text.split(",") if item.strip()]
        storage.set_at_home(user_id, items)
        await update.message.reply_text(
            f"✅ Запомнил! Дома есть: {', '.join(items)}\n\n"
            "Теперь при составлении списка исключу их автоматически.",
            reply_markup=MAIN_KEYBOARD
        )
        return
    
    # Обычный чат с AI
    user = storage.get_user(user_id)
    
    await update.message.chat.send_action("typing")
    
    try:
        reply, updated_history = ai.chat(
            user_id=user_id,
            message=text,
            history=user.get("history", []),
            at_home=user.get("at_home", [])
        )
        
        user["history"] = updated_history
        storage.save_user(user_id, user)
        
        await update.message.reply_text(reply, reply_markup=MAIN_KEYBOARD)
        
        # Если это похоже на список покупок — предлагаем найти акции
        if any(word in reply.lower() for word in ["овощи", "мясо", "молочн", "бакалея", "список"]):
            await update.message.reply_text(
                "💡 Хочешь найду акции на эти продукты? Нажми <b>🏷️ Найти акции</b>",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ Что-то пошло не так: {str(e)}\nПопробуй ещё раз."
        )

# ─── /pro ─────────────────────────────────────────────────────
async def pro_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    is_pro = user.get("is_pro", False)
    if is_pro:
        await update.message.reply_text(
            "Pro план активен. Безлимит, акции, умные замены.",
            reply_markup=MAIN_KEYBOARD
        )
    else:
        await update.message.reply_text(
            "Pro план - 299 руб/мес\n"
            "- Безлимитные запросы\n"
            "- Акции в 5 магазинах\n"
            "- Умные замены\n"
            "- История покупок\n\n"
            "Для оплаты: @YOUR_ADMIN",
            reply_markup=MAIN_KEYBOARD
        )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    is_pro = user.get("is_pro", False)
    used = user.get("requests_today", 0)
    _, remaining = storage.check_limit(user_id)
    if is_pro:
        plan = "Pro (безлимит)"
    else:
        plan = "Бесплатный, осталось " + str(remaining) + " из 5 сегодня"
    msg = "Статус: " + plan + "\nЗапросов сегодня: " + str(used)
    if not is_pro:
        msg += "\n\n/pro - перейти на Pro"
    await update.message.reply_text(msg, reply_markup=MAIN_KEYBOARD)



# ─── История покупок ──────────────────────────────────────────
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = storage.get_shopping_history(user_id)

    if not history:
        await update.message.reply_text(
            "История пуста. Составь первый список!\n\n"
            "Напиши например: борщ на 4 человека",
            reply_markup=MAIN_KEYBOARD
        )
        return

    msg = "📋 Последние списки покупок:\n\n"
    for i, entry in enumerate(history, 1):
        msg += f"{i}. {entry['date']} — {entry['recipe']}\n"

    msg += "\nНапиши номер чтобы повторить список, например: повтори 1"
    await update.message.reply_text(msg, reply_markup=MAIN_KEYBOARD)

async def repeat_list(update: Update, context: ContextTypes.DEFAULT_TYPE, num: int):
    user_id = update.effective_user.id
    history = storage.get_shopping_history(user_id)

    if not history or num > len(history):
        await update.message.reply_text("Список не найден.", reply_markup=MAIN_KEYBOARD)
        return

    entry = history[num - 1]
    await update.message.reply_text(
        f"Список от {entry['date']}:\n\n{entry['items']}",
        reply_markup=MAIN_KEYBOARD
    )

# ─── Обработчик инлайн кнопок онбординга ─────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    quick_messages = {
        "quick_borsh": "борщ на 4 человека",
        "quick_pasta": "паста карбонара на 2 человека",
        "quick_fridge": "что приготовить из яиц, картошки и лука?",
        "quick_recipes": "покажи все рецепты",
        "quick_pro": "/pro",
    }

    if data in quick_messages:
        msg = quick_messages[data]
        if msg == "/pro":
            await pro_info(update, context)
            return

        # Убираем инлайн кнопки
        await query.edit_message_reply_markup(reply_markup=None)

        # Отправляем сообщение как будто пользователь написал сам
        user = storage.get_user(user_id)
        can_request, remaining = storage.check_limit(user_id)
        if not can_request:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Дневной лимит исчерпан (5 запросов).\nPro план за 299 руб/мес — /pro",
                reply_markup=MAIN_KEYBOARD
            )
            return

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")

        try:
            reply, updated_history = ai.chat(
                user_id=user_id,
                message=msg,
                history=user.get("history", []),
                at_home=user.get("at_home", [])
            )
            user["history"] = updated_history
            storage.save_user(user_id, user)
            storage.increment_requests(user_id)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=reply,
                reply_markup=MAIN_KEYBOARD
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Что-то пошло не так. Попробуй ещё раз.",
                reply_markup=MAIN_KEYBOARD
            )

# ─── Запуск ───────────────────────────────────────────────────
def main():
    print("🤖 Бот запускается...")

    PROXY = "http://user252978:my0if1@138.249.249.223:6393"

    app = (
        Application.builder()
        .token(TOKEN)
        .proxy(PROXY)
        .get_updates_proxy(PROXY)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("pro", pro_info))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
