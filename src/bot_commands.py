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
import logging

# bot's modules
from config_paths import CONFIG_PATH
from token_usage_visualization import generate_usage_chart
from modules import reset_token_usage_at_midnight 

# ~~~~~~~~~~~~~~
# admin commands
# ~~~~~~~~~~~~~~

# /admin (admin commands help menu)
async def admin_command(update: Update, context: CallbackContext, bot_owner_id):
    if bot_owner_id == '0':
        await update.message.reply_text("The /admin command is disabled.")
        return

    if str(update.message.from_user.id) == bot_owner_id:
        admin_commands = """
Admin Commands:
- <code>/viewconfig</code>: View the bot configuration (from <code>config.ini</code>).
- <code>/usage</code>: View the bot's daily token usage in plain text.
- <code>/usagechart</code>: View the bot's daily token usage as a chart.
- <code>/reset</code>: Reset the bot's context memory.
- <code>/resetsystemmessage</code>: Reset the system message from <code>config.ini</code>.
- <code>/setsystemmessage &lt;system message&gt;</code>: Set a new system message (note: not saved into config).
        """
        await update.message.reply_text(admin_commands, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# /restart (admin command)
async def restart_command(update: Update, context: CallbackContext, bot_owner_id):
    if bot_owner_id == '0':
        await update.message.reply_text("The /restart command is disabled.")
        return

    if str(update.message.from_user.id) == bot_owner_id:
        # WIP: Implement restart logic here
        await update.message.reply_text("Restarting the bot...")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# /resetdailytokens (admin command for resetting daily token usage)
async def reset_daily_tokens_command(update: Update, context: CallbackContext, bot_instance):
    user_id = update.message.from_user.id
    if bot_instance.bot_owner_id == '0' or str(user_id) != bot_instance.bot_owner_id:
        logging.info(f"User {user_id} tried to use /resetdailytokens but was not authorized.")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        
        # (old fallback method, JIC)
        # Reset the in-memory token usage counter
        # bot_instance.total_token_usage = 0
        # logging.info("In-memory token usage counter reset.")

        # Pass the reset_total_token_usage method as a callback to reset_token_usage_at_midnight
        reset_token_usage_at_midnight(bot_instance.token_usage_file, bot_instance.reset_total_token_usage)
        logging.info(f"User {user_id} has reset the daily token usage, including the in-memory token usage counter.")
        await update.message.reply_text("Daily token usage has been reset, including the in-memory token usage counter.")
        
    except Exception as e:
        logging.error(f"Failed to reset daily token usage: {e}")
        await update.message.reply_text("Failed to reset daily token usage.")

# /resetsystemmessage (admin command)
async def reset_system_message_command(update: Update, context: CallbackContext, bot_instance):
    user_id = update.message.from_user.id
    if bot_instance.bot_owner_id == '0' or str(user_id) != bot_instance.bot_owner_id:
        logging.info(f"User {user_id} tried to use /resetsystemmessage but was not authorized.")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    old_system_message = bot_instance.system_instructions
    bot_instance.system_instructions = bot_instance.config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
    logging.info(f"User {user_id} reset the system message to default.")
    await update.message.reply_text(f"System message reset to default.\n\nOld Message:\n<code>{old_system_message}</code>\n----------------------\nNew Default Message:\n<code>{bot_instance.system_instructions}</code>", parse_mode=ParseMode.HTML)

# /setsystemmessage (admin command)
async def set_system_message_command(update: Update, context: CallbackContext, bot_instance):
    user_id = update.message.from_user.id
    if bot_instance.bot_owner_id == '0' or str(user_id) != bot_instance.bot_owner_id:
        logging.info(f"User {user_id} tried to use /setsystemmessage but was not authorized.")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    new_system_message = ' '.join(context.args)
    if new_system_message:
        old_system_message = bot_instance.system_instructions
        bot_instance.system_instructions = new_system_message
        logging.info(f"User {user_id} updated the system message to: {new_system_message}")
        await update.message.reply_text(f"System message updated.\n\nOld Message: <code>{old_system_message}</code>\nNew Message: <code>{new_system_message}</code>", parse_mode=ParseMode.HTML)
    else:
        logging.info(f"User {user_id} attempted to set system message but provided no new message.")
        await update.message.reply_text("Please provide the new system message in the command line, i.e.: /setsystemmessage My new system message to the AI on what it is, where it is, etc.")


# /usage (admin command)
# bot_commands.py
async def usage_command(update: Update, context: CallbackContext):
    bot_instance = context.bot_data.get('bot_instance')  # Retrieve the bot instance from context
    
    if not bot_instance:
        await update.message.reply_text("Internal error: Bot instance not found.")
        logging.error("Bot instance not found in context.bot_data")
        return

    logging.info(f"User {update.message.from_user.id} invoked /usage command")

    if bot_instance.bot_owner_id == '0':
        await update.message.reply_text("The `/usage` command is disabled.")
        logging.info("Usage command is disabled until a bot owner is defined in `config.ini`.")
        return

    if str(update.message.from_user.id) != bot_instance.bot_owner_id:
        await update.message.reply_text("You don't have permission to use this command.")
        logging.info(f"User {update.message.from_user.id} does not have permission to use /usage")
        return

    # Correct path to token_usage.json inside logs/ directory
    # token_usage_file = os.path.join(bot_instance.data_directory, 'logs', 'token_usage.json')
    token_usage_file = os.path.join(bot_instance.logs_directory, 'token_usage.json')

    logging.info(f"Looking for token usage file at: {token_usage_file}")
    current_date = datetime.datetime.utcnow()

    try:
        if os.path.exists(token_usage_file):
            with open(token_usage_file, 'r') as file:
                token_usage_history = json.load(file)
            logging.info("Loaded token usage history successfully")
            
            # Prune token usage history
            cutoff_date = current_date - datetime.timedelta(days=bot_instance.max_history_days)
            token_usage_history = {
                date: usage for date, usage in token_usage_history.items()
                if datetime.datetime.strptime(date, '%Y-%m-%d') >= cutoff_date
            }
            logging.info("Pruned token usage history based on cutoff date")
        else:
            token_usage_history = {}
            logging.warning(f"Token usage file does not exist at: {token_usage_file}")
    except json.JSONDecodeError:
        await update.message.reply_text("Error reading token usage history.")
        logging.error("JSONDecodeError while reading token_usage.json")
        return
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error in usage_command: {e}")
        return

    today_usage = token_usage_history.get(current_date.strftime('%Y-%m-%d'), 0)
    token_cap_info = (
        f"Today's usage: {today_usage} tokens\n"
        f"Daily token cap: {'No cap' if bot_instance.max_tokens_config == 0 else f'{bot_instance.max_tokens_config} tokens'}\n\n"
        "Token Usage History:\n"
    )

    for date, usage in sorted(token_usage_history.items()):
        token_cap_info += f"{date}: {usage} tokens\n"

    await update.message.reply_text(token_cap_info)
    logging.info("Sent usage information to user")

# /usagechart (admin command)
async def usage_chart_command(update: Update, context: CallbackContext):
    bot_instance = context.bot_data.get('bot_instance')  # Retrieve the bot instance from context
    
    if not bot_instance:
        await update.message.reply_text("Internal error: Bot instance not found.")
        logging.error("Bot instance not found in context.bot_data")
        return

    logging.info(f"User {update.message.from_user.id} invoked /usagechart command")

    if bot_instance.bot_owner_id == '0':
        await update.message.reply_text("The `/usagechart` command is disabled.")
        logging.info("Usagechart command is disabled")
        return

    if str(update.message.from_user.id) != bot_instance.bot_owner_id:
        await update.message.reply_text("You don't have permission to use this command.")
        logging.info(f"User {update.message.from_user.id} does not have permission to use /usagechart")
        return

    # Define paths
    token_usage_file = os.path.join(bot_instance.logs_directory, 'token_usage.json')
    output_image_file = os.path.join(bot_instance.data_directory, 'token_usage_chart.png')

    logging.info(f"Looking for token usage file at: {token_usage_file}")
    logging.info(f"Output image file will be at: {output_image_file}")

    # Ensure the data directory exists
    try:
        if not os.path.exists(bot_instance.data_directory):
            os.makedirs(bot_instance.data_directory, exist_ok=True)
            bot_instance.logger.info(f"Created data directory at {bot_instance.data_directory}")
    except OSError as e:
        bot_instance.logger.error(f"Failed to create data directory {bot_instance.data_directory}: {e}")
        await update.message.reply_text(f"Failed to create the data directory for the chart. Please check the bot's permissions.")
        return

    # Generate the usage chart
    try:
        generate_usage_chart(token_usage_file, output_image_file)
        bot_instance.logger.info(f"Generated usage chart at {output_image_file}")
    except Exception as e:
        bot_instance.logger.error(f"Failed to generate usage chart: {e}")
        await update.message.reply_text("Failed to generate usage chart.")
        return

    # Try to open and send the generated chart image
    try:
        with open(output_image_file, 'rb') as file:
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=file)
        bot_instance.logger.info(f"Sent usage chart to chat_id {update.message.chat_id}")
    except FileNotFoundError:
        await update.message.reply_text("Token usage chart not found. Please ensure it's being generated correctly.")
        bot_instance.logger.error("Token usage chart file not found: %s", output_image_file)
    except Exception as e:
        await update.message.reply_text("Failed to send the usage chart.")
        bot_instance.logger.error(f"Error sending usage chart: {e}")

