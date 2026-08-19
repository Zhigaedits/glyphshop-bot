import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

PACKAGES = {
    "100": "50 000",
    "300": "165 000",
    "500": "275 000",
    "1000": "555 000",
    "2000": "1 110 000",
    "3000": "1 665 000",
}


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

        keyboard = [
            [InlineKeyboardButton(
                "💳 Оплатить",
                callback_data=f"pay_{price}",
            )],
            [InlineKeyboardButton(
                "🔙 Назад",
                callback_data="shop",
            )],
        ]

        await query.edit_message_text(
            f"💎 Пакет: {glyphs} Glyphs\n"
            f"💰 Цена: {price} ₸\n\n"
            "Оплата пока не подключена.",
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

    elif query.data.startswith("pay_"):
        await query.edit_message_text(
            "💳 Оплата пока не подключена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="shop")]
            ]),
        )


async def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN не установлен в Render")

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


if __name__ == "__main__":
    asyncio.run(main())
