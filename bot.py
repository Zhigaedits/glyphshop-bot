import os
import asyncio
from threading import Thread

from flask import Flask
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# НАСТРОЙКИ
# =========================

ADMIN_ID = 816157991

# 100 000 Glyphs = 180 ₸
GLYPHS_PER_TENGE = 100000 / 180

PACKAGES = {
    "100": "50 000",
    "300": "165 000",
    "500": "275 000",
    "1000": "555 000",
    "2000": "1 110 000",
    "3000": "1 665 000",
}


# =========================
# WEB-СЕРВЕР ДЛЯ RENDER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "GlyphShop bot is live!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("📦 Мои покупки", callback_data="purchases")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
    ]

    await update.message.reply_text(
        "👋 Добро пожаловать в GlyphShop!\n\n"
        "💎 Здесь вы можете приобрести Glyphs.\n\n"
        "Выберите нужный раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ПОКАЗ ОПЛАТЫ
# =========================

async def show_payment(
    query,
    context,
    price,
    glyphs,
):
    card_number = os.environ.get("CARD_NUMBER", "")
    card_name = os.environ.get("CARD_NAME", "")

    if not card_number:
        card_number = "Номер карты не настроен"

    if not card_name:
        card_name = "Имя владельца не настроено"

    keyboard = [
        [
            InlineKeyboardButton(
                "📋 Скопировать номер",
                copy_text=CopyTextButton(card_number),
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Я оплатил",
                callback_data=f"paid_{price}_{glyphs}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="shop",
            )
        ],
    ]

    await query.edit_message_text(
        f"💎 Вы выбрали: {glyphs:,} Glyphs\n"
        f"💰 Сумма: {price} ₸\n\n"
        f"💳 Номер карты:\n{card_number}\n\n"
        f"👤 Владелец: {card_name}\n\n"
        "После перевода нажмите «✅ Я оплатил»."
        .replace(",", " "),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# КНОПКИ
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # -------------------------
    # МАГАЗИН
    # -------------------------

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
            InlineKeyboardButton(
                "💰 Своя сумма",
                callback_data="custom_amount",
            )
        ])

        keyboard.append([
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="back",
            )
        ])

        await query.edit_message_text(
            "🛒 GlyphShop\n\n"
            "Выберите готовый пакет или укажите свою сумму:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # -------------------------
    # ГОТОВЫЙ ПАКЕТ
    # -------------------------

    elif query.data.startswith("pack_"):
        price = query.data.replace("pack_", "")
        glyphs = PACKAGES.get(price)

        if not glyphs:
            await query.answer(
                "❌ Пакет не найден.",
                show_alert=True,
            )
            return

        await show_payment(
            query,
            context,
            price,
            glyphs,
        )

    # -------------------------
    # СВОЯ СУММА
    # -------------------------

    elif query.data == "custom_amount":
        context.user_data["waiting_for_amount"] = True

        await query.edit_message_text(
            "💰 Своя сумма\n\n"
            "Напишите сумму в тенге одним сообщением.\n\n"
            "Например:\n"
            "875\n\n"
            "Курс:\n"
            "100 000 Glyphs = 180 ₸"
        )

    # -------------------------
    # МОИ ПОКУПКИ
    # -------------------------

    elif query.data == "purchases":
        await query.edit_message_text(
            "📦 Мои покупки\n\n"
            "Покупки пока не подключены.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Назад",
                        callback_data="back",
                    )
                ]
            ]),
        )

    # -------------------------
    # ПОМОЩЬ
    # -------------------------

    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Если возникли проблемы с покупкой, "
            "обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Назад",
                        callback_data="back",
                    )
                ]
            ]),
        )

    # -------------------------
    # НАЗАД
    # -------------------------

    elif query.data == "back":
        keyboard = [
            [
                InlineKeyboardButton(
                    "🛒 Магазин",
                    callback_data="shop",
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 Мои покупки",
                    callback_data="purchases",
                )
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ Помощь",
                    callback_data="help",
                )
            ],
        ]

        await query.edit_message_text(
            "👋 Добро пожаловать в GlyphShop!\n\n"
            "💎 Здесь вы можете приобрести Glyphs.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # -------------------------
    # Я ОПЛАТИЛ
    # -------------------------

    elif query.data.startswith("paid_"):
        parts = query.data.split("_", 2)

        if len(parts) != 3:
            await query.answer(
                "❌ Ошибка заявки.",
                show_alert=True,
            )
            return

        price = parts[1]
        glyphs = parts[2]

        user = query.from_user

        if user.username:
            username = f"@{user.username}"
        else:
            username = user.full_name

        await query.edit_message_text(
            "⏳ Заявка отправлена администратору.\n\n"
            "После проверки оплаты ожидайте подтверждения."
        )

        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💰 НОВАЯ ЗАЯВКА\n\n"
                    f"👤 Пользователь: {username}\n"
                    f"🆔 ID: {user.id}\n"
                    f"💰 Сумма: {price} ₸\n"
                    f"💎 Glyphs: {glyphs}\n\n"
                    "⚠️ Проверьте поступление оплаты вручную."
                ),
            )


# =========================
# СВОЯ СУММА — ОБРАБОТКА
# =========================

async def custom_amount_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get("waiting_for_amount"):
        return

    text = update.message.text.strip()

    try:
        price = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Введите сумму только цифрами.\n\n"
            "Например: 875"
        )
        return

    if price < 1:
        await update.message.reply_text(
            "❌ Сумма должна быть больше 0 ₸."
        )
        return

    if price > 1000000:
        await update.message.reply_text(
            "❌ Слишком большая сумма."
        )
        return

    context.user_data["waiting_for_amount"] = False

    glyphs_number = int(price * GLYPHS_PER_TENGE)

    glyphs_display = f"{glyphs_number:,}".replace(",", " ")

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Оплатить",
                callback_data=f"custompay_{price}_{glyphs_number}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="shop",
            )
        ],
    ]

    await update.message.reply_text(
        f"💰 Ваша сумма: {price} ₸\n"
        f"💎 Вы получите: {glyphs_display} Glyphs\n\n"
        "Нажмите «💳 Оплатить», чтобы продолжить.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# КНОПКА ОПЛАТИТЬ ДЛЯ СВОЕЙ СУММЫ
# =========================

async def custom_payment_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 2)

    if len(parts) != 3:
        await query.answer(
            "❌ Ошибка.",
            show_alert=True,
        )
        return

    price = parts[1]
    glyphs = parts[2]

    await show_payment(
        query,
        context,
        price,
        glyphs,
    )


# =========================
# MAIN
# =========================

async def run_bot():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN не установлен"
        )

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(
            custom_payment_button,
            pattern=r"^custompay_",
        )
    )

    application.add_handler(
        CallbackQueryHandler(buttons)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            custom_amount_handler,
        )
    )

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
    web_thread = Thread(
        target=run_web,
        daemon=True,
    )

    web_thread.start()

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
