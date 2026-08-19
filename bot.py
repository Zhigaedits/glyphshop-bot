import os
import asyncio
from threading import Thread

from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


# Веб-сервер для Render
web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "GlyphShop bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


PACKAGES = {
    "100": "50 000",
    "300": "165 000",
    "500": "275 000",
    "1000": "555 000",
    "2000": "1 110 000",
    "3000": "1 665 000",
}

ADMIN_ID = 816157991
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("📦 Мои покупки", callback_data="purchases")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
    ]

    await update.message.reply_text(
        "👋 Добро пожаловать в GlyphShop!\n\n"
        "💎 Здесь вы можете приобрести Glyphs.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "shop":
        keyboard = []

        for price, glyphs in PACKAGES.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"💎 {price} ₸ — {glyphs} Glyphs",
                    callback_data=f"pack_{price}",
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 Назад", callback_data="back")
        ])

        await query.edit_message_text(
            "🛒 GlyphShop\n\nВыберите пакет:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("pack_"):
        price = query.data.replace("pack_", "")
        glyphs = PACKAGES[price]

        card_number = os.environ.get("CARD_NUMBER", "")
        card_name = os.environ.get("CARD_NAME", "")

        keyboard = [
            [InlineKeyboardButton(
                "📋 Скопировать номер",
                copy_text={"text": card_number},
            )],
            [InlineKeyboardButton(
                "✅ Я оплатил",
                callback_data=f"paid_{price}",
            )],
            [InlineKeyboardButton(
                "🔙 Назад",
                callback_data="shop",
            )],
        ]

        await query.edit_message_text(
            f"💎 Пакет: {glyphs} Glyphs\n"
            f"💰 Сумма: {price} ₸\n\n"
            f"💳 Карта: {card_number}\n"
            f"👤 Владелец: {card_name}\n\n"
            "После перевода нажмите «✅ Я оплатил».",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "purchases":
        await query.edit_message_text(
            "📦 Мои покупки\n\nПокупок пока нет.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ]),
        )

    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Если возникли проблемы, обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ]),
        )

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
            [InlineKeyboardButton("📦 Мои покупки", callback_data="purchases")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
        ]

        await query.edit_message_text(
            "👋 Добро пожаловать в GlyphShop!",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("paid_"):
        price = query.data.replace("paid_", "")
        glyphs = PACKAGES[price]

        user = query.from_user
        username = f"@{user.username}" if user.username else user.full_name

        await query.edit_message_text(
            "⏳ Заявка на оплату отправлена.\n\n"
            "Ожидайте подтверждения."
        )
        if ADMIN_ID:
            keyboard = [[
                InlineKeyboardButton(
                    "✅ Подтвердить оплату",
                    callback_data=f"confirm_{user.id}_{price}",
                )
            ]]

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💰 Новая заявка на оплату!\n\n"
                    f"👤 Пользователь: {username}\n"
                    f"🆔 ID: {user.id}\n"
                    f"💰 Сумма: {price} ₸\n"
                    f"💎 Пакет: {glyphs} Glyphs\n\n"
                    "Проверьте поступление денег."
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        # Пока уведомление админу не подключено.
        print(
            f"PAYMENT REQUEST: {username} | "
            f"{price} KZT | {glyphs} Glyphs"
        )


async def run_bot():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN не установлен")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
