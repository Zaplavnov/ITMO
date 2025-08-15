from __future__ import annotations
from typing import List

import httpx
from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL


def _build_system_prompt() -> str:
    return (
        "Ты ассистент ИТМО. Отвечай строго по учебным программам AI и AI Product. "
        "Используй переданный контекст. Если нужной информации нет в контексте — скажи, что в материалах программ этого нет. "
        "Отвечай кратко и по-русски; при необходимости перечисляй пункты. Не выдумывай факты."
    )


def _format_context(chunks: List[str], max_total_chars: int = 8000) -> str:
    taken: List[str] = []
    total = 0
    for ch in chunks:
        if total >= max_total_chars:
            break
        ch = ch.strip()
        if not ch:
            continue
        budget = max_total_chars - total
        taken_chunk = ch[: budget]
        taken.append(taken_chunk)
        total += len(taken_chunk)
    sep = "\n\n---\n\n"
    return sep.join(taken)


def _generate_openai(question: str, context_chunks: List[str]) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {
            "role": "user",
            "content": (
                "Контекст (фрагменты с учебных страниц):\n" + _format_context(context_chunks) +
                "\n\nВопрос: " + question +
                "\n\nОтветь по контексту. Если ответа в контексте нет — так и скажи."
            ),
        },
    ]
    resp = client.chat.completions.create(
        model=OPENAI_MODEL or "gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=600,
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_ollama(question: str, context_chunks: List[str]) -> str:
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    prompt = (
        _build_system_prompt()
        + "\n\nКонтекст (фрагменты с учебных страниц):\n"
        + _format_context(context_chunks)
        + "\n\nВопрос: "
        + question
        + "\n\nОтветь по контексту. Если ответа в контексте нет — так и скажи."
    )
    with httpx.Client(timeout=60) as client:
        r = client.post(url, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "options": {"temperature": 0.2}
        })
        r.raise_for_status()
        data = r.json()
        # Ollama /api/generate streams by default when using streaming clients; here it returns full text
        # Some builds return {response: str}
        if isinstance(data, dict) and "response" in data:
            return (data["response"] or "").strip()
        return str(data)


def generate_rag_answer(question: str, context_chunks: List[str]) -> str:
    if OPENAI_API_KEY:
        return _generate_openai(question, context_chunks)
    return _generate_ollama(question, context_chunks)
