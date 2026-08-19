import os
import asyncio
import json
import uuid
from datetime import datetime
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

# 180 ₸ = 100 000 Glyphs
GLYPHS_PER_TENGE = 100000 / 180

PACKAGES = {
    "100": 55555,
    "500": 277777,
    "1000": 555555,
    "1500": 833333,
    "2000": 1111111,
    "2500": 1388888,
    "3000": 1666666,
    "3500": 1944444,
}

TRANSACTIONS_FILE = "transactions.json"


# =========================
# ТРАНЗАКЦИИ
# =========================

def load_transactions():
    if not os.path.exists(TRANSACTIONS_FILE):
        return {}

    try:
        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return {}


def save_transactions(transactions):
    with open(
        TRANSACTIONS_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            transactions,
            file,
            ensure_ascii=False,
            indent=2,
        )


def create_transaction(
    user_id,
    username,
    price,
    glyphs,
):
    transactions = load_transactions()

    transaction_id = uuid.uuid4().hex[:12].upper()

    transactions[transaction_id] = {
        "id": transaction_id,
        "user_id": int(user_id),
        "username": username,
        "price": int(price),
        "glyphs": int(glyphs),
        "status": "waiting_receipt",
        "receipt_received": False,
        "created_at": datetime.now().isoformat(),
        "confirmed_at": None,
    }

    save_transactions(transactions)

    return transaction_id


def update_transaction(
    transaction_id,
    **changes,
):
    transactions = load_transactions()

    if transaction_id not in transactions:
        return False

    transactions[transaction_id].update(changes)

    save_transactions(transactions)

    return True


# =========================
# RENDER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "GlyphShop bot is live!"


def run_web():
    port = int(
        os.environ.get(
            "PORT",
            10000,
        )
    )

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
    context.user_data.clear()

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
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================
# МАГАЗИН
# =========================

