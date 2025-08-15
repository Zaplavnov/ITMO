from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = SRC_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_PATH = PROCESSED_DIR / "tfidf_index.joblib"
DOCUMENTS_PATH = PROCESSED_DIR / "documents.json"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip()

for directory in (DATA_DIR, RAW_DIR, PROCESSED_DIR):
    directory.mkdir(parents=True, exist_ok=True)
