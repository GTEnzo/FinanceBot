from config import BOT_TOKEN
from constants_and_etc import *

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import requests
import json
from urllib.parse import quote


def calculate_period_end(period_key, from_date):
    if period_key == "день":
        return from_date + timedelta(days=1)
    elif period_key == "неделя":
        return from_date + timedelta(days=7)
    elif period_key == "месяц":
        return from_date + timedelta(days=30)
    elif period_key == "год":
        return from_date + timedelta(days=365)
    else:
        return from_date


def generate_chart_url(user_data):
    limits = user_data.get('limits', {})
    if not limits:
        return None

    labels = []
    spent_values = []
    background_colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)'
    ]

    for category, data in limits.items():
        labels.append(category)
        spent_values.append(float(data['spent']))

    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": spent_values,
                "backgroundColor": background_colors[:len(labels)]
            }]
        },
        "options": {
            "plugins": {
                "title": {
                    "display": True,
                    "text": "Ваши расходы по категориям",
                    "font": {"size": 16}
                },
                "legend": {
                    "position": "right",
                    "labels": {"font": {"size": 12}}
                }
            }
        }
    }

    try:
        json_config = json.dumps(chart_config, ensure_ascii=False)
        base_url = "https://quickchart.io/chart"
        return f"{base_url}?c={quote(json_config)}"
    except Exception as e:
        print(f"Ошибка при генерации URL графика: {e}")
        return None


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = USER_DATA.get(user_id, {})

    if not user_data:
        await update.message.reply_text("❌ Нет данных для отображения.")
        return

    chart_url = None
    if user_data.get('limits'):
        try:
            chart_url = generate_chart_url(user_data)
            if chart_url:
                response = requests.head(chart_url, timeout=5)
                if response.status_code == 200:
                    await update.message.reply_photo(
                        photo=chart_url,
                        caption="📊 Ваши расходы по категориям",
                        parse_mode="HTML"
                    )
                else:
                    raise Exception(f"Сервер вернул код {response.status_code}")
        except Exception as e:
            print(f"[Ошибка графика] {e}")
            await update.message.reply_text(
                "⚠️ Не удалось загрузить график. Показываю текстовую статистику..."
            )

    report = ["<b>📊 Статистика</b>"]

    balance = user_data.get('balance', 0)
    report.append(f"\n💰 <b>Баланс:</b> {balance:.2f} ₽")

    if 'general_limit' in user_data:
        gl = user_data['general_limit']
        status = "⚠️ <b>ПРЕВЫШЕН</b>" if gl['spent'] > gl['limit'] else "✅ в норме"
        period_end = gl.get('period_end', 'не установлена')
        if isinstance(period_end, datetime):
            period_end = period_end.strftime("%d.%m.%Y")

        report.append(f"\n🧾 <b>Общий лимит:</b> {gl['spent']:.2f}/{gl['limit']:.2f} ₽ {status}")
        report.append(f"📅 <i>Дата окончания:</i> {period_end}")

    if user_data.get('limits'):
        report.append("\n\n📌 <b>Лимиты по категориям:</b>")
        for cat, data in user_data['limits'].items():
            status = "⚠️" if data['spent'] > data['limit'] else "✅"
            period_end = data.get('period_end', 'не установлена')
            if isinstance(period_end, datetime):
                period_end = period_end.strftime("%d.%m.%Y")

            report.append(f"\n• <b>{cat.capitalize()}</b>: {data['spent']:.2f}/{data['limit']:.2f} ₽ {status}")
            report.append(f"  📅 <i>Дата окончания:</i> {period_end}")

    await update.message.reply_text(
        "\n".join(report),
        parse_mode="HTML",
        reply_markup=markup
    )


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
        f'{user.mention_html()}\n\nБаланс: {balance} 💰\n\nЛимиты:\n{limit_info}'
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

    if text == COMMAND_CANCEL:
        await cancel(update, context)
        return

    if state == UserState.SETTING_BALANCE:
        try:
            balance = float(text.replace(',', '.'))
            USER_DATA.setdefault(user_id, {})['balance'] = balance
            USER_STATES[user_id] = UserState.NONE
            await update.message.reply_text(
                f'Текущий баланс успешно обновлён: {balance:.2f} 💰', reply_markup=markup
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
                'Теперь выберите период для этого лимита:', reply_markup=period_markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите категорию и сумму лимита. Например: "еда 100".'
            )
        return

    if state == UserState.SETTING_GENERAL_LIMIT_AMOUNT:
        try:
            limit = float(text.replace(',', '.'))
            user_data = USER_DATA.setdefault(user_id, {})
            user_data.setdefault('general_limit', {'limit': limit, 'spent': 0.0, 'period': None, 'period_end': None})
            USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_PERIOD
            await update.message.reply_text(
                'Теперь выберите период для общего лимита:', reply_markup=period_markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите сумму общего лимита. Например: "100".'
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
                user_data['general_limit']['period_end'] = calculate_period_end(LIMIT_PERIODS[period], datetime.now())
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

        user_data['balance'] = balance - spend_amount

        if 'general_limit' in user_data:
            general_limit_data = user_data['general_limit']
            general_limit_data['spent'] += spend_amount

            if general_limit_data['spent'] > general_limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit_data["limit"]:.2f}.\n'
                    f'Потрачено: {general_limit_data["spent"]:.2f}.', reply_markup=markup
                )

        await update.message.reply_text(
            f'Учтена трата: {spend_amount:.2f} 💸\nНовый баланс: {balance - spend_amount:.2f} 💰', reply_markup=markup
        )
    except ValueError:
        try:
            category, spend_str = text.split()
            spend_amount = float(spend_str.replace(',', '.'))
            user_data = USER_DATA.setdefault(user_id, {})
            balance = user_data.get('balance')

            if balance is None:
                await update.message.reply_text(
                    'Баланс не задан. Сначала задайте баланс через /set_balance.'
                )
                return

            if 'limits' not in user_data or category not in user_data['limits']:
                await update.message.reply_text(
                    f'❌ Категория "{category}" не найдена. Сначала установите лимит для этой категории через /set_limit.',
                    reply_markup=markup
                )
                return

            user_data['balance'] = balance - spend_amount

            if 'general_limit' in user_data:
                general_limit_data = user_data['general_limit']
                general_limit_data['spent'] += spend_amount
                if general_limit_data['spent'] > general_limit_data['limit']:
                    await update.message.reply_text(
                        f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit_data["limit"]:.2f}.\n'
                        f'Потрачено: {general_limit_data["spent"]:.2f}.'
                    )

            limit_data = user_data['limits'][category]
            limit_data['spent'] += spend_amount

            if limit_data['spent'] > limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный лимит {limit_data["limit"]:.2f} для категории "{category}".\n'
                    f'Потрачено: {limit_data["spent"]:.2f}.'
                )

            await update.message.reply_text(
                f'Учтена трата: {spend_amount:.2f} 💸\n'
                f'Категория: {category}\n'
                f'Новый баланс: {balance - spend_amount:.2f} 💰',
                reply_markup=markup
            )
        except ValueError:
            await update.message.reply_text(
                'Неверный формат. Пожалуйста, введите категорию и сумму. Например: "еда 100".',
                reply_markup=markup
            )


def main():
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