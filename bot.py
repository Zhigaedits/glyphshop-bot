import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

PACKAGES = {
    "100": ("50 000", 100),
    "300": ("165 000", 300),
    "500": ("275 000", 500),
    "1000": ("555 000", 1000),
    "2000": ("1 110 000", 2000),
    "3000": ("1 665 000", 3000),
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Добро пожаловать в GlyphShop!\n\n"
        "💎 Здесь вы можете приобрести Glyphs.\n\n"
        "Выберите нужный раздел:"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("📦 Мои покупки", callback_data="purchases")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "shop":
        keyboard = []

        for price, (glyphs, _) in PACKAGES.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"💎 {price} ₸ — {glyphs} Glyphs",
                    callback_data=f"pack_{price}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 Назад", callback_data="back")
        ])

        await query.edit_message_text(
            "🛒 GlyphShop\n\nВыберите пакет:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("pack_"):
        price = query.data.replace("pack_", "")
        glyphs, _ = PACKAGES[price]

        keyboard = [
            [InlineKeyboardButton(
                "💳 Оплатить",
                callback_data=f"pay_{price}"
            )],
            [InlineKeyboardButton(
                "🔙 Назад",
                callback_data="shop"
            )],
        ]

        await query.edit_message_text(
            f"💎 Пакет: {glyphs} Glyphs\n"
            f"💰 Цена: {price} ₸\n\n"
            "Нажмите «Оплатить», чтобы продолжить.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "purchases":
        await query.edit_message_text(
            "📦 Ваши покупки\n\n"
            "Пока покупок нет.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ])
        )

    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Если у вас возникли проблемы с покупкой, "
            "обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ])
        )

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
            [InlineKeyboardButton("📦 Мои покупки", callback_data="purchases")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
        ]

        await query.edit_message_text(
            "👋 Добро пожаловать в GlyphShop!\n\n"
            "💎 Здесь вы можете приобрести Glyphs.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("pay_"):
        await query.edit_message_text(
            "💳 Оплата пока не подключена.\n\n"
            "Скоро здесь появится способ оплаты.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="shop")]
            ])
        )


def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise ValueError("BOT_TOKEN не установлен")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()


if __name__ == "__main__":
    main()
