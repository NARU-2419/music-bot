import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from googleapiclient.discovery import build
from config import BOT_TOKEN, YOUTUBE_API_KEY

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure the 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Path to cookies.txt
COOKIES_PATH = "cookies.txt"

# YouTube Bot Functions
def search_youtube(query):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=1)
    response = request.execute()

    if "items" in response and len(response["items"]) > 0:
        video_id = response["items"][0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def download_video(url):
    ydl_opts = {
        "format": "best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "cookiefile": COOKIES_PATH,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        return None


def download_audio(url):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "cookiefile": COOKIES_PATH,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
        ],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        return None


async def delete_intermediate_messages(context: CallbackContext, messages):
    """Helper function to delete intermediate messages."""
    for msg in messages:
        try:
            await msg.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🎉 **Welcome to the YouTube Bot!** 🎉\n\n"
        "Here’s what I can do for you:\n"
        "📹 `/video <name>` - Download a YouTube video\n"
        "🎵 `/audio <name>` - Download YouTube audio\n"
        "🔗 `/link <YouTube URL>` - Download directly (video/audio)\n\n"
        "Enjoy! 🚀",
        parse_mode="Markdown",
    )


async def video(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("❌ **Usage:** `/video <video name>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    messages_to_delete = []  # Track intermediate messages
    msg = await update.message.reply_text("🔍 **Searching for your video...**", parse_mode="Markdown")
    messages_to_delete.append(msg)

    url = search_youtube(query)
    if not url:
        final_msg = await msg.edit_text("❌ **No results found. Try again with a different query.**", parse_mode="Markdown")
        messages_to_delete.append(final_msg)
        await delete_intermediate_messages(context, messages_to_delete)
        return

    downloading_msg = await msg.edit_text("📥 **Downloading your video...**", parse_mode="Markdown")
    messages_to_delete.append(downloading_msg)

    file_path = download_video(url)
    if file_path:
        sending_msg = await msg.edit_text("✅ **Video downloaded! Sending it to you now...**", parse_mode="Markdown")
        messages_to_delete.append(sending_msg)
        await update.message.reply_video(video=open(file_path, "rb"))
        os.remove(file_path)
        await delete_intermediate_messages(context, messages_to_delete)
    else:
        error_msg = await msg.edit_text("❌ **Failed to download the video. Please try again.**", parse_mode="Markdown")
        messages_to_delete.append(error_msg)
        await delete_intermediate_messages(context, messages_to_delete)


async def audio(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("❌ **Usage:** `/audio <song name>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    messages_to_delete = []  # Track intermediate messages
    msg = await update.message.reply_text("🔍 **Searching for your audio...**", parse_mode="Markdown")
    messages_to_delete.append(msg)

    url = search_youtube(query)
    if not url:
        final_msg = await msg.edit_text("❌ **No results found. Try again with a different query.**", parse_mode="Markdown")
        messages_to_delete.append(final_msg)
        await delete_intermediate_messages(context, messages_to_delete)
        return

    downloading_msg = await msg.edit_text("📥 **Downloading your audio...**", parse_mode="Markdown")
    messages_to_delete.append(downloading_msg)

    file_path = download_audio(url)
    if file_path:
        sending_msg = await msg.edit_text("✅ **Audio downloaded! Sending it to you now...**", parse_mode="Markdown")
        messages_to_delete.append(sending_msg)
        await update.message.reply_audio(audio=open(file_path, "rb"))
        os.remove(file_path)
        await delete_intermediate_messages(context, messages_to_delete)
    else:
        error_msg = await msg.edit_text("❌ **Failed to download the audio. Please try again.**", parse_mode="Markdown")
        messages_to_delete.append(error_msg)
        await delete_intermediate_messages(context, messages_to_delete)


async def link(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("❌ **Usage:** `/link <YouTube URL>`", parse_mode="Markdown")
        return

    url = context.args[0]
    await update.message.reply_text(
        "🔗 **You provided a link!** What do you want to do?\n\n"
        "Choose an option below 👇:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Download Audio", callback_data=f"audio|{url}"),
             InlineKeyboardButton("📹 Download Video", callback_data=f"video|{url}")],
        ]),
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action, url = query.data.split("|", 1)
    msg = await query.message.reply_text("📥 **Processing your request...**", parse_mode="Markdown")

    if action == "audio":
        file_path = download_audio(url)
        if file_path:
            await msg.edit_text("✅ **Audio downloaded! Sending it to you now...**", parse_mode="Markdown")
            await query.message.reply_audio(audio=open(file_path, "rb"))
            os.remove(file_path)
            await msg.delete()
        else:
            await msg.edit_text("❌ **Failed to download the audio. Please try again.**", parse_mode="Markdown")

    elif action == "video":
        file_path = download_video(url)
        if file_path:
            await msg.edit_text("✅ **Video downloaded! Sending it to you now...**", parse_mode="Markdown")
            await query.message.reply_video(video=open(file_path, "rb"))
            os.remove(file_path)
            await msg.delete()
        else:
            await msg.edit_text("❌ **Failed to download the video. Please try again.**", parse_mode="Markdown")


# Main Function
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("video", video))
    app.add_handler(CommandHandler("audio", audio))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()
    