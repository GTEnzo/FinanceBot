import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN

COMMAND_START = '/start'
COMMAND_PROFILE = '/profile'
COMMAND_SET_BALANCE = '/set_balance'
COMMAND_SET_LIMIT = '/set_limit'
COMMAND_STATS = '/stats'
COMMAND_CANCEL = '/cancel'

PERIOD_DAY = 'День'
PERIOD_WEEK = 'Неделя'
PERIOD_MONTH = 'Месяц'


class UserState:
    NONE = 'none'
    SETTING_BALANCE = 'setting_balance'
    SETTING_LIMIT = 'setting_limit'
    SETTING_LIMIT_PERIOD = 'setting_limit_period'


USER_STATES = {}
USER_DATA = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

reply_keyboard = [
    [COMMAND_START],
    [COMMAND_PROFILE],
    [COMMAND_SET_BALANCE, COMMAND_SET_LIMIT],
    [COMMAND_STATS],
    [COMMAND_CANCEL]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

period_keyboard = [
    [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH],
    [COMMAND_CANCEL]
]
period_markup = ReplyKeyboardMarkup(period_keyboard, resize_keyboard=True)


async def start(update: Update, context):
    user = update.effective_user
    USER_STATES[user.id] = UserState.NONE
    await update.message.reply_html(
        f'Привет, {user.mention_html()}! Я FinanceBot!\n'
        'Используйте клавиатуру, чтобы управлять балансом и лимитами.',
        reply_markup=markup
    )


async def profile(update: Update, context):
    user = update.effective_user
    data = USER_DATA.get(user.id, {})
    balance = data.get('balance', 'не задан')

    limit_text = "не заданы"
    if 'limits' in data:
        limit_text = "\n".join([f"{period}: {amount:.2f}" for period, amount in data['limits'].items()])

    await update.message.reply_html(
        f'{user.mention_html()}\n\nБаланс: {balance}\nЛимиты:\n{limit_text}',
        reply_markup=markup
    )


async def set_balance(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_BALANCE
    await update.message.reply_text(
        'Напишите ваш текущий баланс (число). Для отмены введите /cancel.',
        reply_markup=markup
    )


async def set_limit(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_LIMIT_PERIOD
    await update.message.reply_text(
        'Выберите период для установки лимита:',
        reply_markup=period_markup
    )


async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = USER_STATES.get(user_id, UserState.NONE)

    if text.lower() == COMMAND_CANCEL:
        await cancel(update, context)
        return

    if state == UserState.SETTING_BALANCE:
        try:
            balance = float(text)
            USER_DATA.setdefault(user_id, {})['balance'] = balance
            USER_STATES[user_id] = UserState.NONE
            await update.message.reply_text(
                f'Текущий баланс успешно обновлён: {balance:.2f}',
                reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите ЧИСЛО. Для отмены введите /cancel.',
                reply_markup=markup
            )
        return

    if state == UserState.SETTING_LIMIT_PERIOD:
        if text in [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH]:
            context.user_data['limit_period'] = text
            USER_STATES[user_id] = UserState.SETTING_LIMIT
            await update.message.reply_text(
                f'Укажите значение лимита на {text.lower()} (число). Для отмены введите /cancel.',
                reply_markup=markup
            )
        else:
            await update.message.reply_text(
                'Пожалуйста, выберите период из предложенных вариантов.',
                reply_markup=period_markup
            )
        return

    if state == UserState.SETTING_LIMIT:
        try:
            limit = float(text)
            period = context.user_data.get('limit_period')
            if period:
                USER_DATA.setdefault(user_id, {}).setdefault('limits', {})[period] = limit
                USER_STATES[user_id] = UserState.NONE
                del context.user_data['limit_period']
                await update.message.reply_text(
                    f'Лимит на {period.lower()} успешно установлен: {limit:.2f}',
                    reply_markup=markup
                )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите ЧИСЛО. Для отмены введите /cancel.',
                reply_markup=markup
            )
        return

    try:
        spend_amount = float(text)
        user_data = USER_DATA.setdefault(user_id, {})
        balance = user_data.get('balance')
        if balance is None:
            await update.message.reply_text(
                'Баланс не задан. Задайте через /set_balance.',
                reply_markup=markup
            )
            return

        if 'limits' in user_data:
            for period, limit in user_data['limits'].items():
                if spend_amount > limit:
                    await update.message.reply_text(
                        f'Внимание! Трата превышает лимит ({period}: {limit:.2f})',
                        reply_markup=markup
                    )

        new_balance = balance - spend_amount
        user_data['balance'] = new_balance
        await update.message.reply_text(
            f'Трата: {spend_amount:.2f}\nНовый баланс: {new_balance:.2f}',
            reply_markup=markup
        )
    except ValueError:
        await update.message.reply_text(
            'Пожалуйста, используйте кнопки меню для управления балансом и лимитом '
            'или отправьте числовое значение для списания средств.',
            reply_markup=markup
        )


async def stats(update: Update, context):
    user_id = update.effective_user.id
    data = USER_DATA.get(user_id, {})
    balance = data.get('balance', 'не задан')
    limit_text = "не заданы"
    if 'limits' in data:
        limit_text = "\n".join([f"{period}: {amount:.2f}" for period, amount in data['limits'].items()])

    await update.message.reply_html(
        f'Баланс: {balance}\nЛимиты:\n{limit_text}',
        reply_markup=markup
    )


async def cancel(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.NONE
    if 'limit_period' in context.user_data:
        del context.user_data['limit_period']
    await update.message.reply_text(
        'Отменено.',
        reply_markup=markup
    )


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('set_balance', set_balance))
    application.add_handler(CommandHandler('set_limit', set_limit))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('cancel', cancel))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    )

    application.run_polling()


if __name__ == '__main__':
    main()