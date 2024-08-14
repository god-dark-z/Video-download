import os
import time
import telebot
import logging
import socket
import subprocess
import sys
from yt_dlp import YoutubeDL
from instaloader import Instaloader, Post
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from mega import Mega
from threading import Timer

#-----[Update-Module]-----#
def install_and_update_modules():
    try:
        required_modules = [
            "telebot", "yt-dlp", "instaloader", "mega.py", "tenacity"
        ]
        for module in required_modules:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", module])
        logging.info("All modules installed and updated successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install/update modules: {e}")
        sys.exit("Exiting due to failed module installation.")

install_and_update_modules()

#-----[LOGS]-----#
logging.basicConfig(filename='bot_logs.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

#-----[LOGIN'S]-----#
BOT_TOKEN = '7497349489:AAGFnkSfWUszhrApuY68Lc3tijXud4sS3Fw'
MEGA_EMAIL = 'blackydevil23@gmail.com'
MEGA_PASSWORD = 'L:dw3mGW_3-QnhQ'

#-----[BOT]-----#
bot = telebot.TeleBot(BOT_TOKEN)

#-----[THREADS]-----#
executor = ThreadPoolExecutor(max_workers=10)

#-----[MEGA]-----#
mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

#-----[USER-IP]-----#
def get_user_ip():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        logger.error(f"Error retrieving IP address: {e}")
        return "Unknown"

#-----[RETRY]-----#
def retry_request(func, *args, **kwargs):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise

#-----[YT-DLP]-----#
def download_video(url, chat_id):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'socket_timeout': 60,
    }

    try:
        processing_message = bot.send_message(chat_id, "🔄 Processing your video, please wait...")
        
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            if len(filename) > 100:
                filename = f"{info_dict.get('id', 'video')}.mp4"
            title = info_dict.get('title', 'No title')[:100]
            upload_date = info_dict.get('upload_date', '')
            formatted_date = "Unknown"
            try:
                if upload_date:
                    formatted_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%d/%m/%y')
            except ValueError as e:
                logger.error(f"Date parsing error for chat_id {chat_id}: {e}")

            platform = url.split('/')[2]
            views = info_dict.get('view_count', 'Unknown')
            likes = info_dict.get('like_count', 'Unknown')
            author = info_dict.get('uploader', 'Unknown')
            video_size = os.path.getsize(filename) / (1024 * 1024)
            bot.edit_message_text(chat_id=chat_id, message_id=processing_message.message_id, text=f"🔄 Uploading to Mega.nz, please wait...")
            file = m.upload(filename)
            link = m.get_upload_link(file)
            caption = (
                f"🎬 **Title**: *{title}*\n"
                f"📅 **Upload Date**: *{formatted_date}*\n"
                f"👀 **Views**: *{views}*\n"
                f"👍 **Likes**: *{likes}*\n"
                f"📝 **Author**: *{author}*\n"
                f"💾 **Size**: *{video_size:.2f} MB*\n"
                f"🌐 **Platform**: *{platform}*\n\n"
                f"📥 **Download Link**: [Click Here]({link})\n"
                f"⏳ *Note*: The video will be removed from Mega.nz in **10 minutes**."
            )
            bot.edit_message_text(chat_id=chat_id, message_id=processing_message.message_id, text=f"✅ Your video is ready!")
            bot.send_message(chat_id, caption, parse_mode="Markdown")
            Timer(600, lambda: m.delete(file[0])).start()
            os.remove(filename)
            logger.info(f"Video downloaded, uploaded to Mega.nz, and sent successfully for chat_id {chat_id}!\nVideo Title: {title}\nPlatform: {platform}")
    except Exception as e:
        logger.error(f"Error downloading video for chat_id {chat_id}: {e}")
        bot.send_message(chat_id, "❌ Failed to download or send the video. Please check the link and try again.")

#-----[INSTAGRAM]-----#
def download_instagram_video(url, chat_id):
    loader = Instaloader()
    def fetch_post_data(shortcode):
        post = Post.from_shortcode(loader.context, shortcode)
        return post
    try:
        shortcode = url.split("/")[-2]
        post = retry_request(fetch_post_data, shortcode)
        video_url = post.video_url
        title = post.title if post.title else "Instagram Video"
        upload_date = post.date_utc.strftime("%d/%m/%y")
        likes = post.likes
        views = post.video_view_count
        author = post.owner_username
        caption = (
            f"🎥 **Title**: *{title}*\n"
            f"📅 **Upload Date**: *{upload_date}*\n"
            f"👀 **Views**: *{views}*\n"
            f"👍 **Likes**: *{likes}*\n"
            f"📝 **Author**: *{author}*\n"
            f"🌐 **Platform**: *Instagram*\n\n"
            f"📥 **Download Link**: [Click Here]({video_url})\n"
        )
        bot.send_message(chat_id, "🔄 Processing your Instagram video, please wait...")
        bot.send_message(chat_id, caption, parse_mode="Markdown")
        logger.info(f"Instagram video processed and sent successfully for chat_id {chat_id}!\nVideo Title: {title}\nPlatform: Instagram")
    except Exception as e:
        logger.error(f"Error downloading Instagram video for chat_id {chat_id}: {e}")
        bot.send_message(chat_id, "❌ Failed to download or send the Instagram video. Please check the link and try again.")

#-----[HANDLE-LINKS]-----#
def handle_message(message):
    url = message.text
    chat_id = message.chat.id
    if message.text.startswith("/start"):
        bot.send_message(chat_id, "🎉 Welcome! Send me a video link from YouTube, Instagram, Facebook, or TikTok, and I'll download it for you in the best quality.")
        return
    if 'youtube.com' in url or 'youtu.be' in url or 'facebook.com' in url or 'tiktok.com' in url:
        executor.submit(download_video, url, chat_id)
    elif 'instagram.com' in url:
        executor.submit(download_instagram_video, url, chat_id)
    else:
        bot.send_message(chat_id, "⚠️ Unsupported video platform. Please send a link from YouTube, Instagram, Facebook, or TikTok.")

#-----[BOT-HANDLER]-----#
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    handle_message(message)

#-----[START]-----#
if __name__ == '__main__':
    bot.polling(none_stop=True)
