import os
import re
import logging
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from sheets import append_row

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))

CASH_WORDS = ["нал", "наличные", "наличка", "cash"]
CARD_WORDS = ["безнал", "карта", "картой", "перевод", "безналичные", "card"]


def parse_transaction(text: str):
    """
    Формат: [+/-] СУММА ОПИСАНИЕ нал/безнал
    Примеры:
      -2000 электрика нал
      +1500 принял от назара безнал
      -800 такси картой
    """
    text = text.strip()

    # Знак
    if text.startswith("+"):
        sign = "+"
        text = text[1:].strip()
        tx_type = "приход"
    elif text.startswith("-") or text.startswith("−"):
        sign = "-"
        text = text[1:].strip()
        tx_type = "расход"
    else:
        sign = "-"
        tx_type = "расход"

    # Сумма в начале
    amount_match = re.match(r"^(\d[\d\s]*\.?\d*)", text)
    if not amount_match:
        return None

    amount_str = amount_match.group(1).replace(" ", "")
    try:
        float(amount_str)
    except ValueError:
        return None

    amount = f"{sign}{amount_str}"
    rest = text[amount_match.end():].strip()

    if not rest:
        return None

    # Тип оплаты — ищем ПОСЛЕДНЕЕ слово
    words = rest.split()
    payment_type = "не указан"

    last_word = words[-1].lower().strip(".,!?")
    if last_word in CASH_WORDS:
        payment_type = "нал"
        words = words[:-1]
    elif last_word in CARD_WORDS:
        payment_type = "безнал"
        words = words[:-1]

    # Всё остальное — категория
    category = " ".join(words).strip()
    if not category:
        category = "без категории"

    return amount, category, payment_type, tx_type


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message:
        return

    if CHAT_ID != 0 and message.chat_id != CHAT_ID:
        return

    text = message.text or message.caption or ""
    if not text:
        return

    result = parse_transaction(text)
    if result is None:
        return

    amount, category, payment_type, tx_type = result
    date_str = message.date.strftime("%d.%m.%Y")

    if message.from_user:
        first = message.from_user.first_name or ""
        last = message.from_user.last_name or ""
        sender = f"{first} {last}".strip() or "неизвестно"
    else:
        sender = message.chat.title or "канал"

    row = [date_str, amount, category, payment_type, tx_type, sender]

    try:
        append_row(row)
        logger.info(f"✅ Записано: {row}")
        # Ставим реакцию ✅ на сообщение
        await message.set_reaction(ReactionTypeEmoji("✅"))
    except Exception as e:
        logger.error(f"❌ Ошибка записи: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_message))

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
        logger.info("🔄 Polling mode")
        app.run_polling()


if __name__ == "__main__":
    main()
