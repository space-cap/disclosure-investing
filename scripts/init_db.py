from app.config import load_settings
from app.database import init_db


if __name__ == "__main__":
    settings = load_settings()
    init_db(settings.database_path)
    print(f"Initialized database: {settings.database_path}")

