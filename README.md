## ITMO Admission Assistant Bot

Телеграм‑бот, который помогает абитуриентам магистратур ИТМО (AI и AI Product):
- отвечает на вопросы по содержимому страниц программ;
- выдаёт выдержки из учебных планов (retrieval по TF‑IDF);
- даёт рекомендации по выборным дисциплинам с учётом бэкграунда (/recommend);
- отфильтровывает нерелевантные вопросы (отвечает только по программам AI и AI Product).

Исходные страницы:
- https://abit.itmo.ru/program/master/ai
- https://abit.itmo.ru/program/master/ai_product

### Быстрый старт (Windows PowerShell)
1) Создать/активировать окружение и установить зависимости:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
```

2) Собрать данные (парсинг и индексация):
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_data.ps1
```

3) Настроить переменные окружения:
- Скопируйте `env.example` → `.env` и заполните:
  - `TELEGRAM_BOT_TOKEN` — токен вашего бота;
  - для локальной модели Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (по умолчанию `gemma3:1b`);
  - `USE_LLM=true|false` — включить/выключить генерацию ИИ (при `false` бот показывает сниппеты без LLM);
  - при необходимости корпоративного прокси: `HTTP_PROXY`.

4) Запуск бота:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_bot.ps1
```

### Использование
- Обычные вопросы по программам: задавайте свободным текстом (например, «какие треки есть в AI Product», «какие дисциплины по ML?»).
- Рекомендации по выборным дисциплинам с учётом бэкграунда:
```text
/recommend Я backend разработчик, хочу в AI Product
```
Бот определит намерение, учтёт бэкграунд (например: python, ml, data_science, product и т.д.) и вернёт релевантные фрагменты про выборные дисциплины.

### Как это работает
- `src/scrape.py` — парсит страницы программ, чистит текст, режет на чанки, сохраняет `documents.json`.
- `src/indexer.py` — строит TF‑IDF индекс (`tfidf_index.joblib`).
- `src/retriever.py` — быстрый поиск релевантных фрагментов по косинусной близости.
- `src/domain.py` — определение намерения, релевантности и бэкграунда.
- `src/recommender.py` — простые эвристики для рекомендаций выборных дисциплин.
- `src/bot.py` — Telegram‑бот, команды, обработчики.

### Замечания
- Бот осознанно отвечает только по учебным программам AI и AI Product (вопросы вне темы отсекаются).
- Для корпоративных сетей можно указать прокси в `.env` через `HTTP_PROXY`.

### Лицензия
MIT