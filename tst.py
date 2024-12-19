import os
import logging
import requests
import cv2  # For video validation
from PIL import Image  # For image validation
import instaloader
from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure the 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Initialize Pyrogram Client
app_pyro = Client("instagram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
loader = instaloader.Instaloader()


class MediaProcessor:
    @staticmethod
    def download_media(url, prefix="temp"):
        try:
            post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
            media_type = "video" if post.is_video else "image"
            media_url = post.video_url if post.is_video else post.url
            ext = "mp4" if media_type == "video" else "jpg"
            file_path = f"downloads/{prefix}_media.{ext}"

            response = requests.get(media_url, stream=True)
            if response.status_code != 200:
                return None
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if media_type == "video":
                return MediaProcessor.validate_video(file_path)
            elif media_type == "image":
                return MediaProcessor.validate_image(file_path)
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None

    @staticmethod
    def validate_video(file_path):
        try:
            video = cv2.VideoCapture(file_path)
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            duration = int(video.get(cv2.CAP_PROP_FRAME_COUNT) / fps) if fps > 0 else 0
            video.release()

            if width > 0 and height > 0 and duration > 0:
                return file_path
            else:
                os.remove(file_path)
                return None
        except Exception as e:
            logger.error(f"Video validation error: {e}")
            os.remove(file_path)
            return None

    @staticmethod
    def validate_image(file_path):
        try:
            with Image.open(file_path) as img:
                img.verify()  # Verify image integrity
                if img.size[0] > 0 and img.size[1] > 0:
                    return file_path
            os.remove(file_path)
            return None
        except Exception as e:
            logger.error(f"Image validation error: {e}")
            os.remove(file_path)
            return None


@app_pyro.on_message(filters.regex(r"(https?://www.instagram.com/[^ ]+)"))
async def handle_instagram_url(client, message):
    url = message.text.strip()
    processing_msg = await message.reply_text("🔄 Processing Instagram URL...")

    file_path = MediaProcessor.download_media(url)
    if file_path:
        if file_path.endswith(".mp4"):
            await client.send_video(chat_id=message.chat.id, video=file_path)
        elif file_path.endswith(".jpg"):
            await client.send_photo(chat_id=message.chat.id, photo=file_path)
        os.remove(file_path)
        await processing_msg.delete()
    else:
        await processing_msg.edit_text("❌ Failed to download or validate Instagram media.")


# Run Pyrogram Client
if __name__ == "__main__":
    app_pyro.run()
    