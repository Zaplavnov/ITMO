import re
import time
from typing import Optional
import requests


def fetch_url(url: str, http_proxy: Optional[str] = None, timeout: int = 30) -> str:
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }
    proxies = {"http": http_proxy, "https": http_proxy} if http_proxy else None
    for attempt in range(3):
        try:
            response = session.get(url, headers=headers, proxies=proxies, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5)
    raise RuntimeError("Unreachable")


def clean_text(text: str) -> str:
    # Normalize whitespace and remove very short lines
    text = text.replace('\r', '\n')
    text = re.sub(r"\n+", "\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if len(ln) >= 2]
    # Collapse multiple spaces
    lines = [re.sub(r"\s+", " ", ln) for ln in lines]
    # Remove duplicates preserving order
    seen = set()
    unique_lines = []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            unique_lines.append(ln)
    return "\n".join(unique_lines).strip()
