import os
import re
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from sheets import append_row

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))

# Синонимы для типа оплаты
CASH_WORDS = ["нал", "наличные", "наличка", "cash"]
CARD_WORDS = ["безнал", "карта", "картой", "перевод", "безналичные", "card"]


def parse_expense(text: str):
    """
    Парсит сообщение вида:
      -2000 электрика нал
      -1500 продукты безнал
      -500 такси картой

    Возвращает (сумма, категория, тип_оплаты) или None если не похоже на расход.
    """
    text = text.strip()

    # Ищем сумму — число со знаком минус (или без)
    amount_match = re.match(r"^[-−]?\s*(\d[\d\s]*)", text)
    if not amount_match:
        return None

    amount_str = amount_match.group(1).replace(" ", "")
    amount = f"-{amount_str}"  # всегда делаем отрицательным (расход)

    # Остаток текста после суммы
    rest = text[amount_match.end():].strip()
    if not rest:
        return None

    # Ищем тип оплаты в конце строки
    payment_type = "не указан"
    words = rest.split()

    for i, word in enumerate(reversed(words)):
        w = word.lower().strip(".,!?")
        if w in CASH_WORDS:
            payment_type = "нал"
            words = words[:len(words) - 1 - i] + words[len(words) - i:]
            words.pop(len(words) - 1 - i)
            break
        elif w in CARD_WORDS:
            payment_type = "безнал"
            words = words[:len(words) - 1 - i] + words[len(words) - i:]
            words.pop(len(words) - 1 - i)
            break

    # Всё что осталось — категория/описание
    category = " ".join(words).strip(" .,!?")
    if not category:
        category = "без категории"

    return amount, category, payment_type


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message:
        return

    if CHAT_ID != 0 and message.chat_id != CHAT_ID:
        return

    text = message.text or message.caption or ""
    if not text:
        return

    result = parse_expense(text)
    if result is None:
        return  # Не похоже на расход — просто игнорируем

    amount, category, payment_type = result

    # Дата и время сообщения
    date_str = message.date.strftime("%d.%m.%Y")

    # Имя отправителя
    if message.from_user:
        first = message.from_user.first_name or ""
        last = message.from_user.last_name or ""
        sender = f"{first} {last}".strip() or "неизвестно"
    else:
        sender = message.chat.title or "канал"

    row = [date_str, amount, category, payment_type, sender]

    try:
        append_row(row)
        logger.info(f"✅ Записан расход: {row}")

        # Подтверждение в чат
        await message.reply_text(
            f"✅ Записано!\n"
            f"💸 Сумма: {amount} ₽\n"
            f"📌 Категория: {category}\n"
            f"💳 Оплата: {payment_type}"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка записи: {e}")
        await message.reply_text("❌ Ошибка при записи в таблицу. Проверь настройки.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(
        filters.TEXT | filters.CAPTION,
        handle_message
    ))

    port = int(os.environ.get("PORT", 8080))
    webhook_url = os.environ.get("WEBHOOK_URL")

    if webhook_url:
        logger.info(f"🚀 Webhook: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/webhook",
            url_path="/webhook",
        )
    else:
        logger.info("🔄 Polling mode (локально)")
        app.run_polling()


if __name__ == "__main__":
    main()
