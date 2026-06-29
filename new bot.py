from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8723775714:AAEgJWdeNWIbmg34oHCcdG5skZ_d7GGvt1Q"
ADMIN_CHAT_ID = 1191164193  # Your personal Telegram ID

ASK_TYPE, ASK_NAME, ASK_PHONE, DONE = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Full Account", callback_data="full")],
        [InlineKeyboardButton("🔍 Trial Account", callback_data="trial")]
    ])
    await update.message.reply_text(
        "👋 Welcome to MQ Bank!\n\nWhat type of account would you like?",
        reply_markup=keyboard
    )
    return ASK_TYPE

async def account_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["type"] = query.data.capitalize()
    await query.edit_message_text(
        f"Great! You chose a *{context.user_data['type']} Account*.\n\nWhat's your full name?",
        parse_mode="Markdown"
    )
    return ASK_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    phone_button = KeyboardButton("📱 Share my phone number", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[phone_button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"Thanks {update.message.text}! Now please share your phone number:",
        reply_markup=keyboard
    )
    return ASK_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    name = context.user_data["name"]
    acc_type = context.user_data["type"]
    student_id = update.effective_user.id
    username = update.effective_user.username or "no username"

    name_parts = name.strip().lower().split()
    email = f"{name_parts[0]}@{name_parts[-1]}.com" if len(name_parts) >= 2 else f"{name_parts[0]}@mqbank.com"
    password = phone.replace("+", "")

    active_users[student_id] = {"name": name, "phone": phone, "type": acc_type}

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"🆕 New account request!\n\n"
            f"📋 Type: {acc_type}\n"
            f"👤 Name: {name}\n"
            f"📞 Phone: {phone}\n"
            f"🔗 Username: @{username}\n"
            f"🆔 ID: {student_id}\n\n"
            f"To reply:\n/reply {student_id} <message>\n\n"
            f"📧 Email: {email}\n"
            f"🔑 Password: {password}"
        )
    )

    await update.message.reply_text(
        "✅ Request sent! You'll hear back soon.\n\nFeel free to send a screenshot or message anytime if you need help.",
        reply_markup=ReplyKeyboardRemove()
    )
    return DONE

# Handle messages AND screenshots after signup
async def handle_student_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_id = update.effective_user.id
    if student_id == ADMIN_CHAT_ID:
        return
    name = active_users.get(student_id, {}).get("name", f"User {student_id}")

    if update.message.photo:
        # Forward the screenshot to you
        caption = update.message.caption or ""
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=update.message.photo[-1].file_id,  # highest resolution
            caption=f"📸 Screenshot from {name} (ID: {student_id}):\n{caption}\n\nReply: /reply {student_id} <message>"
        )
        await update.message.reply_text("📸 Screenshot received! We'll get back to you soon.")
    elif update.message.text:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"💬 Message from {name} (ID: {student_id}):\n\n{update.message.text}\n\nReply: /reply {student_id} <message>"
        )

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    try:
        student_id = int(context.args[0])
        message = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=student_id, text=message)
        await update.message.reply_text("✅ Sent!")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reply <user_id> <message>")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

active_users = {}

def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_TYPE: [CallbackQueryHandler(account_type)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_student_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_student_message))
    app.run_polling()

if __name__ == "__main__":
    main()