from config import BOT_TOKEN

import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

COMMAND_START = '/start'
COMMAND_PROFILE = '/profile'
COMMAND_SET_BALANCE = '/set_balance'
COMMAND_SET_LIMIT = '/set_limit'
COMMAND_SET_GENERAL_LIMIT = '/set_general_limit'
COMMAND_STATS = '/stats'
COMMAND_CANCEL = '/cancel'


class UserState:
    NONE = 'none'
    SETTING_BALANCE = 'setting_balance'
    SETTING_LIMIT_AMOUNT = 'setting_limit_amount'
    SETTING_LIMIT_PERIOD = 'setting_limit_period'
    SETTING_GENERAL_LIMIT_AMOUNT = 'setting_general_limit_amount'
    SETTING_GENERAL_LIMIT_PERIOD = 'setting_general_limit_period'


LIMIT_PERIODS = {
    "день": "day",
    "неделя": "week",
    "месяц": "month",
    "год": "year"
}

USER_STATES = {}
USER_DATA = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

reply_keyboard = [
    [COMMAND_START],
    [COMMAND_PROFILE, COMMAND_STATS],
    [COMMAND_SET_BALANCE],
    [COMMAND_SET_LIMIT, COMMAND_SET_GENERAL_LIMIT],
    [COMMAND_CANCEL]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)


def calculate_period_end(period_key: str, from_date: datetime) -> datetime:
    if period_key == "day":
        return from_date + timedelta(days=1)
    elif period_key == "week":
        return from_date + timedelta(weeks=1)
    elif period_key == "month":
        return from_date + timedelta(days=30)
    elif period_key == "year":
        return from_date + timedelta(days=365)
    else:
        return from_date


async def start(update: Update, context):
    user = update.effective_user
    USER_STATES[user.id] = UserState.NONE
    await update.message.reply_html(
        f'Привет, {user.mention_html()}! Я FinanceBot!\n'
        'Используйте кнопки ниже, чтобы управлять балансом и лимитами.',
        reply_markup=markup
    )


async def profile(update: Update, context):
    user = update.effective_user
    data = USER_DATA.get(user.id, {})
    balance = data.get('balance', 'не задан')
    limits = data.get('limits', {})
    spent = {category: limit_data['spent'] for category, limit_data in limits.items()}

    limit_info = "\n".join(
        [f"{category}: {limit_data['limit']} (потрачено: {spent[category]})" for category, limit_data in
         limits.items()]) if limits else "не заданы"

    await update.message.reply_html(
        f'{user.mention_html()}\n\nБаланс: {balance}\nЛимиты:\n{limit_info}'
    )


