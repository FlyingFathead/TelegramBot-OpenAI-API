# utils.py
import re
import shutil
import sys
import datetime
from functools import partial

# set `now`
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# print term width horizontal line
def hz_line(character='-'):
    terminal_width = shutil.get_terminal_size().columns
    line = character * terminal_width
    print(line)
    sys.stdout.flush()  # Flush the output to the terminal immediately

def print_startup_message(version_number):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hz_line()
    print(f"[{now}] Telegram bot v.{version_number} for OpenAI API starting up...", flush=True)
    hz_line()

# escape markdown v2, v0.12 [currently not in use because this is a ... it's a thing]
def escape_markdown_v2(text):

    # Escape MarkdownV2 special characters
    def escape_special_chars(m):
        char = m.group(0)
        # Escape all special characters with a backslash, except for asterisks and underscores
        if char in ('_', '*', '`'):
            # These are used for formatting and shouldn't be escaped.
            return char
        return '\\' + char

    # First, we'll handle the code blocks by temporarily removing them
    code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
    code_placeholders = [f"CODEBLOCK{i}" for i in range(len(code_blocks))]
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(block, placeholder)

    # Now we escape the special characters outside of the code blocks
    text = re.sub(r'([[\]()~>#+\-=|{}.!])', escape_special_chars, text)

    # We convert **bold** and *italic* (or _italic_) syntax to Telegram's MarkdownV2 syntax
    # Bold: **text** to *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Italic: *text* or _text_ to _text_ (if not part of a code block)
    text = re.sub(r'\b_(.+?)_\b', r'_\1_', text)
    text = re.sub(r'\*(.+?)\*', r'_\1_', text)

    # Restore the code blocks
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(placeholder, block)

    return text