async def show_shop(query):

    keyboard = []

    for price, glyphs in PACKAGES.items():

        glyphs_text = (
            f"{glyphs:,}"
            .replace(",", " ")
        )

        keyboard.append([
            InlineKeyboardButton(
                f"💎 {price} ₸ — "
                f"{glyphs_text} Glyphs",
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
        "Выберите пакет или укажите "
        "свою сумму:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================
# СТРАНИЦА ОПЛАТЫ
# =========================

async def show_payment(
    query,
    context,
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

    price = int(price)
    glyphs = int(glyphs)

    glyphs_text = (
        f"{glyphs:,}"
        .replace(",", " ")
    )

    user = query.from_user

    if user.username:
        username = f"@{user.username}"
    else:
        username = user.full_name

    transaction_id = create_transaction(
        user.id,
        username,
        price,
        glyphs,
    )

    context.user_data[
        "transaction_id"
    ] = transaction_id

    context.user_data[
        "waiting_for_receipt"
    ] = False

    context.user_data[
        "waiting_for_amount"
    ] = False

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
        f"🧾 Транзакция: "
        f"`{transaction_id}`\n\n"
        f"💎 Glyphs: {glyphs_text}\n"
        f"💰 Сумма: {price} ₸\n\n"
        f"💳 Карта:\n{card_number}\n"
        f"👤 Владелец: {card_name}\n\n"
        "1️⃣ Переведите указанную сумму.\n"
        "2️⃣ Нажмите «📎 Отправить квитанцию».\n"
        "3️⃣ Отправьте квитанцию именно "
        "как ФАЙЛ.",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown",
    )


# =========================
# КНОПКИ
# =========================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # =========================
    # SHOP
    # =========================

    if data == "shop":

        context.user_data[
            "waiting_for_amount"
        ] = False

        context.user_data[
            "waiting_for_receipt"
        ] = False

        context.user_data[
            "admin_sending_link"
        ] = False

        await show_shop(query)

        return

    # =========================
    # PACKAGE
    # =========================

    if data.startswith("pack_"):

        price = data.replace(
            "pack_",
            "",
        )

        if price not in PACKAGES:

            await query.answer(
                "❌ Пакет не найден.",
                show_alert=True,
            )

            return

        await show_payment(
            query,
            context,
            price,
            PACKAGES[price],
        )

        return

    # =========================
    # CUSTOM AMOUNT
    # =========================

    if data == "custom_amount":

        context.user_data[
            "waiting_for_amount"
        ] = True

        context.user_data[
            "waiting_for_receipt"
        ] = False

        await query.edit_message_text(
            "💰 Своя сумма\n\n"
            "Напишите сумму в тенге.\n\n"
            "Например:\n"
            "875\n\n"
            "Курс:\n"
            "180 ₸ = 100 000 Glyphs",
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
    # CARD
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
    # SEND RECEIPT
    # =========================

    if data == "send_receipt":

        transaction_id = (
            context.user_data.get(
                "transaction_id"
            )
        )

        if not transaction_id:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        context.user_data[
            "waiting_for_receipt"
        ] = True

        context.user_data[
            "waiting_for_amount"
        ] = False

        await query.edit_message_text(
            "📎 Отправьте квитанцию сюда "
            "ИМЕННО КАК ФАЙЛ.\n\n"
            "❗ Фото отправлять нельзя.\n"
            "❗ Текст вместо квитанции нельзя.\n\n"
            "После получения файла появится "
            "кнопка «✅ Я оплатил счёт»."
        )

        return

    # =========================
    # CONFIRM PAYMENT
    # =========================

    if data == "paid_confirm":

        transaction_id = (
            context.user_data.get(
                "transaction_id"
            )
        )

        if not transaction_id:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        transactions = load_transactions()

        transaction = transactions.get(
            transaction_id
        )

        if not transaction:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        if not transaction[
            "receipt_received"
        ]:

            await query.answer(
                "❌ Сначала отправьте квитанцию.",
                show_alert=True,
            )

            return

        if transaction[
            "status"
        ] != "receipt_received":

            await query.answer(
                "❌ Эта транзакция уже обработана "
                "или находится в другом статусе.",
                show_alert=True,
            )

            return

        user = query.from_user

        username = (
            f"@{user.username}"
            if user.username
            else user.full_name
        )

        await query.edit_message_text(
            "⏳ Заявка отправлена.\n\n"
            "Квитанция передана "
            "администратору.\n"
            "Ожидайте проверки оплаты."
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💰 НОВАЯ ТРАНЗАКЦИЯ\n\n"
                f"🧾 ID: {transaction_id}\n"
                f"👤 {username}\n"
                f"🆔 ID пользователя: "
                f"{user.id}\n"
                f"💰 Сумма: "
                f"{transaction['price']} ₸\n"
                f"💎 Glyphs: "
                f"{transaction['glyphs']:,}\n\n"
                "Проверьте поступление денег "
                "в Kaspi."
            ).replace(",", " "),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Подтвердить оплату",
                        callback_data=(
                            "admin_confirm_"
                            f"{transaction_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Отклонить",
                        callback_data=(
                            "admin_reject_"
                            f"{transaction_id}"
                        ),
                    )
                ],
            ]),
        )

        return

    # =========================
    # ADMIN CONFIRM
    # =========================

    if data.startswith(
        "admin_confirm_"
    ):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )

            return

        transaction_id = data.replace(
            "admin_confirm_",
            "",
        )

        transactions = load_transactions()

        transaction = transactions.get(
            transaction_id
        )

        if not transaction:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        if transaction[
            "status"
        ] == "confirmed":

            await query.answer(
                "⚠️ Эта транзакция уже подтверждена.",
                show_alert=True,
            )

            return

        if transaction[
            "status"
        ] != "receipt_received":

            await query.answer(
                "❌ Нельзя подтвердить эту транзакцию.",
                show_alert=True,
            )

            return

        update_transaction(
            transaction_id,
            status="confirmed",
            confirmed_at=datetime.now().isoformat(),
        )

        await query.edit_message_text(
            "✅ ОПЛАТА ПОДТВЕРЖДЕНА\n\n"
            f"🧾 Транзакция: "
            f"{transaction_id}\n"
            f"👤 ID: "
            f"{transaction['user_id']}\n"
            f"💰 Сумма: "
            f"{transaction['price']} ₸\n"
            f"💎 Glyphs: "
            f"{transaction['glyphs']:,}\n"
            .replace(",", " "),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔗 Отправить ссылку",
                        callback_data=(
                            "admin_send_link_"
                            f"{transaction_id}"
                        ),
                    )
                ]
            ]),
        )

        await context.bot.send_message(
            chat_id=transaction[
                "user_id"
            ],
            text=(
                "✅ Оплата подтверждена!\n\n"
                f"🧾 Транзакция: "
                f"{transaction_id}\n"
                f"💰 Сумма: "
                f"{transaction['price']} ₸\n"
                f"💎 Glyphs: "
                f"{transaction['glyphs']:,}\n\n"
                "Оплата успешно проверена."
            ).replace(",", " "),
        )

        return

    # =========================
    # ADMIN SEND LINK
    # =========================

    if data.startswith(
        "admin_send_link_"
    ):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )

            return

        transaction_id = data.replace(
            "admin_send_link_",
            "",
        )

        transactions = load_transactions()

        transaction = transactions.get(
            transaction_id
        )

        if not transaction:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        if transaction["status"] != "confirmed":

            await query.answer(
                "❌ Сначала подтвердите оплату.",
                show_alert=True,
            )

            return

        # Сохраняем ИМЕННО эту транзакцию
        # для последующей отправки ссылки.
        context.user_data[
            "admin_sending_link"
        ] = True

        context.user_data[
            "admin_link_transaction_id"
        ] = transaction_id

        await query.message.reply_text(
            "🔗 Отправьте ссылку сейчас.\n\n"
            "Она будет отправлена пользователю:\n"
            f"🆔 {transaction['user_id']}\n\n"
            f"🧾 Транзакция: {transaction_id}"
        )

        return

    # =========================
    # ADMIN REJECT
    # =========================

    if data.startswith(
        "admin_reject_"
    ):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )

            return

        transaction_id = data.replace(
            "admin_reject_",
            "",
        )

        transactions = load_transactions()

        transaction = transactions.get(
            transaction_id
        )

        if not transaction:

            await query.answer(
                "❌ Транзакция не найдена.",
                show_alert=True,
            )

            return

        if transaction[
            "status"
        ] in (
            "confirmed",
            "rejected",
        ):

            await query.answer(
                "⚠️ Транзакция уже обработана.",
                show_alert=True,
            )

            return

        update_transaction(
            transaction_id,
            status="rejected",
        )

        await query.edit_message_text(
            "❌ ОПЛАТА ОТКЛОНЕНА\n\n"
            f"🧾 Транзакция: "
            f"{transaction_id}"
        )

        await context.bot.send_message(
            chat_id=transaction[
                "user_id"
            ],
            text=(
                "❌ Оплата отклонена.\n\n"
                f"🧾 Транзакция: "
                f"{transaction_id}\n\n"
                "Если вы считаете, что произошла "
                "ошибка, обратитесь к администратору."
            ),
        )

        return

    # =========================
    # PURCHASES
    # =========================

    if data == "purchases":

        user_id = query.from_user.id

        transactions = load_transactions()

        user_transactions = [
            transaction
            for transaction in transactions.values()
            if transaction[
                "user_id"
            ] == user_id
        ]

        user_transactions.sort(
            key=lambda x: x["created_at"],
            reverse=True,
        )

        if not user_transactions:

            text = (
                "📦 Мои покупки\n\n"
                "Покупок пока нет."
            )

        else:

            lines = [
                "📦 Мои покупки\n"
            ]

            for transaction in (
                user_transactions[:10]
            ):

                status = {
                    "waiting_receipt":
                        "⏳ Ожидает квитанцию",
                    "receipt_received":
                        "🔍 На проверке",
                    "confirmed":
                        "✅ Подтверждено",
                    "rejected":
                        "❌ Отклонено",
                }.get(
                    transaction["status"],
                    transaction["status"],
                )

                lines.append(
                    f"🧾 {transaction['id']}\n"
                    f"💰 {transaction['price']} ₸\n"
                    f"💎 "
                    f"{transaction['glyphs']:,} Glyphs\n"
                    f"{status}\n"
                )

            text = "\n".join(lines)

        await query.edit_message_text(
            text.replace(",", " "),
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
    # HELP
    # =========================

    if data == "help":

        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Выберите пакет или укажите "
            "свою сумму.\n\n"
            "Квитанцию необходимо отправлять "
            "именно как файл.\n\n"
            "После проверки оплаты "
            "администратором транзакция "
            "будет подтверждена.",
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
    # BACK
    # =========================

    if data == "back":

        context.user_data[
            "waiting_for_amount"
        ] = False

        context.user_data[
            "waiting_for_receipt"
        ] = False

        context.user_data[
            "admin_sending_link"
        ] = False

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
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
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
        return False

    text = update.message.text.strip()

    try:
        price = int(text)

    except ValueError:

        await update.message.reply_text(
            "❌ Введите сумму только цифрами.\n\n"
            "Например: 875"
        )

        return True

    if price < 1:

        await update.message.reply_text(
            "❌ Сумма должна быть больше 0 ₸."
        )

        return True

    if price > 1000000:

        await update.message.reply_text(
            "❌ Максимальная сумма — "
            "1 000 000 ₸."
        )

        return True

    context.user_data[
        "waiting_for_amount"
    ] = False

    glyphs = int(
        price * GLYPHS_PER_TENGE
    )

    glyphs_text = (
        f"{glyphs:,}"
        .replace(",", " ")
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Оплатить",
                callback_data=(
                    f"custompay_"
                    f"{price}_"
                    f"{glyphs}"
                ),
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
        f"💎 Вы получите: "
        f"{glyphs_text} Glyphs\n\n"
        "Нажмите «💳 Оплатить».",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )

    return True


# =========================
# CUSTOM PAYMENT
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
# ОТПРАВКА ССЫЛКИ ПОЛЬЗОВАТЕЛЮ
# =========================

async def admin_link_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not context.user_data.get(
        "admin_sending_link",
        False,
    ):
        return False

    transaction_id = context.user_data.get(
        "admin_link_transaction_id"
    )

    if not transaction_id:
        context.user_data[
            "admin_sending_link"
        ] = False

        await update.message.reply_text(
            "❌ Транзакция не найдена."
        )

        return True

    transactions = load_transactions()

    transaction = transactions.get(
        transaction_id
    )

    if not transaction:
        context.user_data[
            "admin_sending_link"
        ] = False

        await update.message.reply_text(
            "❌ Транзакция не найдена."
        )

        return True

    if transaction["status"] != "confirmed":
        context.user_data[
            "admin_sending_link"
        ] = False

        await update.message.reply_text(
            "❌ Эта транзакция ещё не подтверждена."
        )

        return True

    # Получаем текст администратора.
    # Если это ссылка — отправляем её как обычное
    # сообщение, Telegram сделает её кликабельной.
    link_text = update.message.text.strip()

    if not link_text:
        await update.message.reply_text(
            "❌ Отправьте ссылку текстовым сообщением."
        )

        return True

    target_user_id = int(
        transaction["user_id"]
    )

    try:

        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "🔗 Ваша ссылка:\n\n"
                f"{link_text}"
            ),
        )

    except Exception as error:

        await update.message.reply_text(
            "❌ Не удалось отправить ссылку "
            f"пользователю.\n\nОшибка: {error}"
        )

        return True

    context.user_data[
        "admin_sending_link"
    ] = False

    context.user_data[
        "admin_link_transaction_id"
    ] = None

    await update.message.reply_text(
        "✅ Ссылка отправлена!\n\n"
        f"🧾 Транзакция: {transaction_id}\n"
        f"🆔 Получатель: {target_user_id}"
    )

    return True


