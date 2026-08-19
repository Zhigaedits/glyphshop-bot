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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_for_amount", None)
    context.user_data.pop("pending_order", None)
    context.user_data.pop("receipt_sent", None)

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

async def show_shop(query):
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

async def show_payment(query, context, price, glyphs):
    card_number = os.environ.get(
        "CARD_NUMBER",
        "Карта не настроена",
    )

    card_name = os.environ.get(
        "CARD_NAME",
        "Имя не настроено",
    )

    glyphs = int(glyphs)
    price = int(price)

    glyphs_text = f"{glyphs:,}".replace(",", " ")

    context.user_data["pending_order"] = {
        "price": price,
        "glyphs": glyphs,
    }

    context.user_data["receipt_sent"] = False

    keyboard = [
        [
            InlineKeyboardButton(
                f"💳 {card_number}",
                callback_data="card_info",
            )
        ],
        [
            InlineKeyboardButton(
                "📎 Отправить квитанцию",
                callback_data="send_receipt",
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
        "1️⃣ Переведите указанную сумму.\n"
        "2️⃣ Нажмите «📎 Отправить квитанцию».\n"
        "3️⃣ Отправьте файл или фото квитанции.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# КНОПКИ
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    data = query.data

    # =========================
    # МАГАЗИН
    # =========================

    if data == "shop":
        await show_shop(query)
        return

    # =========================
    # ПАКЕТ
    # =========================

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
            context,
            price,
            glyphs,
        )
        return

    # =========================
    # СВОЯ СУММА
    # =========================

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

    # =========================
    # КАРТА
    # =========================

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

    # =========================
    # ОТПРАВИТЬ КВИТАНЦИЮ
    # =========================

    if data == "send_receipt":
        order = context.user_data.get("pending_order")

        if not order:
            await query.answer(
                "❌ Сначала выберите пакет.",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            "📎 Отправьте сюда квитанцию.\n\n"
            "Можно отправить файл или фото "
            "квитанции из Kaspi.\n\n"
            "После отправки появится кнопка "
            "«✅ Я оплатил счёт»."
        )

        context.user_data["waiting_for_receipt"] = True
        return

    # =========================
    # Я ОПЛАТИЛ СЧЁТ
    # =========================

    if data == "paid_confirm":
        order = context.user_data.get("pending_order")

        if not order:
            await query.answer(
                "❌ Заказ не найден.",
                show_alert=True,
            )
            return

        if not context.user_data.get("receipt_sent", False):
            await query.answer(
                "❌ Сначала отправьте квитанцию.",
                show_alert=True,
            )
            return

        price = order["price"]
        glyphs = order["glyphs"]

        user = query.from_user

        if user.username:
            username = f"@{user.username}"
        else:
            username = user.full_name

        await query.edit_message_text(
            "⏳ Заявка отправлена.\n\n"
            "Квитанция передана администратору.\n"
            "Ожидайте подтверждения оплаты."
        )

        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Подтвердить оплату",
                    callback_data=(
                        f"admin_confirm_{user.id}_{price}_{glyphs}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{user.id}",
                )
            ],
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💰 ПОДТВЕРЖДЕНИЕ ОПЛАТЫ\n\n"
                f"👤 Пользователь: {username}\n"
                f"🆔 ID: {user.id}\n"
                f"💰 Сумма: {price} ₸\n"
                f"💎 Glyphs: {glyphs:,}\n\n"
                "📎 Квитанция была отправлена выше."
            ).replace(",", " "),
            reply_markup=admin_keyboard,
        )

        return

    # =========================
    # АДМИН: ПОДТВЕРДИТЬ
    # =========================

    if data.startswith("admin_confirm_"):

        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )
            return

        parts = data.split("_")

        # ВАЖНО:
        # admin_confirm_USER_ID_PRICE_GLYPHS
        # = 5 частей
        if len(parts) != 5:
            await query.answer(
                "❌ Ошибка заявки.",
                show_alert=True,
            )
            return

        user_id = parts[2]
        price = parts[3]
        glyphs = parts[4]

        await query.edit_message_text(
            "✅ Оплата подтверждена.\n\n"
            f"👤 ID: {user_id}\n"
            f"💰 Сумма: {price} ₸\n"
            f"💎 Glyphs: {int(glyphs):,}".replace(",", " "),
        )

        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                "✅ Оплата подтверждена!\n\n"
                f"💰 Сумма: {price} ₸\n"
                f"💎 Glyphs: {int(glyphs):,}\n\n"
                "Ваш платёж проверен администратором."
            ).replace(",", " "),
        )

        return

    # =========================
    # АДМИН: ОТКЛОНИТЬ
    # =========================

    if data.startswith("admin_reject_"):

        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )
            return

        parts = data.split("_")

        if len(parts) != 3:
            return

        user_id = parts[2]

        await query.edit_message_text(
            "❌ Оплата отклонена.\n\n"
            f"👤 ID: {user_id}"
        )

        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                "❌ Оплата не подтверждена.\n\n"
                "Пожалуйста, свяжитесь с администратором."
            ),
        )

        return

    # =========================
    # МОИ ПОКУПКИ
    # =========================

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

    # =========================
    # ПОМОЩЬ
    # =========================

    if data == "help":
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Выберите пакет или укажите свою сумму.\n"
            "После оплаты отправьте квитанцию.\n\n"
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

    # =========================
    # НАЗАД
    # =========================

    if data == "back":
        await start_from_button(query)
        return


# =========================
# ГЛАВНОЕ МЕНЮ
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

    glyphs = int(price * GLYPHS_PER_TENGE)

    glyphs_text = f"{glyphs:,}".replace(",", " ")

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
        context,
        price,
        glyphs,
    )


# =========================
# ПОЛУЧЕНИЕ КВИТАНЦИИ
# =========================

async def receipt_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get(
        "waiting_for_receipt",
        False,
    ):
        return

    order = context.user_data.get("pending_order")

    if not order:
        await update.message.reply_text(
            "❌ Заказ не найден. "
            "Сначала выберите пакет."
        )
        return

    user = update.effective_user

    price = order["price"]
    glyphs = order["glyphs"]

    if user.username:
        username = f"@{user.username}"
    else:
        username = user.full_name

    context.user_data["waiting_for_receipt"] = False
    context.user_data["receipt_sent"] = True

    # Пересылаем оригинальную квитанцию админу
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "⚠️ Не удалось переслать квитанцию.\n\n"
                f"Ошибка: {e}"
            ),
        )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "📎 ПОЛУЧЕНА КВИТАНЦИЯ\n\n"
            f"👤 Пользователь: {username}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Сумма: {price} ₸\n"
            f"💎 Glyphs: {glyphs:,}\n\n"
            "Пользователь должен нажать "
            "«✅ Я оплатил счёт»."
        ).replace(",", " "),
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Я оплатил счёт",
                callback_data="paid_confirm",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 В магазин",
                callback_data="shop",
            )
        ],
    ]

    await update.message.reply_text(
        "📎 Квитанция получена!\n\n"
        "Теперь нажмите:\n"
        "✅ «Я оплатил счёт»",
        reply_markup=InlineKeyboardMarkup(keyboard),
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
            filters.Document.ALL | filters.PHOTO,
            receipt_handler,
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

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
