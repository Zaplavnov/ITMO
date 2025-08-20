import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from .config import TELEGRAM_BOT_TOKEN, LOG_LEVEL, USE_LLM, OLLAMA_MODEL, HTTP_PROXY
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


def _format_snippets_fallback(results) -> str:
    """Format search results into readable snippets"""
    lines = []
    for r in results:
        # Clean and truncate text
        text = r.text.strip()
        if len(text) > 300:
            text = text[:300] + "..."
        
        # Add source info
        source = f"📚 {r.title.replace('_', ' ').title()}"
        lines.append(f"{source}\n{text}\n")
    
    return "\n".join(lines)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = (update.message.text or "").strip()
    if not query:
        await update.message.reply_text("Пожалуйста, введите вопрос.")
        return
    
    logger.info(f"Processing question: {query}")
    retriever: Retriever = context.application.bot_data.get("retriever")

    if not is_relevant_question(query, retriever):
        logger.info("Question not relevant to ITMO programs")
        await update.message.reply_text("Я отвечаю только на вопросы по обучению на магистратурах AI и AI Product в ИТМО.")
        return

    if is_recommendation_intent(query):
        logger.info("Recommendation intent detected")
        await update.message.reply_text("Похоже, нужны рекомендации по выборным. Используй команду /recommend и опиши свой бэкграунд и программу.")
        return

    try:
        logger.info("Searching for relevant information")
        results = retriever.search(query, top_k=4)
        if not results:
            logger.warning("No search results found")
            await update.message.reply_text("Не нашёл релевантную информацию в учебных планах.")
            return

        logger.info(f"Found {len(results)} search results")
        
        # Try LLM if enabled
        if USE_LLM:
            logger.info("LLM is enabled, attempting generation")
            
            # Notify user that model is processing
            processing_msg = await update.message.reply_text("🤖 ИИ-модель анализирует ваш вопрос и найденную информацию...")
            
            try:
                chunks = [r.text for r in results]
                logger.info(f"Preparing {len(chunks)} chunks for LLM")
                
                answer = generate_rag_answer(query, chunks)
                logger.info(f"LLM generated answer: {len(answer)} chars")
                
                # Append sources
                urls = list(set(r.url for r in results))
                if urls:
                    answer += "\n\n📖 Источники:\n" + "\n".join([f"• {u}" for u in urls])
                
                # Delete processing message and send answer
                await processing_msg.delete()
                await update.message.reply_text(answer)
                logger.info("Successfully sent LLM answer")
                return
                
            except Exception as e:
                logger.error(f"LLM generation failed: {e}", exc_info=True)
                logger.warning("Falling back to snippets due to LLM failure")
                
                # Update processing message to show fallback (ignore network errors)
                try:
                    await processing_msg.edit_text("🤖 ИИ-модель временно недоступна. Показываю найденную информацию:")
                except Exception as edit_err:
                    logger.warning(f"Failed to edit processing message: {edit_err}")

        # Fallback: show formatted snippets
        logger.info("Using fallback snippets")
        formatted = _format_snippets_fallback(results)
        await update.message.reply_text(formatted)
        logger.info("Successfully sent fallback snippets")
        
    except Exception as e:
        logger.exception(f"Failed to process question: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса.")


def build_app(token: str) -> Application:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Configure Telegram HTTP client with timeouts and optional proxy
    request = HTTPXRequest(
        proxy_url=HTTP_PROXY or None,
        connect_timeout=15.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=5.0,
    )
    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("recommend", cmd_recommend))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    return app


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Добавьте его в .env")

    logger.info("Starting ITMO bot")
    logger.info(f"USE_LLM: {USE_LLM}")
    if USE_LLM:
        logger.info(f"Using Ollama model: {OLLAMA_MODEL}")
    
    retr = Retriever()
    app = build_app(TELEGRAM_BOT_TOKEN)
    app.bot_data["retriever"] = retr

    app.run_polling()


if __name__ == "__main__":
    main()
