import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from telegram import ReplyKeyboardMarkup

USER_STATES = {}
BALANCE = 0
LIMIT = 'Не установлен'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

reply_keyboard = [
    ['/profile'],
    ['/set_balance'],
    ['/set_limit'],
    ['/stats']
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


async def start(update, context):
    user = update.effective_user
    await update.message.reply_html(
        f'Привет, {user.mention_html()}! Я FinanceBot!',
        reply_markup=markup
    )


async def profile(update, context):
    user = update.effective_user
    await update.message.reply_html(
        f'{user.mention_html()}\n'
        f'\n'
        f'Баланс: {BALANCE}\n'
        f'Лимит: {LIMIT}\n'
    )


async def set_balance(update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = 'waiting_for_input'

    await update.message.reply_text(
        'Напишите ваш текущий баланс.'
    )
    await update.message.get_balance(update, context)


async def get_balance(update, context):
    global BALANCE

    user_id = update.effective_user.id
    if USER_STATES.get(user_id) != 'waiting_for_input':
        return

    text = update.message.text
    if text.isdigit():
        await update.message.reply_text(
            f'Текущий баланс: {text}.'
        )
        BALANCE = int(text)
    else:
        await update.message.reply_text(
            'Пожалуйста, введите число!'
        )
        await set_balance(update, context)

    del USER_STATES[user_id]


async def set_limit(update, context):
    await update.message.reply_text(
        'Напишите лимит, который хотите установить.'
    )


async def stats(update, context):
    await update.message.reply_text(
        'Ваша статистика.'
    )


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('set_balance', set_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_balance))
    application.add_handler(CommandHandler('set_limit', set_limit))
    application.add_handler(CommandHandler('stats', stats))
    application.run_polling()


if __name__ == '__main__':
    main()
