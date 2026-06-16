from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    dart_api_key: str
    openai_api_key: str
    openai_model: str
    database_path: Path


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip(),
        database_path=Path(os.getenv("DATABASE_PATH", "data/disclosures.db")),
    )

