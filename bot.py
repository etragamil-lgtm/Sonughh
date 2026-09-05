import os
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import telebot

# Apna Bot Token dalein
BOT_TOKEN = "8765709173:AAF0hDgBiH61--zD5mr_e1pm-fuGxvPMryw"
bot = telebot.TeleBot(BOT_TOKEN)

# Render port binding ke liye dummy server (Crash/Sleep rokne ke liye)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    text = (
        f"Namaste {user_name}! 🎨\n\n"
        "Main AI Photo Generator & Editor Bot hoon.\n\n"
        "1. Nayi photo: `/gen cyber warrior neon 4k`\n"
        "2. Photo remix: Photo bhejein aur Caption me prompt likhein!"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['gen', 'photo'])
def generate_text_to_image(message):
    chat_id = message.chat.id
    prompt = message.text.replace('/gen', '').replace('/photo', '').strip()

    if not prompt:
        bot.send_message(chat_id, "❌ Prompt dalein! Example:\n`/gen anime warrior with fire 4k`", parse_mode="Markdown")
        return

    wait_msg = bot.send_message(chat_id, f"🎨 Generating: *{prompt}*...", parse_mode="Markdown")
    bot.send_chat_action(chat_id, 'upload_photo')

    encoded = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

    try:
        bot.send_photo(chat_id, photo=image_url, caption=f"✨ *Prompt:* {prompt}", parse_mode="Markdown")
        bot.delete_message(chat_id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Error: {e}", chat_id, wait_msg.message_id)

@bot.message_handler(content_types=['photo'])
def handle_incoming_photo(message):
    chat_id = message.chat.id
    caption = message.caption

    if not caption:
        bot.send_message(chat_id, "⚠️ Photo ke sath **Caption** likhna zaroori hai!")
        return

    wait_msg = bot.send_message(chat_id, "🔄 AI photo transform kar raha hai...", parse_mode="Markdown")
    bot.send_chat_action(chat_id, 'upload_photo')

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        input_image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        encoded_prompt = urllib.parse.quote(caption)
        encoded_img_url = urllib.parse.quote(input_image_url)
        remix_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?image={encoded_img_url}&width=1024&height=1024&nologo=true"

        bot.send_photo(chat_id, photo=remix_url, caption=f"✨ *Transformed!*\n📝 {caption}", parse_mode="Markdown")
        bot.delete_message(chat_id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Error: {e}", chat_id, wait_msg.message_id)

if __name__ == "__main__":
    # Web server background thread me start karein
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("🤖 Bot 24/7 Cloud Started with Webhook Support...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
    
