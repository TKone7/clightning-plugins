from telegram.ext import Updater, CommandHandler
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

TOKEN = '1072922906:AAE9LgfG0EHXgbmUdPFE1FieW4SLrnPZSVI'
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm your personal Lightning-Bot, I'll send you interesting stuff about your node.")


# Start handler
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

updater.start_polling()
