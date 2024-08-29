import telegram.ext
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import sqlite3

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Initialize the database
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Create the table for storing PDFs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            file_data BLOB NOT NULL
        )
    ''')

    # Create a table to store the bot hit counter
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hit_count INTEGER NOT NULL
        )
    ''')

    # Create a table to store user hit counts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_hits (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            hit_count INTEGER NOT NULL
        )
    ''')

    # Initialize hit count if not already present
    cursor.execute('INSERT INTO bot_hits (hit_count) VALUES (0) ON CONFLICT(id) DO NOTHING')

    conn.commit()
    conn.close()

# Function to increment the bot hit counter
def increment_bot_hit_counter():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Increment the hit counter
    cursor.execute('UPDATE bot_hits SET hit_count = hit_count + 1 WHERE id = 1')

    # Fetch the updated hit count
    cursor.execute('SELECT hit_count FROM bot_hits WHERE id = 1')
    result = cursor.fetchone()

    conn.commit()
    conn.close()

    # Print the current hit count in the terminal
    if result:
        print(f"Bot hit count: {result[0]}")

# Function to increment the user hit counter
def increment_user_hit_counter(user_id, username):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Check if the user already exists in the database
    cursor.execute('SELECT hit_count FROM user_hits WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result:
        # Update the hit count for the existing user
        cursor.execute('UPDATE user_hits SET hit_count = hit_count + 1 WHERE user_id = ?', (user_id,))
    else:
        # Insert a new user with an initial hit count of 1
        cursor.execute('INSERT INTO user_hits (user_id, username, hit_count) VALUES (?, ?, ?)', (user_id, username, 1))

    # Fetch the updated hit count
    cursor.execute('SELECT hit_count FROM user_hits WHERE user_id = ?', (user_id,))
    user_hits = cursor.fetchone()

    conn.commit()
    conn.close()

    # Print the current user hit count in the terminal
    if user_hits:
        print(f"User {username} (ID: {user_id}) hit count: {user_hits[0]}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Welcome to Study Bot")

# Help command
async def helps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '''
        Hi there! I'm Telegram Bot created by Sankalp. Please follow these commands:-
        
        /start - to start the conversation
        /content - Information about ME
        /contact - Information about contact
        /help - to get this help menu
        
        I hope this helps you :)
        '''
    )

# Content command
async def content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '''
        Create a focused study environment, set clear goals, and use active learning techniques. Take regular breaks to avoid burnout. Prioritize sleep and stay organized with a planner. Don't hesitate to seek help when needed. Remember, consistent effort and smart strategies are key to academic success.
        '''
    )

# Contact command
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '''
        **Contact Us:**

        * **Phone:** +91 123 456 7890
        * **Email:** [email protected]
        * **Address:** Your Company, Your City, India

        **Social Media:** [Links to your social media profiles]

        **Hours:** Mon-Fri 9-5, Sat 10-2, Sun Closed
        '''
    )

# Start the PDF upload process
async def add_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Admin check
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in chat_admins]

    if user_id not in admin_ids:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Store the keyword for later use
    try:
        keyword = context.args[0].lower()
        context.user_data['pdf_keyword'] = keyword
        await update.message.reply_text("Please send the PDF file now.")
    except IndexError:
        await update.message.reply_text("Please provide a keyword.")

# Handle the PDF file upload
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pdf_keyword' not in context.user_data:
        await update.message.reply_text("Please use the /addpdf command first to provide a keyword.")
        return

    keyword = context.user_data.pop('pdf_keyword')  # Retrieve and remove the keyword
    file = update.message.document

    if file.mime_type == "application/pdf":
        try:
            file_data = await file.get_file()
            file_bytes = await file_data.download_as_bytearray()

            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO pdfs (keyword, file_data) VALUES (?, ?)", (keyword, file_bytes))
            conn.commit()
            conn.close()

            await update.message.reply_text(f"PDF added with keyword '{keyword}'.")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {e}")
    else:
        await update.message.reply_text("Please upload a PDF file.")

# Handle messages and documents
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    user_name = update.effective_user.first_name  # Fetch the user's first name
    user_id = update.effective_user.id  # Fetch the user's ID

    # Increment the bot and user hit counters
    increment_bot_hit_counter()
    increment_user_hit_counter(user_id, user_name)

    # Debugging: Print user query and name
    print(f"User query: {user_text}, User name: {user_name}")

    # Check if the user text contains 'note' or 'notes'
    if 'note' in user_text or 'notes' in user_text:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT file_data FROM pdfs WHERE ? LIKE '%' || keyword || '%' AND (instr(?, ' note') > 0 OR instr(?, ' notes') > 0)", (user_text, user_text, user_text))
        result = cursor.fetchone()
        conn.close()

        if result:
            pdf_data = result[0]
            if pdf_data:
                await update.message.reply_document(document=pdf_data, filename="document.pdf")
            else:
                await update.message.reply_text("The file associated with this keyword no longer exists in the database.")
        else:
            await update.message.reply_text("No PDF found for your query.")

# Create the bot application
application = Application.builder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', helps))
application.add_handler(CommandHandler('content', content))
application.add_handler(CommandHandler('contact', contact))
application.add_handler(CommandHandler('addpdf', add_pdf))

# Add handlers for documents and text
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

# Initialize the database
init_db()

# Start polling
application.run_polling()
