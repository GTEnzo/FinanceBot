from data.ORM.services import *
from data.charts_generator import *
from data.constants_and_etc import *
from data.limits_functions import *

import requests
from datetime import datetime
from telegram import Update


async def start(update: Update, context):
    user = update.effective_user
    create_or_import_user(f'{user['id']}')
    USER_STATES[user.id] = UserState.NONE
    await update.message.reply_html(
        f'<b>Привет, {user.mention_html()}! Я FinanceBot!</b>\n\n'
        'Используйте кнопки ниже, чтобы управлять балансом и лимитами.',
        reply_markup=markup
    )


async def profile(update: Update, context):
    user = update.effective_user
    data = USER_DATA.get(user.id, {})

    balance = import_balance(f'{user['id']}')
    general_limit = import_general_limit(f'{user['id']}')
    limits = data.get('limits', {})
    spent = {category: limit_data['spent'] for category, limit_data in limits.items()}

    balance_info = f'{float(balance):.2f}' if balance is not None else 'не задан'
    general_limit_info = f'{general_limit[0]} (потрачено: {general_limit[1]})' if general_limit[0] else 'не задан'
    limit_info = '\n'.join(
        [f'{category}: {limit_data['limit']} (потрачено: {spent[category]})' for category, limit_data in
         limits.items()]) if limits else 'не заданы'

    await update.message.reply_html(
        f'{user.mention_html()}\n\nБаланс: {balance_info}\n\nОбщий лимит: {general_limit_info}\n\nЛимиты:\n{limit_info}'
    )


async def stats(update: Update, context):
    user_id = update.effective_user.id
    user_data = USER_DATA.get(user_id, {})

    if user_data.get('limits'):
        try:
            chart_url = generate_chart_url(user_data)
            if chart_url:
                response = requests.head(chart_url, timeout=5)
                if response.status_code == 200:
                    await update.message.reply_photo(
                        photo=chart_url,
                        caption='📊 <b>Ваши расходы по категориям</b>',
                        parse_mode='HTML'
                    )
                else:
                    raise Exception(f'❌ Сервер вернул код {response.status_code}')
        except Exception as e:
            print(f'[Ошибка графика] {e}')
            await update.message.reply_text(
                '❌ Не удалось загрузить график. Показываю текстовую статистику...'
            )

    report = ['<b>📊 Статистика</b>']

    balance = import_balance(f'{user_id}')
    if balance:
        report.append(f'\n💰 <b>Баланс:</b> {balance:.2f} ₽')

    general_limit = import_general_limit(f'{user_id}')
    if general_limit[0]:
        status = '⚠️' if general_limit[1] > general_limit[0] else '✅'
        period_end = convert_time_format(general_limit[3])

        report.append(f'\n🧾 <b>Общий лимит:</b> {general_limit[1]:.2f}/{general_limit[0]:.2f} ₽ {status}')
        report.append(f'📅 Дата окончания: {period_end}')

    if user_data.get('limits'):
        report.append('\n📌 <b>Лимиты по категориям:</b>')

        for cat, data in user_data['limits'].items():
            status = '⚠️' if data['spent'] > data['limit'] else '✅'
            period_end = data.get('period_end', 'не установлена')
            if isinstance(period_end, datetime):
                period_end = period_end.strftime('%d.%m.%Y %H:%M')

            report.append(f'\n• <b>{cat.capitalize()}</b>: {data['spent']:.2f}/{data['limit']:.2f} ₽ {status}')
            report.append(f'  📅 Дата окончания: {period_end}')

    if report == ['<b>📊 Статистика</b>']:
        report = ['❌ Нет данных для отображения']

    await update.message.reply_text(
        '\n'.join(report),
        parse_mode='HTML',
        reply_markup=markup
    )


