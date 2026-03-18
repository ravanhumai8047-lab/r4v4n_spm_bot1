import os
import threading
from flask import Flask
import telebot
from openai import OpenAI

# Fetch environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Initialize Flask app (Required by Render to keep the web service alive)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running perfectly!", 200

# Initialize OpenAI Client (using Hugging Face Router as requested)
hf_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# Initialize Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN)

# Command: /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI chatting bot. Send me any message and I will reply using DeepSeek.\n\nUse /setname <new_name> in a group to change the group's name.")

# Command: /setname (Group Name Changer)
@bot.message_handler(commands=['setname'])
def change_group_name(message):
    # Check if the command is used inside a group
    if message.chat.type in ['group', 'supergroup']:
        # Extract the new name
        new_name = message.text.replace('/setname', '').strip()
        
        if not new_name:
            bot.reply_to(message, "Please provide a new name. Example: `/setname Awesome Group`")
            return
            
        try:
            # Change the group title
            bot.set_chat_title(message.chat.id, new_name)
            bot.reply_to(message, f"✅ Group name successfully changed to: **{new_name}**")
        except telebot.apihelper.ApiTelegramException as e:
            bot.reply_to(message, "❌ Failed to change the name. Please ensure I am an **Admin** in this group and have the **Change Group Info** permission.")
    else:
        bot.reply_to(message, "This command can only be used in groups!")

# Handle general text messages for AI Chatting
@bot.message_handler(func=lambda message: True, content_types=['text'])
def chat_with_ai(message):
    # Ignore any other commands
    if message.text.startswith('/'):
        return
        
    try:
        # Show "Typing..." action in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the Hugging Face AI Model
        chat_completion = hf_client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
        )
        
        # Extract response and reply
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Sorry, I encountered an error communicating with the AI. Please try again later.")

# Function to run the Telegram bot polling
def run_bot():
    print("Starting Telegram Bot...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start the bot in a separate background thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start the Flask web server (needed for Render to bind to a port)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
