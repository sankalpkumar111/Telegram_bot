import telegram.ext
from dotenv import load_dotenv
import os
import sqlite3


load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))



async def start(update, context):
    await update.message.reply_text("Hello! Welcome to Study Bot")

async def helps(update, context):
    await update.message.reply_text(
        '''
        Hi there! I'm Telegram Bot created by Sankalp. Please follow these commands:-
        
        /start - to start the conversation
        /content - Information about ME
        /contact - Information about contact
        /helps - to get this help menu
        
        I hope this helps you :)
        '''
    )

async def content(update, context):
    await update.message.reply_text(
        '''
        Create a focused study environment, set clear goals, and use active learning techniques. Take regular breaks to avoid burnout. Prioritize sleep and stay organized with a planner. Don't hesitate to seek help when needed. Remember, consistent effort and smart strategies are key to academic success.
        '''
    )

async def contact(update, context):
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

async def add_pdf(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in chat_admins]

    if user_id not in admin_ids:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        keyword = context.args[0].lower()  
        pdf_file = context.args[1] 
        
        if not os.path.exists(pdf_file):
            await update.message.reply_text("File does not exist. Please provide a valid file path.")
            return

        with open(pdf_file, 'rb') as f:
            pdf_data = f.read()
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pdfs (keyword, file_data) VALUES (?, ?)", (keyword, pdf_data))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"PDF added with keyword '{keyword}'.")
    except IndexError:
        await update.message.reply_text("Please provide both a keyword and a file path.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

async def handle_msg(update, context):
    user_text = update.message.text.lower()  
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


application = telegram.ext.Application.builder().token(TOKEN).build()

application.add_handler(telegram.ext.CommandHandler('start', start))
application.add_handler(telegram.ext.CommandHandler('help', helps))
application.add_handler(telegram.ext.CommandHandler('content', content))
application.add_handler(telegram.ext.CommandHandler('contact', contact))
application.add_handler(telegram.ext.CommandHandler('addpdf', add_pdf))

application.add_handler(telegram.ext.MessageHandler(telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND, handle_msg))

application.run_polling()
