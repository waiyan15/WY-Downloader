import os
import re
import io
import time
import threading
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from flask import Flask

# ================== BOT TOKEN ==================
BOT_TOKEN = "8706771918:AAGQW9r9Hn9fDMePGXatzt5_9STTwRuWTpk"

# ================== Start Image ==================
START_IMAGE = "https://i.supaimg.com/4f602596-8e4b-401c-9465-b978ececeeed/0c5b3096-bcac-452c-a6ad-e7d924643b10.png"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- Render Web Server (Free Tier) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Alive and Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ======================================================
#                 Helper Functions
# ======================================================
def clean_filename(text):
    return re.sub(r'[\\/:*?"<>|]', '', text)

def extract_tiktok_url(text: str):
    pattern = r"(https?://[^\s]+tiktok\.com[^\s]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None

def extract_youtube_url(text: str):
    pattern = r"(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None

def tiktok_api(url):
    api = "https://tikwm.com/api/"
    payload = {"url": url, "hd": 1}
    r = requests.post(api, data=payload, timeout=15)
    return r.json()

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"

def download_with_progress(url, chat_id, message_id, timeout=60):
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    chunks = []
    last_update = 0

    for chunk in response.iter_content(chunk_size=1024 * 128):
        if chunk:
            chunks.append(chunk)
            downloaded += len(chunk)

            now = time.time()
            if now - last_update >= 0.8 or downloaded == total_size:
                last_update = now
                if total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    bar = "▓" * (10 * downloaded // total_size) + "░" * (10 - (10 * downloaded // total_size))
                    text = f"⏳ <b>Downloading...</b>\n\n<code>{bar}</code> <b>{percent}%</b>\n📦 {format_size(downloaded)} / {format_size(total_size)}"
                else:
                    text = f"⏳ Downloading...\n📦 {format_size(downloaded)}"

                try:
                    bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML")
                except:
                    pass

    return io.BytesIO(b"".join(chunks))

# ======================================================
#                     START COMMAND
# ======================================================
@bot.message_handler(commands=["start"])
def start(message):
    name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    text = (
        f"👋 <b>မင်္ဂလာပါ {name}</b>\n\n"
        "🤖 <b>ဒီ Bot က TikTok နှင့် YouTube Downloader ပါ</b>\n\n"
        "✅ <b>TikTok</b> - Watermark မပါတဲ့ Video / MP3 / Photo Post\n"
        "✅ <b>YouTube</b> - Shorts နှင့် Videos များ\n\n"
        "🔗 Link ပို့ပေးရုံနဲ့ အလိုအလျောက် Download ဆွဲပေးပါမည်။"
    )
    try:
        bot.send_photo(message.chat.id, START_IMAGE, caption=text, parse_mode="HTML")
    except:
        bot.send_message(message.chat.id, text, parse_mode="HTML")

# ======================================================
#                 TikTok MP3 Callback
# ======================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("mp3|"):
        url = call.data.split("|", 1)[1]
        bot.answer_callback_query(call.id, "MP3 Downloading...")
        wait = bot.send_message(call.message.chat.id, "⏳ MP3 Downloading...")

        try:
            r = tiktok_api(url)
            d = r.get("data")
            if not d:
                bot.edit_message_text("❌ MP3 Download မအောင်မြင်ပါ", call.message.chat.id, wait.message_id)
                return

            title = clean_filename(d.get("title", "TikTok"))
            author = clean_filename(d.get("author", {}).get("nickname", "User"))
            audio_file = download_with_progress(d["music"], call.message.chat.id, wait.message_id, timeout=30)

            bot.send_audio(call.message.chat.id, audio=audio_file, caption=f"🎵 {title}", title=title, performer=author)
            bot.delete_message(call.message.chat.id, wait.message_id)
        except Exception as e:
            bot.edit_message_text(f"⚠️ Error: {e}", call.message.chat.id, wait.message_id)

# ======================================================
#                   MAIN HANDLER
# ======================================================
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    if not message.text:
        return

    text = message.text.strip()
    tiktok_url = extract_tiktok_url(text)
    youtube_url = extract_youtube_url(text)

    # ------------------ TikTok ------------------
    if tiktok_url:
        wait = bot.reply_to(message, "⏳ TikTok video ရှာနေပါသည်...")
        try:
            r = tiktok_api(tiktok_url)
            d = r.get("data")
            if not d:
                bot.edit_message_text("❌ Video ရှာမတွေ့ပါ", message.chat.id, wait.message_id)
                return

            title = clean_filename(d.get("title", "TikTok"))
            author = clean_filename(d.get("author", {}).get("nickname", "User"))
            images = d.get("images")

            if images:
                for i, img in enumerate(images, start=1):
                    bot.edit_message_text(f"📸 Photo {i}/{len(images)} downloading...", message.chat.id, wait.message_id)
                    photo = download_with_progress(img, message.chat.id, wait.message_id, timeout=20)
                    bot.send_photo(message.chat.id, photo=photo, caption=f"📸 {title} ({i})")

                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🎵 Download Music MP3", callback_data=f"mp3|{tiktok_url}"))
                bot.send_message(message.chat.id, "🎵 Music လိုရင် နှိပ်ပါ", reply_markup=kb)
                bot.delete_message(message.chat.id, wait.message_id)
                return

            video_file = download_with_progress(d["play"], message.chat.id, wait.message_id, timeout=60)
            bot.send_video(message.chat.id, video=video_file, caption=f"🎬 {title} - {author}.mp4", supports_streaming=True)

            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🎵 Download Music MP3", callback_data=f"mp3|{tiktok_url}"))
            bot.send_message(message.chat.id, "🎵 Music လိုရင် နှိပ်ပါ", reply_markup=kb)
            bot.delete_message(message.chat.id, wait.message_id)
            return
        except Exception as e:
            bot.edit_message_text(f"⚠️ TikTok Error: {e}", message.chat.id, wait.message_id)
            return

    # ------------------ YouTube ------------------
    if youtube_url:
        wait = bot.reply_to(message, "⏳ YouTube video processing... (ခေတ္တစောင့်ပါ)")
        out_file = f"yt_{message.chat.id}_{int(time.time())}.mp4"

        ydl_opts = {
            'format': 'best[ext=mp4][filesize<45M]/best[filesize<45M]/best',
            'outtmpl': out_file,
            'quiet': True,
            'no_warnings': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                title = clean_filename(info.get('title', 'YouTube Video'))

            if os.path.exists(out_file):
                bot.edit_message_text("📤 Telegram သို့ ပို့တင်နေပါသည်...", message.chat.id, wait.message_id)
                with open(out_file, 'rb') as vf:
                    bot.send_video(message.chat.id, video=vf, caption=f"🎬 <b>{title}</b>", supports_streaming=True)
                os.remove(out_file)
                bot.delete_message(message.chat.id, wait.message_id)
            else:
                bot.edit_message_text("❌ Download ဖိုင် မတွေ့ပါ", message.chat.id, wait.message_id)
        except Exception as e:
            if os.path.exists(out_file):
                os.remove(out_file)
            bot.edit_message_text(f"⚠️ YouTube Error: {e}", message.chat.id, wait.message_id)
        return

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    print("🤖 Bot Running (TikTok + YouTube)...")
    bot.infinity_polling()
