# bot_commands.py
# for telegram
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from functools import partial

import json
import os
import datetime

# ~~~~~~~~~~~~~~
# admin commands
# ~~~~~~~~~~~~~~

# /admin (admin commands help menu)
async def admin_command(update: Update, context: CallbackContext, bot_owner_id):
    if bot_owner_id == '0':
        await update.message.reply_text("The `/admin` command is disabled.")
        return

    if str(update.message.from_user.id) == bot_owner_id:
        admin_commands = """
        Admin Commands:
        - /viewconfig: View the bot configuration (from `config.ini`).
        - /usage: View the bot's daily token usage.
        """
        await update.message.reply_text(admin_commands)
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# /restart (admin command)
async def restart_command(update: Update, context: CallbackContext, bot_owner_id):
    if bot_owner_id == '0':
        await update.message.reply_text("The `/restart` command is disabled.")
        return

    if str(update.message.from_user.id) == bot_owner_id:
        # WIP: Implement restart logic here
        await update.message.reply_text("Restarting the bot...")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# /usage (admin command)
async def usage_command(update: Update, context: CallbackContext, bot_owner_id, token_usage_file, max_tokens_config):
    if bot_owner_id == '0':
        await update.message.reply_text("The `/usage` command is disabled.")
        return

    if str(update.message.from_user.id) != bot_owner_id:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        if os.path.exists(token_usage_file):
            with open(token_usage_file, 'r') as file:
                token_usage_history = json.load(file)
        else:
            token_usage_history = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Error reading token usage history.")
        return

    current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    today_usage = token_usage_history.get(current_date, 0)
    token_cap_info = f"Today's usage: {today_usage} tokens\n" \
                     f"Daily token cap: {'No cap' if max_tokens_config == 0 else f'{max_tokens_config} tokens'}\n\n" \
                     "Token Usage History:\n"

    for date, usage in token_usage_history.items():
        token_cap_info += f"{date}: {usage} tokens\n"

    await update.message.reply_text(token_cap_info)

# /viewconfig (admin command)
async def view_config_command(update: Update, context: CallbackContext, bot_owner_id):
    if bot_owner_id == '0':
        await update.message.reply_text("The `/viewconfig` command is disabled.")
        return

    if str(update.message.from_user.id) == bot_owner_id:
        try:
            config_contents = "<pre>"
            with open('config.ini', 'r') as file:
                for line in file:
                    if not line.strip() or line.strip().startswith('#'):
                        continue
                    # Escape HTML special characters
                    line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    config_contents += line
            config_contents += "</pre>"
            if config_contents:
                await update.message.reply_text(config_contents, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("No configuration settings available.")
        except Exception as e:
            await update.message.reply_text(f"Error reading configuration file: {e}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# ~~~~~~~~~~~~~
# user commands
# ~~~~~~~~~~~~~

# /start
async def start(update: Update, context: CallbackContext, start_command_response):
    await update.message.reply_text(start_command_response)

# /about
async def about_command(update: Update, context: CallbackContext, version_number):
    about_text = f"""
    This is an OpenAI-powered Telegram chatbot created by FlyingFathead.
    Version: v{version_number}
    For more information, visit: https://github.com/FlyingFathead/TelegramBot-OpenAI-API
    (The original author is NOT responsible for any chatbots created using the code)
    """
    await update.message.reply_text(about_text)

# /help
async def help_command(update: Update, context: CallbackContext):
    help_text = """
    Welcome to this OpenAI API-powered chatbot! Here are some commands you can use:

    - /start: Start a conversation with the bot.
    - /help: Display this help message.
    - /about: Learn more about this bot.
    - /admin: (For bot owner only) Display admin commands.
    
    Just type your message to chat with the bot!
    """
    await update.message.reply_text(help_text)
