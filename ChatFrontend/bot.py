from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import PIL
from PIL import Image

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def help(bot, update):
    """Send a message when /help is issues"""
    reply = "Handwritten Equation Solver Bot\nSend an image to get started.\n"
    update.message.reply_text(reply)

def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text("Please send an image of the equation to get started.")

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def image_reply(bot, update):
    update.message.reply_text("Downloading...")
    file_id = update.message.photo[0].file_id
    newFile = bot.getFile(file_id)
    newFile.download('test.jpg')
    print("Saving image to file test.jpg")
    compress(28, 'test.jpg')

def compress(basewidth, name):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save('test_re.jpg')

def main():
    # Create the EventHandler and pass it your bot's token.
    token = "565522254:AAFzehm10MW8Z1CmNxamlcb2ZubQGIoNFvI"
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler(Filters.photo, image_reply))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
