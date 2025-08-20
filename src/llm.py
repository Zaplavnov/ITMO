from __future__ import annotations
from typing import List, Optional
import logging
import psutil
import time

import httpx

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, USE_LLM

logger = logging.getLogger(__name__)


def _check_system_resources() -> bool:
    """Check if system has enough resources for LLM models"""
    try:
        # For 1B models, need at least 1.5GB free RAM (more realistic)
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        logger.info(f"Available RAM: {available_gb:.1f} GB")
        
        if available_gb < 1.5:
            logger.warning(f"Insufficient RAM: {available_gb:.1f} GB available, need at least 1.5 GB")
            return False
        return True
    except Exception as e:
        logger.warning(f"Could not check system resources: {e}")
        return True  # Assume OK if we can't check


def _get_available_models() -> List[str]:
    """Get list of available Ollama models"""
    try:
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        with httpx.Client(timeout=10) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.info(f"Available Ollama models: {models}")
            return models
    except Exception as e:
        logger.error(f"Failed to get Ollama models: {e}")
        return []


def _check_ollama_model(model_name: str) -> bool:
    """Check if specific model is available"""
    models = _get_available_models()
    return model_name in models


def _pull_ollama_model(model_name: str, timeout_seconds: int = 300) -> bool:
    """Attempt to pull model via Ollama HTTP API and wait until available."""
    pull_url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/pull"
    try:
        with httpx.Client(timeout=60) as client:
            # Start pull (non-streaming to simplify)
            client.post(pull_url, json={"name": model_name, "stream": False})
    except Exception as e:
        logger.warning(f"Failed to initiate pull for {model_name}: {e}")
        # Continue to polling anyway in case pull started

    # Poll availability
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _check_ollama_model(model_name):
            logger.info(f"Model became available after pull: {model_name}")
            return True
        time.sleep(2.0)
    logger.error(f"Timed out waiting for model to pull: {model_name}")
    return False


def _find_working_model() -> Optional[str]:
    """Find a working model, prioritizing lighter models"""
    if not _check_system_resources():
        logger.warning("System resources insufficient for LLM models")
        return None
    
    primary_model = OLLAMA_MODEL
    # Order by resource requirements (lightest models first)
    fallback_models = ["gemma3:1b", "qwen3:4b", "llama3.1:8b"]
    
    # Try primary model first
    if _check_ollama_model(primary_model):
        return primary_model
    # Try to pull primary automatically if missing (do NOT auto-pull heavier fallbacks)
    logger.info(f"Primary model {primary_model} not found. Attempting to pull it via Ollama API...")
    if _pull_ollama_model(primary_model):
        return primary_model
    
    # Try fallbacks in order of preference
    for model in fallback_models:
        if model != primary_model and _check_ollama_model(model):
            logger.info(f"Primary model {primary_model} not available, using fallback: {model}")
            return model
    
    logger.error(f"No working models found. Available: {_get_available_models()}")
    return None


def _build_system_prompt() -> str:
    return "Ты ассистент ИТМО. Отвечай кратко по-русски."


def _format_context(chunks: List[str], max_total_chars: int = 1500) -> str:
    """Format context with reduced size for 1B models"""
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
    result = sep.join(taken)
    logger.info(f"Context formatted: {len(result)} chars, {len(taken)} chunks")
    return result


def _generate_ollama(question: str, context_chunks: List[str]) -> str:
    # Find working model
    working_model = _find_working_model()
    if not working_model:
        raise RuntimeError("No working Ollama models found")
    
    logger.info(f"Using Ollama model: {working_model}")

    # Build compact context to stay within safe limits for 1B models
    context_text = _format_context(context_chunks, max_total_chars=1000)

    # Compose user prompt with explicit instruction to use ONLY the provided context
    user_prompt = (
        "Контекст (фрагменты с учебных страниц):\n" + context_text +
        "\n\nВопрос: " + question +
        "\n\nОтветь кратко по-русски строго по контексту. Если ответа нет в контексте — так и скажи."
    )
    
    # Try chat completion API first
    chat_url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    logger.info(f"Trying chat API: {chat_url}")
    
    with httpx.Client(timeout=60) as client:
        try:
            r = client.post(chat_url, json={
                "model": working_model,
                "messages": [
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            })
            logger.info(f"Chat API response status: {r.status_code}")
            
            if r.status_code != 200:
                logger.error(f"Chat API error: {r.text}")
                raise RuntimeError(f"Chat API returned {r.status_code}")
                
            data = r.json()
            logger.info(f"Chat API response data: {data}")
            
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                logger.warning(f"Unexpected chat API response format: {data}")
                raise RuntimeError("Invalid chat API response format")
                
        except Exception as e:
            logger.warning(f"Chat API failed: {e}, trying generate API")
        
        # Fallback to generate API with simple prompt
        generate_url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        logger.info(f"Trying generate API: {generate_url}")
        
        try:
            r = client.post(generate_url, json={
                "model": working_model,
                "prompt": user_prompt + "\n\nКраткий ответ:",
                "stream": False
            })
            logger.info(f"Generate API response status: {r.status_code}")
            
            if r.status_code != 200:
                logger.error(f"Generate API error: {r.text}")
                raise RuntimeError(f"Generate API returned {r.status_code}")
                
            data = r.json()
            logger.info(f"Generate API response data: {data}")
            
            return (data.get("response") or "").strip()
            
        except Exception as e:
            logger.error(f"Generate API also failed: {e}")
            raise


def generate_rag_answer(question: str, context_chunks: List[str]) -> str:
    if not USE_LLM:
        raise RuntimeError("LLM disabled")
    logger.info("Using Ollama API")
    return _generate_ollama(question, context_chunks)
