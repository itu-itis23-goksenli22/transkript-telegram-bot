import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from modules.instagram import extract_instagram_url, download_video, cleanup
from modules.gemini_service import process_video

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatma komutu."""
    welcome_message = """Merhaba! Ben Instagram Video Transkript Botuyum.

Bana bir Instagram video/reel linki gönder, sana:
- Orijinal transkripti
- Türkçe çevirisini
- İngilizce çevirisini

göndereceğim!

Örnek link formatları:
- https://www.instagram.com/reel/ABC123/
- https://www.instagram.com/p/XYZ789/"""

    await update.message.reply_text(welcome_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen mesajları işler."""
    text = update.message.text

    # Instagram URL'si var mı kontrol et
    instagram_url = extract_instagram_url(text)

    if not instagram_url:
        await update.message.reply_text(
            "Bu geçerli bir Instagram linki değil.\n\n"
            "Lütfen şu formatlarda bir link gönderin:\n"
            "- instagram.com/reel/...\n"
            "- instagram.com/p/..."
        )
        return

    # İşlem başlıyor
    status_message = await update.message.reply_text("⏳ Video indiriliyor...")
    temp_dir = None

    try:
        # Video indir
        video_path, temp_dir = await download_video(instagram_url)

        # Durum güncelle
        await status_message.edit_text("🎯 Transkript çıkarılıyor...")

        # Transkript ve çeviri
        await status_message.edit_text("🎯 Transkript çıkarılıyor ve çeviriler hazırlanıyor...")
        result = await process_video(video_path)

        # Sonuç mesajını formatla
        if result['original'] == "Bu videoda konuşma bulunamadı.":
            await status_message.edit_text("❌ Bu videoda konuşma bulunamadı.")
            return

        response_text = f"""✅ İşlem tamamlandı!

📝 **Orijinal Transkript:**
{result['original']}

🇹🇷 **Türkçe:**
{result['turkish']}

🇬🇧 **English:**
{result['english']}"""

        # Mesaj çok uzunsa parçala
        if len(response_text) > 4000:
            await status_message.edit_text("✅ İşlem tamamlandı!")

            await update.message.reply_text(f"📝 **Orijinal Transkript:**\n{result['original']}")
            await update.message.reply_text(f"🇹🇷 **Türkçe:**\n{result['turkish']}")
            await update.message.reply_text(f"🇬🇧 **English:**\n{result['english']}")
        else:
            await status_message.edit_text(response_text)

    except Exception as e:
        logger.error(f"Hata: {str(e)}")
        error_message = "❌ Bir hata oluştu.\n\n"

        if "Private" in str(e) or "private" in str(e):
            error_message += "Bu video gizli, erişilemiyor."
        elif "not found" in str(e).lower():
            error_message += "Video bulunamadı."
        else:
            error_message += "Lütfen tekrar deneyin."

        await status_message.edit_text(error_message)

    finally:
        # Temizlik
        if temp_dir:
            cleanup(temp_dir)


def create_bot() -> Application:
    """Telegram bot uygulamasını oluşturur."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handler'ları ekle
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application
