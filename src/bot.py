import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from .config import TELEGRAM_BOT_TOKEN, LOG_LEVEL
from .retriever import Retriever

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу разобраться с магистратурами ИТМО (AI и AI Product). Задай вопрос."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Задай вопрос по программам: учебный план, дисциплины, треки, выбор по бэкграунду."
    )


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = (update.message.text or "").strip()
    if not query:
        await update.message.reply_text("Пожалуйста, введите вопрос.")
        return
    try:
        retriever: Retriever = context.application.bot_data.get("retriever")
        results = retriever.search(query, top_k=4)
        if not results:
            await update.message.reply_text("Не нашёл релевантную информацию в учебных планах.")
            return
        lines = []
        for r in results:
            lines.append(f"• {r.title} ({r.url})\n{r.text[:600]}…")
        await update.message.reply_text("\n\n".join(lines))
    except Exception as exc:
        logger.exception("Failed to answer: %s", exc)
        await update.message.reply_text("Произошла ошибка при обработке запроса.")


def build_app(token: str) -> Application:
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    return app


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Добавьте его в .env")
    from .retriever import Retriever

    retr = Retriever()
    app = build_app(TELEGRAM_BOT_TOKEN)
    app.bot_data["retriever"] = retr

    app.run_polling()


if __name__ == "__main__":
    main()