# /reset
async def reset_command(update: Update, context: CallbackContext, bot_owner_id, reset_enabled, admin_only_reset):
    # Check if the /reset command is enabled
    if not reset_enabled:
        logging.info(f"User tried to use the /reset command, but it was disabled.")
        await update.message.reply_text("The /reset command is disabled.")
        return

    # Check if the command is admin-only and if the user is the admin
    if admin_only_reset and str(update.message.from_user.id) != bot_owner_id:
        logging.info(f"User tried to use the /reset command, but was not authorized to do so.")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # If the user is authorized, or if the command is not admin-only
    if 'chat_history' in context.chat_data:
        context.chat_data['chat_history'] = []
        logging.info(f"Memory context was reset successfully with: /reset")
        await update.message.reply_text("Memory context reset successfully.")
    else:
        logging.info(f"No memory context to reset with: /reset")
        await update.message.reply_text("No memory context to reset.")

# /viewconfig (admin command)
async def view_config_command(update: Update, context: CallbackContext, bot_owner_id):
    user_id = update.message.from_user.id  # Retrieve the user_id

    if bot_owner_id == '0':
        logging.info(f"User {user_id} attempted to view the config with: /viewconfig -- command disabled")
        await update.message.reply_text("The /viewconfig command is disabled.")
        return

    if str(user_id) == bot_owner_id:
        try:
            config_contents = "<pre>"
            with open(CONFIG_PATH, 'r') as file:
                for line in file:
                    if not line.strip() or line.strip().startswith('#'):
                        continue
                    # Escape HTML special characters
                    line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    config_contents += line
            config_contents += "</pre>"
            logging.info(f"User {user_id} (owner) viewed the config with: /viewconfig")
            if config_contents:
                await update.message.reply_text(config_contents, parse_mode=ParseMode.HTML)
            else:
                logging.info(f"[WARNING] User {user_id} attempted to view the config with: /viewconfig -- no configuration settings were available")
                await update.message.reply_text("No configuration settings available.")
        except Exception as e:
            logging.info(f"[ERROR] User {user_id} attempted to view the config with: /viewconfig -- there was an error reading the config file: {e}")
            await update.message.reply_text(f"Error reading configuration file: {e}")
    else:
        logging.info(f"[ATTENTION] User {user_id} attempted to view the config with: /viewconfig -- access denied")
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
    🤖 TelegramBot-OpenAI-API ⚡️ Powered by ChatKeke 🚀
    This is an OpenAI-powered Telegram chatbot created by FlyingFathead.
    Version: v{version_number}
    For more information, visit: https://github.com/FlyingFathead/TelegramBot-OpenAI-API
    (The original author is NOT responsible for any chatbots created using the code)
    """
    await update.message.reply_text(about_text)

# /help
async def help_command(update: Update, context: CallbackContext, reset_enabled, admin_only_reset):
    help_text = """
    Welcome to this OpenAI API-powered chatbot! Here are some commands you can use:

    - /start: Start a conversation with the bot.
    - /help: Display this help message.
    - /about: Learn more about this bot.
    """

    if reset_enabled:
        help_text += "- /reset: Reset the bot's context memory.\n"
        if admin_only_reset:
            help_text += "  (Available to admin only)\n"

    help_text += "- /admin: (For bot owner only) Display admin commands.\n\nJust type your message to chat with the bot!"

    await update.message.reply_text(help_text)