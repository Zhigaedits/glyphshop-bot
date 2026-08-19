import os
import asyncio
from threading import Thread

from flask import Flask

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
    "100": 50000,
    "300": 165000,
    "500": 275000,
    "1000": 555000,
    "2000": 1110000,
    "3000": 1665000,
}


# =========================
# RENDER WEB SERVER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "GlyphShop bot is live!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(
        host="0.0.0.0",
        port=port,
    )


# =========================
# /START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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

    await update.message.reply_text(
        "👋 Добро пожаловать в GlyphShop!\n\n"
        "💎 Здесь вы можете приобрести Glyphs.\n\n"
        "Выберите нужный раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# МАГАЗИН
# =========================

async def show_shop(
    query,
):
    keyboard = []

    for price, glyphs in PACKAGES.items():
        glyphs_text = f"{glyphs:,}".replace(",", " ")

        keyboard.append([
            InlineKeyboardButton(
                f"💎 {price} ₸ — {glyphs_text} Glyphs",
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
        "Выберите пакет или укажите свою сумму:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# СТРАНИЦА ОПЛАТЫ
# =========================

async def show_payment(
    query,
    price,
    glyphs,
):
    card_number = os.environ.get(
        "CARD_NUMBER",
        "Карта не настроена",
    )

    card_name = os.environ.get(
        "CARD_NAME",
        "Имя не настроено",
    )

    glyphs_text = f"{int(glyphs):,}".replace(",", " ")

    keyboard = [
        [
            InlineKeyboardButton(
                f"💳 {card_number}",
                callback_data="card_info",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Я перевёл деньги",
                callback_data=f"paid_{price}_{int(glyphs)}",
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
        f"💎 Glyphs: {glyphs_text}\n"
        f"💰 Сумма: {price} ₸\n\n"
        f"💳 Карта:\n{card_number}\n"
        f"👤 Владелец: {card_name}\n\n"
        "После перевода нажмите "
        "«💳 Я перевёл деньги».",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ОБРАБОТКА КНОПОК
# =========================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    data = query.data

    # -------------------------
    # МАГАЗИН
    # -------------------------

    if data == "shop":
        await show_shop(query)
        return

    # -------------------------
    # ПАКЕТ
    # -------------------------

    if data.startswith("pack_"):
        price = data.replace("pack_", "")

        if price not in PACKAGES:
            await query.answer(
                "❌ Пакет не найден.",
                show_alert=True,
            )
            return

        glyphs = PACKAGES[price]

        await show_payment(
            query,
            price,
            glyphs,
        )
        return

    # -------------------------
    # СВОЯ СУММА
    # -------------------------

    if data == "custom_amount":
        context.user_data["waiting_for_amount"] = True

        await query.edit_message_text(
            "💰 Своя сумма\n\n"
            "Напишите сумму в тенге.\n\n"
            "Например:\n"
            "875\n\n"
            "Курс:\n"
            "100 000 Glyphs = 180 ₸",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Назад",
                        callback_data="shop",
                    )
                ]
            ]),
        )
        return

    # -------------------------
    # КАРТА
    # -------------------------

    if data == "card_info":
        card_number = os.environ.get(
            "CARD_NUMBER",
            "Карта не настроена",
        )

        await query.answer(
            f"Номер карты: {card_number}",
            show_alert=True,
        )
        return

    # -------------------------
    # Я ОПЛАТИЛ
    # -------------------------

    if data.startswith("paid_"):
        parts = data.split("_")

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
            "⏳ Заявка отправлена.\n\n"
            "Администратор проверит перевод "
            "и сообщит о результате."
        )

        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💰 НОВАЯ ЗАЯВКА\n\n"
                    f"👤 Пользователь: {username}\n"
                    f"🆔 ID: {user.id}\n"
                    f"💰 Сумма: {price} ₸\n"
                    f"💎 Glyphs: {int(glyphs):,}\n\n"
                    "⚠️ Проверьте поступление перевода вручную."
                    .replace(",", " ")
                ),
            )

        return

    # -------------------------
    # МОИ ПОКУПКИ
    # -------------------------

    if data == "purchases":
        await query.edit_message_text(
            "📦 Мои покупки\n\n"
            "История покупок пока не подключена.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Назад",
                        callback_data="back",
                    )
                ]
            ]),
        )
        return

    # -------------------------
    # ПОМОЩЬ
    # -------------------------

    if data == "help":
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Выберите пакет или укажите свою сумму.\n"
            "После перевода нажмите кнопку оплаты.\n\n"
            "Если возникли проблемы, обратитесь "
            "к администратору.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Назад",
                        callback_data="back",
                    )
                ]
            ]),
        )
        return

    # -------------------------
    # НАЗАД
    # -------------------------

    if data == "back":
        await start_from_button(query)
        return


# =========================
# ГЛАВНОЕ МЕНЮ ИЗ КНОПКИ
# =========================

async def start_from_button(query):
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


# =========================
# СВОЯ СУММА
# =========================

async def custom_amount_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get(
        "waiting_for_amount",
        False,
    ):
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
            "❌ Максимальная сумма — 1 000 000 ₸."
        )
        return

    context.user_data["waiting_for_amount"] = False

    glyphs = int(
        price * GLYPHS_PER_TENGE
    )

    glyphs_text = f"{glyphs:,}".replace(
        ",",
        " ",
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Оплатить",
                callback_data=f"custompay_{price}_{glyphs}",
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
        f"💰 Сумма: {price} ₸\n"
        f"💎 Вы получите: {glyphs_text} Glyphs\n\n"
        "Нажмите «💳 Оплатить».",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ОПЛАТА СВОЕЙ СУММЫ
# =========================

async def custom_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split("_")

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
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            custom_payment,
            pattern=r"^custompay_",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            buttons,
        )
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

    asyncio.run(
        run_bot()
    )


if __name__ == "__main__":
    main()
