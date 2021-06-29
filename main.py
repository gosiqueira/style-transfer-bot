import argparse
import logging
import os
from io import BytesIO

from dotenv import dotenv_values
from PIL import Image
from telegram import ParseMode, ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from src.style import transfer
from src.utils import image_loader, unload_image

logger = logging.getLogger(__name__)

CHOOSING, SENDING_IMG, TYPING_REPLY = range(3)

reply_keyboard = [
    ['Source'],
    ['Target'],
    ['Done'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def download_image(update, context, user_id, img_type='style'):
    logging.debug(f'Downloading {img_type} image')
    if update.message.photo is None:
        update.message.reply_text('Please provide a **valid image**.',
            parse_mode=ParseMode.MARKDOWN)
        valid = False
    else:
        img = context.bot.get_file(file_id=update.message.photo[-1].file_id)
        img.download(f'{img_type}_{user_id}.jpg')
        valid = True
    return valid


def start_handler(update, context):
    logging.debug('Starting /start handler')
    logging.info(f'Start handler called by user {update.message.from_user.id}')
    """Start the conversation and ask user for input."""
    update.message.reply_text(
        'Hi! I\'m the _Neural Style Transfer bot_. I customize images using advanced machine learning.\n'
        'All I need is that you send me a source and a target images.\n\n'
        'The *source image* contains the style you want to transfer.\n'
        'The *target image* has the structure content you want to apply the style.\n'
        'You can create lots of awesome combinations as the ones found [here](https://miro.medium.com/max/2166/1*8bbp3loQjkLXaIm_QBfD8w.jpeg)\n\n'
        'Why don\'t you tell me which one you want to pass me first?',
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN
    )

    return CHOOSING


def choice_handler(update, context):
    logging.debug('Starting choice handler')
    text = update.message.text.lower()
    logging.info(f'User {update.message.from_user.id} selected {text}')
    context.user_data['choice'] = text
    update.message.reply_text(f'Send me the {text} image')

    return SENDING_IMG


def img_handler(update, context):
    logging.debug('Starting img handler')
    user_id = update.message.from_user.id
    choice = context.user_data['choice']

    if not download_image(update, context, user_id, img_type=choice):
        return

    update.message.reply_text(f'{choice.capitalize()} image received.', reply_markup=markup)

    return CHOOSING


def transfer_handler(update, context):
    logging.debug('Starting transfer handler')
    user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']
    
    user_id = update.message.from_user.id

    update.message.reply_text('Stylizing your image...')

    logging.debug('Loading style image')
    style_img   = image_loader(f'source_{user_id}.jpg')
    logging.debug('Loading content image')
    content_img = image_loader(f'target_{user_id}.jpg')

    content_size = content_img.size

    tensor_img = transfer(style_img, content_img)
    image = unload_image(tensor_img)

    image = image.resize(content_size, Image.ANTIALIAS)

    bio = BytesIO()
    bio.name = f'result_{user_id}.jpeg'
    image.save(bio, 'JPEG')
    bio.seek(0)

    logging.debug('Sending image to user')
    update.message.reply_text('Here goes your stylized image...')
    context.bot.send_photo(update.message.chat_id, bio)

    logging.debug('Deleting user\'s images')
    os.remove(f'source_{user_id}.jpg')
    os.remove(f'target_{user_id}.jpg')

    logging.debug('Cleaning user\'s data')
    user_data.clear()
    return ConversationHandler.END


def help_handler(update, context):
    logging.debug('Starting /help handler')
    response = [
        'Hello, I\'m _Neural Style Transfer Bot_!\n',
        'I apply the style from a source image to the content of a target image.',
        '\n\n*Commands*\n\n',
        '/start - initiate a new style transfering\n'
        '/help - bot command helper\n'
    ]

    update.message.reply_text(''.join(response), parse_mode=ParseMode.MARKDOWN)


def main():
    # Load sensible content
    config = dotenv_values('.env')

    # Create the Updater and pass it the bot's token
    updater = Updater(config['TOKEN'])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states STYLE, CONTENT and TRANSFER
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_handler)],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('^((S|s)ource|(T|t)arget)$'), choice_handler),
            ],
            SENDING_IMG: [
                MessageHandler(Filters.photo, img_handler)
            ]
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), transfer_handler)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('help', help_handler))

    # Start the Bot
    updater.start_polling()
    logger.info('=== Bot running! ===')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    logger.info('=== Bot shutting down! ===')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Neural Style Transfer Bot')
    parser.add_argument('--debug', action='store_true', help='Debug flag')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)

    main()