async def set_balance(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_BALANCE
    await update.message.reply_text(
        'Напишите ваш текущий баланс (числовое значение). Для отмены введите /cancel.'
    )


async def add_to_balance(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.ADDING_TO_BALANCE
    await update.message.reply_text(
        'Напишите ваше пополнение баланса (числовое значение). Для отмены введите /cancel.'
    )


async def set_limit(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_LIMIT_AMOUNT
    await update.message.reply_text(
        'Укажите категорию лимита (например, "еда") и сумму лимита (числовое значение), например "еда 100". Для отмены введите /cancel.'
    )


async def set_general_limit(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_AMOUNT
    await update.message.reply_text(
        'Укажите сумму общего лимита (числовое значение). Для отмены введите /cancel.'
    )


async def cancel(update: Update, context):
    user_id = update.effective_user.id
    USER_STATES[user_id] = UserState.NONE
    await update.message.reply_text(
        'Операция отменена.', reply_markup=markup
    )


async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    update_limits()
    text = update.message.text.strip()
    state = USER_STATES.get(user_id, UserState.NONE)

    if text == COMMAND_CANCEL:
        await cancel(update, context)
        return

    if state == UserState.SETTING_BALANCE:
        try:
            new_balance = float(text.replace(',', '.'))
            USER_STATES[user_id] = UserState.NONE
            update_balance(user_id, new_balance)
            await update.message.reply_text(
                f'Текущий баланс успешно обновлён: {new_balance:.2f}.', reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите число. Для отмены введите /cancel.'
            )
        return

    if state == UserState.ADDING_TO_BALANCE:
        try:
            adding = float(text.replace(',', '.'))
            USER_STATES[user_id] = UserState.NONE
            to_balance(user_id, adding)
            await update.message.reply_text(
                f'Текущий баланс успешно пополнен на {adding}.', reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите число. Для отмены введите /cancel.'
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
                'Теперь выберите период для этого лимита:', reply_markup=period_markup
            )
        except ValueError:
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите категорию и сумму лимита. Например: "еда 100".'
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
                '❌ Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    if state == UserState.SETTING_GENERAL_LIMIT_AMOUNT:
        try:
            new_general_limit = float(text.replace(',', '.'))
            USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_PERIOD
            update_general_limit(user_id, new_general_limit, -1)
            await update.message.reply_text(
                'Теперь выберите период для общего лимита:', reply_markup=period_markup
            )
        except ValueError:
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите сумму общего лимита. Например: "100".'
            )
        return

    if state == UserState.SETTING_GENERAL_LIMIT_PERIOD:
        new_period = text.lower()
        if new_period in LIMIT_PERIODS:
            USER_STATES[user_id] = UserState.NONE
            update_general_limit_period(user_id, new_period, datetime.now())
            await update.message.reply_text(
                f'Период для общего лимита установлен: {new_period}.', reply_markup=markup
            )
        else:
            await update.message.reply_text(
                '❌ Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    try:
        spend_amount = float(text.replace(',', '.'))

        balance = import_balance(user_id)
        general_limit = import_general_limit(user_id)

        new_balance = balance - spend_amount

        if new_balance - spend_amount < 0:
            await update.message.reply_text(
                f'⚠️ Внимание! Ваш баланс меньше нуля.'
            )
        update_balance(user_id, balance - spend_amount)

        if general_limit[0]:
            update_general_limit(user_id, general_limit[0], spend_amount)
            general_limit[1] += spend_amount

            if general_limit[1] > general_limit[0]:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit[0]:.2f}.\n'
                    f'Потрачено: {general_limit[1]:.2f}.', reply_markup=markup
                )

        await update.message.reply_text(
            f'Учтена трата: {spend_amount:.2f}\nНовый баланс: {balance - spend_amount:.2f}', reply_markup=markup
        )
    except ValueError:
        try:
            category, spend_str = text.split()
            spend_amount = float(spend_str.replace(',', '.'))

            user_data = USER_DATA.setdefault(user_id, {})
            balance = import_balance(user_id)

            if balance is None:
                await update.message.reply_text(
                    '❌ Баланс не задан. Сначала задайте баланс через /set_balance.'
                )
                return

            if 'limits' not in user_data or category not in user_data['limits']:
                await update.message.reply_text(
                    f'❌ Категория "{category}" не найдена. Сначала установите лимит для этой категории через /set_limit.',
                    reply_markup=markup
                )
                return

            limit_data = user_data['limits'][category]
            limit_data['spent'] += spend_amount

            if limit_data['spent'] > limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный лимит {limit_data['limit']:.2f} для категории "{category}".\n'
                    f'Потрачено: {limit_data['spent']:.2f}.'
                )

            await update.message.reply_text(
                f'Учтена трата: {spend_amount:.2f}\n'
                f'Категория: {category}\n'
                f'Новый баланс: {balance - spend_amount:.2f}',
                reply_markup=markup
            )
            update_balance(user_id, balance - spend_amount),
            general_limit = import_general_limit(user_id)
            update_general_limit(user_id, general_limit[0], spend_amount)

        except ValueError:
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите категорию и сумму. Например: "еда 100".',
                reply_markup=markup
            )