async def set_balance(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_BALANCE
    await update.message.reply_text(
        'Напишите ваш текущий баланс (числовое значение). Для отмены введите /cancel.'
    )


async def set_limit(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_LIMIT_AMOUNT
    await update.message.reply_text(
        'Укажите категорию лимита (например, "еда") и сумму лимита (числовое значение). Для отмены введите /cancel.'
    )


async def set_general_limit(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_AMOUNT
    await update.message.reply_text(
        'Укажите сумму общего лимита (числовое значение). Для отмены введите /cancel.'
    )


async def set_limit_period(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_LIMIT_PERIOD
    await update.message.reply_text(
        'Выберите период для установки лимита: день, неделя, месяц или год. Например: "неделя".'
    )


async def set_general_limit_period(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_PERIOD
    await update.message.reply_text(
        'Выберите период для общего лимита: день, неделя, месяц или год. Например: "неделя".'
    )


async def cancel(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.NONE
    await update.message.reply_text(
        'Операция отменена.', reply_markup=markup
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
            balance = float(text.replace(',', '.'))
            USER_DATA.setdefault(user_id, {})['balance'] = balance
            USER_STATES[user_id] = UserState.NONE
            await update.message.reply_text(
                f'Текущий баланс успешно обновлён: {balance:.2f}', reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите число. Для отмены введите /cancel.'
            )
        return

    if state == UserState.SETTING_LIMIT_AMOUNT:
        try:
            category, limit_str = text.split()
            limit = float(limit_str.replace(',', '.'))
            user_data = USER_DATA.setdefault(user_id, {})
            user_data.setdefault('limits', {})[category] = {'limit': limit, 'spent': 0.0, 'period': None,
                                                            'period_end': None}
            USER_STATES[user_id] = UserState.SETTING_LIMIT_PERIOD
            await update.message.reply_text(
                'Теперь выберите период для этого лимита: день, неделя, месяц или год.', reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите категорию и сумму лимита. Например: "еда 200".'
            )
        return

    if state == UserState.SETTING_GENERAL_LIMIT_AMOUNT:
        try:
            limit = float(text.replace(',', '.'))
            user_data = USER_DATA.setdefault(user_id, {})
            user_data.setdefault('general_limit', {'limit': limit, 'spent': 0.0, 'period': None, 'period_end': None})
            USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_PERIOD
            await update.message.reply_text(
                'Теперь выберите период для общего лимита: день, неделя, месяц или год.', reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите сумму общего лимита. Например: "200".'
            )
        return

    if state == UserState.SETTING_LIMIT_PERIOD:
        period = text.lower()
        if period in LIMIT_PERIODS:
            user_data = USER_DATA.setdefault(user_id, {})
            for category in user_data.get('limits', {}):
                if user_data['limits'][category]['period'] is None:
                    user_data['limits'][category]['period'] = LIMIT_PERIODS[period]
                    user_data['limits'][category]['period_end'] = calculate_period_end(LIMIT_PERIODS[period],
                                                                                       datetime.now())
            USER_STATES[user_id] = UserState.NONE
            await update.message.reply_text(
                f'Период для лимита установлен: {period}.', reply_markup=markup
            )
        else:
            await update.message.reply_text(
                'Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    if state == UserState.SETTING_GENERAL_LIMIT_PERIOD:
        period = text.lower()
        if period in LIMIT_PERIODS:
            user_data = USER_DATA.setdefault(user_id, {})
            if 'general_limit' in user_data:
                user_data['general_limit']['period'] = LIMIT_PERIODS[period]
                user_data['general_limit']['period_end'] = calculate_period_end(LIMIT_PERIODS[period],
                                                                                datetime.now())
            USER_STATES[user_id] = UserState.NONE
            await update.message.reply_text(
                f'Период для общего лимита установлен: {period}.', reply_markup=markup
            )
        else:
            await update.message.reply_text(
                'Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    try:
        spend_amount = float(text.replace(',', '.'))
        user_data = USER_DATA.setdefault(user_id, {})
        balance = user_data.get('balance')
        if balance is None:
            await update.message.reply_text(
                'Баланс не задан. Сначала задайте баланс через /set_balance.'
            )
            return

        new_balance = balance - spend_amount
        user_data['balance'] = new_balance

        if 'general_limit' in user_data:
            general_limit_data = user_data['general_limit']
            general_limit_data['spent'] += spend_amount

            if general_limit_data['spent'] > general_limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit_data["limit"]:.2f}.\n'
                    f'Потрачено: {general_limit_data["spent"]:.2f}.', reply_markup=markup
                )

        for category in user_data.get('limits', {}):
            limit_data = user_data['limits'][category]
            limit_data['spent'] += spend_amount

            if limit_data['spent'] > limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный лимит {limit_data["limit"]:.2f} для категории "{category}".\n'
                    f'Потрачено: {limit_data["spent"]:.2f}.', reply_markup=markup
                )

        await update.message.reply_text(
            f'Учтена трата: {spend_amount:.2f}\nНовый баланс: {new_balance:.2f}', reply_markup=markup
        )
    except ValueError:
        try:
            category, spend_str = text.split()
            spend_amount = float(spend_str.replace(',', '.'))
            user_data = USER_DATA.setdefault(user_id, {})
            limits = user_data.get('limits', {})
            if category in limits:
                limit_data = limits[category]
                limit_data['spent'] += spend_amount

                if limit_data['spent'] > limit_data['limit']:
                    await update.message.reply_text(
                        f'⚠️ Внимание! Вы превысили установленный лимит {limit_data["limit"]:.2f} для категории "{category}".\n'
                        f'Потрачено: {limit_data["spent"]:.2f}.', reply_markup=markup
                    )
                else:
                    await update.message.reply_text(
                        f'Сумма {spend_amount:.2f} вычтена из лимита категории "{category}".', reply_markup=markup
                    )
            else:
                await update.message.reply_text(
                    f'Категория "{category}" не найдена. Пожалуйста, проверьте название категории.'
                )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите категорию и сумму. Например: "еда 50".'
            )


async def stats(update: Update, context):
    user_id = update.effective_user.id
    user_data = USER_DATA.get(user_id, {})
    balance = user_data.get('balance', None)
    limits = user_data.get('limits', {})

    if balance is None or not limits:
        await update.message.reply_text(
            'Данные по балансу или лимитам не заданы. Пожалуйста, сначала укажите их.'
        )
        return

    report = "📊 Статистика по вашему бюджету:\n\n"
    for category, limit_data in limits.items():
        limit = limit_data['limit']
        spent = limit_data['spent']
        period_end = limit_data['period_end']

        period_end_str = period_end.strftime("%Y-%m-%d %H:%M:%S") if period_end else "не установлен"

        report += (f"Категория: {category}\n"
                   f"Лимит: {limit:.2f}\n"
                   f"Потрачено: {spent:.2f}\n"
                   f"Дата обновления лимита: {period_end_str}\n\n")

    if 'general_limit' in user_data:
        general_limit_data = user_data['general_limit']
        general_limit = general_limit_data['limit']
        general_spent = general_limit_data['spent']
        general_period_end = general_limit_data['period_end']
        general_period_end_str = general_period_end.strftime(
            "%Y-%m-%d %H:%M:%S") if general_period_end else "не установлен"

        report += (f"Общий лимит:\n"
                   f"Лимит: {general_limit:.2f}\n"
                   f"Потрачено: {general_spent:.2f}\n"
                   f"Дата обновления общего лимита: {general_period_end_str}\n\n")

    await update.message.reply_text(report, reply_markup=markup)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("set_balance", set_balance))
    application.add_handler(CommandHandler("set_limit", set_limit))
    application.add_handler(CommandHandler("set_general_limit", set_general_limit))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("cancel", cancel))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