# =========================
# ТОЛЬКО ФАЙЛ КВИТАНЦИИ
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

    transaction_id = (
        context.user_data.get(
            "transaction_id"
        )
    )

    if not transaction_id:

        await update.message.reply_text(
            "❌ Транзакция не найдена."
        )

        return

    transactions = load_transactions()

    transaction = transactions.get(
        transaction_id
    )

    if not transaction:

        await update.message.reply_text(
            "❌ Транзакция не найдена."
        )

        return

    document = update.message.document

    if not document:

        await update.message.reply_text(
            "❌ Можно отправить только "
            "квитанцию как ФАЙЛ.\n\n"
            "Фото и текст не принимаются."
        )

        return

    user = update.effective_user

    if user.username:
        username = f"@{user.username}"
    else:
        username = user.full_name

    update_transaction(
        transaction_id,
        receipt_received=True,
        status="receipt_received",
    )

    context.user_data[
        "waiting_for_receipt"
    ] = False

    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "📎 НОВАЯ КВИТАНЦИЯ\n\n"
            f"🧾 Транзакция: "
            f"{transaction_id}\n"
            f"👤 {username}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Сумма: "
            f"{transaction['price']} ₸\n"
            f"💎 Glyphs: "
            f"{transaction['glyphs']:,}\n\n"
            "Проверьте оплату в Kaspi."
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
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================
# ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТА
# =========================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # 1. Сначала проверяем отправку ссылки админом.
    if await admin_link_handler(
        update,
        context,
    ):
        return

    # 2. Затем собственную сумму.
    if await custom_amount_handler(
        update,
        context,
    ):
        return

    # 3. Если пользователь ждёт квитанцию,
    # текст не принимается.
    if context.user_data.get(
        "waiting_for_receipt",
        False,
    ):

        await update.message.reply_text(
            "❌ Квитанция принимается "
            "ТОЛЬКО КАК ФАЙЛ.\n\n"
            "📎 Отправьте файл квитанции "
            "через Telegram как документ.\n\n"
            "Фото и текст не принимаются."
        )

        return


# =========================
# ФОТО ПРИ ОЖИДАНИИ КВИТАНЦИИ
# =========================

async def reject_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "waiting_for_receipt",
        False,
    ):
        return

    await update.message.reply_text(
        "❌ Квитанция принимается "
        "ТОЛЬКО КАК ФАЙЛ.\n\n"
        "📎 Отправьте файл квитанции "
        "через Telegram как документ.\n\n"
        "Фото не принимаются."
    )


# =========================
# MAIN
# =========================

async def run_bot():

    token = os.environ.get(
        "BOT_TOKEN"
    )

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

    # =========================
    # DOCUMENT — КВИТАНЦИЯ
    # =========================

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            receipt_handler,
        )
    )

    # =========================
    # TEXT
    #
    # Один обработчик правильно
    # распределяет:
    # - сумму;
    # - ссылку админа;
    # - текст при ожидании квитанции.
    # =========================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    # =========================
    # PHOTO
    # =========================

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            reject_photo,
        )
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling()

    try:

        while True:

            await asyncio.sleep(
                3600
            )

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
