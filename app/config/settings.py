import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "Payment Gateway Simulator"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str = os.getenv("DATABASE_URL")

    IDEMPOTENCY_KEY_EXPIRY_HOURS: int = 24
    MAX_WEBHOOK_ATTEMPTS: int = 5


settings = Settings()