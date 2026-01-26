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

    # Railway/Cloud Session Restore
    import os
    import base64
    from config import INSTAGRAM_SESSION_DATA

    session_path = os.path.join(os.path.dirname(__file__), 'instagram_session')
    
    if INSTAGRAM_SESSION_DATA and not os.path.exists(session_path):
        try:
            logger.info("Environment variable'dan session yükleniyor...")
            with open(session_path, 'wb') as f:
                f.write(base64.b64decode(INSTAGRAM_SESSION_DATA))
            logger.info("Session oluşturuldu.")
        except Exception as e:
            logger.error(f"Session oluşturulurken hata: {e}")

    # Bot oluştur
    application = create_bot()

    # Bot'u çalıştır
    logger.info("Bot çalışıyor. Durdurmak için Ctrl+C")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
