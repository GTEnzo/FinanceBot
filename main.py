from config import BOT_TOKEN
from data.commands import *

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('set_balance', set_balance))
    application.add_handler(CommandHandler('add_to_balance', add_to_balance))
    application.add_handler(CommandHandler('set_limit', set_limit))
    application.add_handler(CommandHandler('set_general_limit', set_general_limit))
    application.add_handler(CommandHandler('remove_limit', remove_limit))
    application.add_handler(CommandHandler('remove_general_limit', remove_general_limit))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('cancel', cancel))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    )

    application.run_polling()


if __name__ == '__main__':
    main()
