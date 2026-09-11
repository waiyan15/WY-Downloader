import os
import re
import time
import threading
import telebot
import yt_dlp
from flask import Flask

# ================== BOT TOKEN ==================
BOT_TOKEN = "8706771918:AAGQW9r9Hn9fDMePGXatzt5_9STTwRuWTpk"

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

# ======================================================
#                     START COMMAND
# ======================================================
@bot.message_handler(commands=["start"])
def start(message):
    name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    text = (
        f"👋 <b>မင်္ဂလာပါ {name}</b>\n\n"
        "🤖 <b>ဒီ Bot က TikTok နှင့် YouTube Downloader ပါ</b>\n\n"
        "✅ <b>TikTok</b> - Watermark မပါသော ဗီဒီယိုများ\n"
        "✅ <b>YouTube</b> - Shorts နှင့် Videos များ\n\n"
        "🔗 Link ပို့ပေးရုံနဲ့ အလိုအလျောက် Download ဆွဲပေးပါမည်။"
    )
    try:
        bot.send_photo(message.chat.id, START_IMAGE, caption=text, parse_mode="HTML")
    except:
        bot.send_message(message.chat.id, text, parse_mode="HTML")

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

    target_url = tiktok_url or youtube_url
    platform = "TikTok" if tiktok_url else ("YouTube" if youtube_url else None)

    if not platform:
        return

    wait = bot.reply_to(message, f"⏳ {platform} ဗီဒီယိုကို ဒေါင်းလုဒ်ဆွဲနေပါသည်... (ခေတ္တစောင့်ပါ)")
    out_file = f"vid_{message.chat.id}_{int(time.time())}.mp4"

    ydl_opts = {
        'format': 'best[ext=mp4][filesize<48M]/best[filesize<48M]/best',
        'outtmpl': out_file,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            title = clean_filename(info.get('title', f'{platform} Video'))

        if os.path.exists(out_file):
            bot.edit_message_text("📤 Telegram သို့ ပို့တင်နေပါသည်...", message.chat.id, wait.message_id)
            with open(out_file, 'rb') as vf:
                bot.send_video(
                    message.chat.id,
                    video=vf,
                    caption=f"🎬 <b>{title}</b>\n\n📌 <i>Downloaded via @{bot.get_me().username}</i>",
                    supports_streaming=True
                )
            os.remove(out_file)
            bot.delete_message(message.chat.id, wait.message_id)
        else:
            bot.edit_message_text(f"❌ {platform} ဗီဒီယို ရှာမတွေ့ပါ", message.chat.id, wait.message_id)

    except Exception as e:
        if os.path.exists(out_file):
            os.remove(out_file)
        bot.edit_message_text(f"⚠️ Error ဖြစ်နေပါသည် (ဖိုင်အရွယ်အစား ကြီးလွန်းခြင်း သို့မဟုတ် Link မှားယွင်းခြင်း ဖြစ်နိုင်ပါသည်)\n\n{e}", message.chat.id, wait.message_id)

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    print("🤖 Bot Running (TikTok + YouTube)...")
    bot.infinity_polling()
