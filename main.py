import logging
from modules.telegram_bot import create_bot

# Logging yapılandırması
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Bot'u başlatır."""
    logger.info("Bot başlatılıyor...")

    # Bot oluştur
    application = create_bot()

    # Bot'u çalıştır
    logger.info("Bot çalışıyor. Durdurmak için Ctrl+C")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
