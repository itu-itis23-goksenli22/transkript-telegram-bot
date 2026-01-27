import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from modules.instagram import extract_instagram_url, download_video, cleanup
from modules.gemini_service import process_video, generate_thumbnail

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

    # URL'yi context'e kaydet
    context.user_data['instagram_url'] = instagram_url

    # Seçenek butonları göster
    keyboard = [
        [
            InlineKeyboardButton("📝 Transkript", callback_data="action_transcript"),
            InlineKeyboardButton("🖼️ Thumbnail", callback_data="action_thumbnail"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Ne yapmak istiyorsun?",
        reply_markup=reply_markup
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buton tıklamalarını işler."""
    query = update.callback_query
    await query.answer()

    action = query.data
    instagram_url = context.user_data.get('instagram_url')

    if not instagram_url:
        await query.edit_message_text("❌ Link bulunamadı. Lütfen tekrar bir Instagram linki gönderin.")
        return

    if action == "action_transcript":
        await process_transcript(query, context, instagram_url)
    elif action == "action_thumbnail":
        await process_thumbnail_request(query, context, instagram_url)


async def process_transcript(query, context: ContextTypes.DEFAULT_TYPE, instagram_url: str):
    """Transkript işlemini gerçekleştirir."""
    await query.edit_message_text("⏳ Video indiriliyor...")
    temp_dir = None

    try:
        # Video indir
        video_path, temp_dir = await download_video(instagram_url)

        # Durum güncelle
        await query.edit_message_text("🎯 Transkript çıkarılıyor ve çeviriler hazırlanıyor...")

        # Transkript ve çeviri
        result = await process_video(video_path)

        # Sonuç mesajını formatla
        if result['original'] == "Bu videoda konuşma bulunamadı.":
            await query.edit_message_text("❌ Bu videoda konuşma bulunamadı.")
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
            await query.edit_message_text("✅ İşlem tamamlandı!")

            chat_id = query.message.chat_id
            await context.bot.send_message(chat_id, f"📝 **Orijinal Transkript:**\n{result['original']}")
            await context.bot.send_message(chat_id, f"🇹🇷 **Türkçe:**\n{result['turkish']}")
            await context.bot.send_message(chat_id, f"🇬🇧 **English:**\n{result['english']}")
        else:
            await query.edit_message_text(response_text)

    except Exception as e:
        logger.error(f"Hata: {str(e)}")
        error_message = "❌ Bir hata oluştu.\n\n"
        error_str = str(e).lower()

        if "private" in error_str:
            error_message += "Bu video gizli, erişilemiyor."
        elif "login required" in error_str or "rate-limit" in error_str or "not available" in error_str:
            error_message += "Bu videoya erişilemiyor. Muhtemel sebepler:\n"
            error_message += "• Video gizli/private olabilir\n"
            error_message += "• Instagram geçici olarak engellemiş olabilir\n"
            error_message += "• Farklı bir video deneyin"
        elif "not found" in error_str:
            error_message += "Video bulunamadı."
        else:
            error_message += "Lütfen tekrar deneyin."

        await query.edit_message_text(error_message)

    finally:
        # Temizlik
        if temp_dir:
            cleanup(temp_dir)


async def process_thumbnail_request(query, context: ContextTypes.DEFAULT_TYPE, instagram_url: str):
    """Thumbnail oluşturma işlemini gerçekleştirir."""
    await query.edit_message_text("⏳ Video indiriliyor...")
    temp_dir = None

    try:
        # Video indir
        video_path, temp_dir = await download_video(instagram_url)

        # Durum güncelle
        await query.edit_message_text("🎨 Thumbnail oluşturuluyor... (Bu biraz zaman alabilir)")

        # Thumbnail oluştur
        image_bytes, hook_text = await generate_thumbnail(video_path)

        # Görseli gönder
        chat_id = query.message.chat_id
        await query.edit_message_text("✅ Thumbnail hazır!")

        # Bytes'ı dosya olarak gönder
        image_file = io.BytesIO(image_bytes)
        image_file.name = "thumbnail.png"

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_file,
            caption=f"🖼️ Instagram Reels Thumbnail\n\n📌 Hook: **{hook_text}**"
        )

    except Exception as e:
        logger.error(f"Thumbnail hatası: {str(e)}")
        error_message = "❌ Thumbnail oluşturulurken hata oluştu.\n\n"
        error_str = str(e).lower()

        if "private" in error_str:
            error_message += "Bu video gizli, erişilemiyor."
        elif "image" in error_str or "görsel" in error_str:
            error_message += "Görsel oluşturulamadı. Lütfen tekrar deneyin."
        else:
            error_message += "Lütfen tekrar deneyin."

        await query.edit_message_text(error_message)

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
    application.add_handler(CallbackQueryHandler(handle_callback))

    return application
