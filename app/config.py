import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from the base directory
load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_NAME: str = "PocketSmart AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Your Smart Budget & Recommendation Assistant for Home, Party, and Jewelry Planning"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "pocketsmart-super-secret-key-change-in-production-2026")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'pocketsmart.db'}")
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")


settings = Settings()
