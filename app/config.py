import os
from dotenv import load_dotenv
import secrets

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for Wardrobe Manager application"""

    # App Configuration
    APP_NAME: str = os.getenv("APP_NAME", "Wardrobe Manager")
    APP_VERSION: str = os.getenv("APP_VERSION", "alpha")

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 24 * 60))

    # Server Configuration
    HOST_URL: str = os.getenv("HOST_URL", "127.0.0.1")
    HOST_PORT: int = int(os.getenv("HOST_PORT", "3000"))

    # Database Configuration (for future use)
    DATABASE_URL: str = os.getenv("DATABASE_URL", None)

    # CORS Configuration (for future use)
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    # Names of categories
    # If you want to group some categories under the same display name
    CATEGORY_NAMES: dict = {
        "obuv": "Обувь",
        "plata": "Платья",
        "jeans": "Джинсы",
        "bruki": "Брюки",
        "ankle-boots": "Ботильоны",
        "cardigans-2": "Кардиганы",
        "sweaters": "Свитеры",
        "verhnaa-odezda-sale": "Верхняя одежда",
        "ubki": "Юбки",
        "t-shirts2": "Футболки",
        "sneakers": "Кроссовки",
        "sweatshirts2": "Свитшоты",
        "longsleevetop": "Лонгсливы",
        "sweatshirts": "Свитшоты",
        "top": "Топы",
        "mules": "Мюли",
        "aksessuary": "Аксессуары",
        "zakety": "Пиджаки",
        "shirts": "Рубашки",
        "t-shirts": "Футболки",
        "bags": "Сумки",
        "verhnaa-odezda": "Верхняя одежда",
        "boots": "Ботинки",
        "sapki": "Головные уборы"
    }




# Create global config instance
config = Config()