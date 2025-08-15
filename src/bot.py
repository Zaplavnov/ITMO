import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from .config import TELEGRAM_BOT_TOKEN, LOG_LEVEL, OPENAI_API_KEY
from .retriever import Retriever
from .domain import is_relevant_question, is_recommendation_intent, extract_background_tags, detect_program_from_text
from .recommender import recommend_electives
from .llm import generate_rag_answer

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу разобраться с магистратурами ИТМО (AI и AI Product). Задай вопрос или используй /recommend."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Задай вопрос по программам: учебный план, дисциплины, треки. Для рекомендаций по выборным предметам используй /recommend и опиши свой бэкграунд."
    )


async def cmd_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/recommend", "").strip()
    prog = detect_program_from_text(text) or "ai"
    tags = extract_background_tags(text)
    recs = recommend_electives(tags, prog)
    if not recs:
        await update.message.reply_text("Пока не нашёл релевантные рекомендации для выборных дисциплин.")
        return
    reply = "\n\n".join([f"• {r}" for r in recs])
    await update.message.reply_text(reply)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = (update.message.text or "").strip()
    if not query:
        await update.message.reply_text("Пожалуйста, введите вопрос.")
        return
    retriever: Retriever = context.application.bot_data.get("retriever")

    if not is_relevant_question(query, retriever):
        await update.message.reply_text("Я отвечаю только на вопросы по обучению на магистратурах AI и AI Product в ИТМО.")
        return

    if is_recommendation_intent(query):
        await update.message.reply_text("Похоже, нужны рекомендации по выборным. Используй команду /recommend и опиши свой бэкграунд и программу.")
        return

    try:
        results = retriever.search(query, top_k=6)
        if not results:
            await update.message.reply_text("Не нашёл релевантную информацию в учебных планах.")
            return

        # If LLM available – generate RAG answer; otherwise fallback to snippets
        if OPENAI_API_KEY:
            chunks = [r.text for r in results]
            answer = generate_rag_answer(query, chunks)
            # Append sources (unique urls)
            urls = []
            for r in results:
                if r.url not in urls:
                    urls.append(r.url)
            if urls:
                answer += "\n\nИсточники:\n" + "\n".join([f"- {u}" for u in urls])
            await update.message.reply_text(answer)
            return

        # Fallback: show snippets
        lines = []
        for r in results:
            lines.append(f"• {r.title} ({r.url})\n{r.text[:600]}…")
        await update.message.reply_text("\n\n".join(lines))
    except Exception:
        logger.exception("Failed to answer")
        await update.message.reply_text("Произошла ошибка при обработке запроса.")


def build_app(token: str) -> Application:
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("recommend", cmd_recommend))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    return app


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Добавьте его в .env")

    retr = Retriever()
    app = build_app(TELEGRAM_BOT_TOKEN)
    app.bot_data["retriever"] = retr

    app.run_polling()


if __name__ == "__main__":
    main()
