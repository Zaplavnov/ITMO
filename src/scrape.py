from pathlib import Path
import json
from bs4 import BeautifulSoup

from .config import RAW_DIR, PROCESSED_DIR, DOCUMENTS_PATH, HTTP_PROXY
from .utils import fetch_url, clean_text

PROGRAM_URLS = [
    "https://abit.itmo.ru/program/master/ai",
    "https://abit.itmo.ru/program/master/ai_product",
]


def extract_readable_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text("\n")
    return clean_text(text)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 120) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    documents: list[dict] = []

    for url in PROGRAM_URLS:
        html = fetch_url(url, http_proxy=HTTP_PROXY)
        slug = url.rstrip("/").split("/")[-1]
        raw_path = RAW_DIR / f"{slug}.html"
        raw_path.write_text(html, encoding="utf-8")

        text = extract_readable_text(html)
        text_path = PROCESSED_DIR / f"{slug}.txt"
        text_path.write_text(text, encoding="utf-8")

        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            documents.append(
                {
                    "id": f"{slug}-{idx}",
                    "url": url,
                    "title": slug,
                    "text": chunk,
                }
            )

    DOCUMENTS_PATH.write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
