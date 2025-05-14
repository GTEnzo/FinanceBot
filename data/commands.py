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
    # получаем объект пользователя
    user = update.effective_user
    create_or_import_user(f'{user.id}')

    # получаем финансовые данные
    balance = import_balance(f'{user.id}')
    general_limit = import_general_limit(f'{user.id}')
    data = import_limits(user.id)
    if data:
        data = data.replace("'", '"')
        user_data = json.loads(data)
        limits = user_data.get('limits', {})
    else:
        limits = None

    # формируем текстовую часть сообщения
    balance_info = f'{float(balance):.2f} ₽' if balance is not None else 'Не задан'
    general_limit_info = f'{general_limit[0]:.2f} ₽' if general_limit[0] else 'Не задан'

    # формируем список лимитов (только суммы без трат)
    limit_info = [f'• {category.capitalize()}: {limit_data['limit']:.2f} ₽'
                  for category, limit_data in limits.items()] if limits else None

    caption = (
            f'👤 {user.mention_html()}\n\n'
            f'💰 <b>Баланс:</b> {balance_info}\n\n'
            f'🧾 <b>Общий лимит:</b> {general_limit_info}\n\n'
            f'📌 <b>Лимиты по категориям:</b>\n' +
            ('\n'.join(limit_info) if limit_info else 'Не заданы')
    )

    # пытаемся получить и отправить аватарку с текстом
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file = await photos.photos[0][0].get_file()
            await update.message.reply_photo(
                photo=photo_file.file_id,
                caption=caption,
                parse_mode='HTML',
                reply_markup=markup
            )
        else:
            # если аватарки нет, отправляем только текст
            await update.message.reply_text(
                caption,
                parse_mode='HTML',
                reply_markup=markup
            )
    except Exception as e:
        print(f'Ошибка при обработке фото профиля: {e}')
        await update.message.reply_text(
            caption,
            parse_mode='HTML',
            reply_markup=markup
        )


async def stats(update: Update, context):
    # получаем ID пользователя, который вызвал команду
    user_id = update.effective_user.id

    # получаем список его лимитов
    data = import_limits(user_id)
    if data:
        data = data.replace("'", '"')
        user_data = json.loads(data)
    else:
        user_data = {}

    # проверяем, есть ли у пользователя установленные лимиты
    if user_data.get('limits'):
        try:
            # генерируем URL графика на основе данных пользователя
            chart_url = generate_chart_url(user_data)

            # если URL получен успешно
            if chart_url:
                # проверяем доступность графика (HEAD-запрос)
                response = requests.head(chart_url, timeout=5)

                # если сервер вернул код 200 (OK)
                if response.status_code == 200:
                    # отправляем пользователю график в виде фото
                    await update.message.reply_photo(
                        photo=chart_url,
                        caption='📊 <b>Ваши расходы по категориям</b>',
                        parse_mode='HTML'
                    )
                else:
                    # если сервер вернул ошибку - генерируем исключение
                    raise Exception(f'❌ Сервер вернул код {response.status_code}')

        # обработка возможных ошибок
        except Exception as e:
            print(f'[Ошибка графика] {e}')
            # сообщаем пользователю об ошибке и переключаемся на текстовую статистику
            await update.message.reply_text(
                '❌ Не удалось загрузить график. Показываю текстовую статистику...'
            )

    # начинаем формировать текстовый отчет со статистикой
    report = ['<b>📊 Статистика</b>']

    # импортируем баланс пользователя
    balance = import_balance(f'{user_id}')
    if balance:
        # добавляем информацию о балансе в отчет
        report.append(f'\n💰 <b>Баланс:</b> {balance:.2f} ₽')

    # импортируем общий лимит пользователя
    general_limit = import_general_limit(f'{user_id}')
    if general_limit[0]:
        # определяем статус лимита (превышен или нет)
        status = '⚠️' if general_limit[1] > general_limit[0] else '✅'
        # конвертируем дату окончания периода в читаемый формат
        period_end = convert_time_format(general_limit[3])

        # добавляем информацию об общем лимите
        report.append(f'\n🧾 <b>Общий лимит:</b> {general_limit[1]:.2f}/{general_limit[0]:.2f} ₽ {status}')
        report.append(f'📅 Дата окончания: {period_end}')

    # если у пользователя есть лимиты по категориям
    if user_data.get('limits'):
        report.append('\n📌 <b>Лимиты по категориям:</b>')

        # перебираем все категории пользователя
        for cat, data in user_data['limits'].items():
            # определяем статус для каждой категории
            status = '⚠️' if data['spent'] > data['limit'] else '✅'
            # получаем дату окончания периода
            period_end = data.get('period_end', 'не установлена')
            # если дата в формате datetime - конвертируем в строку
            if isinstance(period_end, datetime):
                period_end = period_end.strftime('%d.%m.%Y %H:%M')

            # добавляем информацию по категории
            report.append(f'\n• <b>{cat.capitalize()}</b>: {data['spent']:.2f}/{data['limit']:.2f} ₽ {status}')
            report.append(f'  📅 Дата окончания: {period_end}')

    # если кроме заголовка в отчете ничего нет
    if report == ['<b>📊 Статистика</b>']:
        report = ['❌ Нет данных для отображения']

    # отправляем пользователю итоговый отчет
    await update.message.reply_text(
        '\n'.join(report),  # объединяем все строки отчета
        parse_mode='HTML',  # разрешаем HTML-разметку
        reply_markup=markup  # добавляем клавиатуру
    )


async def set_balance(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id

    # Устанавливаем состояние пользователя в режим установки баланса
    USER_STATES[user_id] = UserState.SETTING_BALANCE

    # Отправляем пользователю инструкцию для ввода баланса
    await update.message.reply_text(
        'Напишите ваш текущий баланс (числовое значение). Для отмены введите /cancel.'
    )


async def add_to_balance(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id
    # Устанавливаем состояние пользователя в режим пополнения баланса
    USER_STATES[user_id] = UserState.ADDING_TO_BALANCE
    # Отправляем пользователю инструкцию для ввода суммы пополнения
    await update.message.reply_text(
        'Напишите ваше пополнение баланса (числовое значение). Для отмены введите /cancel.'
    )


async def set_limit(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id
    # Устанавливаем состояние пользователя в режим установки лимита
    USER_STATES[user_id] = UserState.SETTING_LIMIT_AMOUNT
    # Отправляем пользователю инструкцию для ввода категории и суммы лимита
    await update.message.reply_text(
        'Укажите категорию лимита (например, "еда") и сумму лимита (числовое значение), например "еда 100". Для отмены введите /cancel.'
    )


async def set_general_limit(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id
    # Устанавливаем состояние пользователя в режим установки общего лимита
    USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_AMOUNT
    # Отправляем пользователю инструкцию для ввода суммы общего лимита
    await update.message.reply_text(
        'Укажите сумму общего лимита (числовое значение). Для отмены введите /cancel.'
    )


async def remove_general_limit(update: Update, context):
    user_id = update.effective_user.id
    # Удаляем общий лимит из базы данных
    remove_gen_limit(user_id)
    USER_STATES[user_id] = UserState.NONE
    await update.message.reply_text(
        'Общий лимит успешно удалён.', reply_markup=markup
    )


async def remove_limit(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id
    # Устанавливаем состояние пользователя в режим удаления лимитов
    USER_STATES[user_id] = UserState.REMOVING_LIMIT
    await update.message.reply_text(
        'Напишите название лимита, которую вы хотите удалить.', reply_markup=markup
    )


async def cancel(update: Update, context):
    # Получаем ID пользователя, отправившего сообщение
    user_id = update.effective_user.id
    # Сбрасываем состояние пользователя в начальное (NONE)
    USER_STATES[user_id] = UserState.NONE
    # Отправляем сообщение об отмене операции и возвращаем основную клавиатуру
    await update.message.reply_text(
        'Операция отменена.', reply_markup=markup
    )


async def help(update: Update, context):
    help_text = '''
<b>📚 Справка по командам FinanceBot</b>

<b>Основные команды:</b>
• /start - Начало работы с ботом
• /profile - Ваш профиль (баланс и лимиты)
• /stats - Статистика расходов (график + текстовый отчет)

<b>Управление балансом:</b>
• /set_balance - Установить текущий баланс
• /add_to_balance - Пополнить баланс
 *Простой ввод числа* - Записать трату
 *Ввод в виде "категория сумма"* - Записать трату по категории (например: "еда 100")

<b>Управление лимитами:</b>
• /set_limit - Установить лимит с категорией
• /set_general_limit - Установить общий лимит расходов
• /remove_limit - Удалить лимит с категорией
• /remove_general_limit - Удалить общий лимит расходов

<b>Дополнительно:</b>
• /cancel - Отменить текущую операцию

<b>Примеры использования:</b>
• Установить баланс 5000 руб: /set_balance → "5000"
• Добавить 1000 руб к балансу: /add_to_balance → "1000"
• Установить лимит на еду: /set_limit → "еда 3000" → выбрать период (день, неделя, месяц, год)
• Записать трату: "транспорт 100" или просто "100"
    '''
    await update.message.reply_html(help_text, reply_markup=markup)


async def handle_text(update: Update, context):
    # получаем id пользователя из сообщения
    user_id = update.effective_user.id

    # получаем текст сообщения
    text = update.message.text.strip()
    # получаем текущее состояние пользователя или устанавливаем NONE
    state = USER_STATES.get(user_id, UserState.NONE)

    # если команда отмены
    if text == COMMAND_CANCEL:
        # вызываем функцию отмены
        await cancel(update, context)
        return

    # если состояние - установка баланса
    if state == UserState.SETTING_BALANCE:
        try:
            # преобразуем текст в число, заменяя запятую на точку
            new_balance = float(text.replace(',', '.'))
            # сбрасываем состояние пользователя
            USER_STATES[user_id] = UserState.NONE
            # обновляем баланс пользователя
            update_balance(user_id, new_balance)
            # отправляем подтверждение
            await update.message.reply_text(
                f'Текущий баланс успешно обновлён: {new_balance:.2f}.', reply_markup=markup
            )
        except ValueError:
            # если не удалось преобразовать в число
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите число. Для отмены введите /cancel.'
            )
        return

    # если состояние - пополнение баланса
    if state == UserState.ADDING_TO_BALANCE:
        try:
            # преобразуем текст в число
            adding = float(text.replace(',', '.'))
            # сбрасываем состояние
            USER_STATES[user_id] = UserState.NONE
            # добавляем сумму к балансу
            to_balance(user_id, adding)
            # отправляем подтверждение
            await update.message.reply_text(
                f'Текущий баланс успешно пополнен на {adding}.', reply_markup=markup
            )
        except ValueError:
            # если не число
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите число. Для отмены введите /cancel.'
            )
        return

    # если состояние - установка лимита
    if state == UserState.SETTING_LIMIT_AMOUNT:
        try:
            # разделяем текст на категорию и сумму
            category, limit_str = text.split()
            # преобразуем сумму в число
            limit = float(limit_str.replace(',', '.'))
            # получаем или создаем данные пользователя
            data = import_limits(user_id)
            if data:
                data = data.replace("'", '"')
                user_data = json.loads(data)
            else:
                user_data = {}
            # создаем запись лимита для категории
            user_data.setdefault('limits', {})[category] = {'limit': limit, 'spent': 0.0, 'period': '',
                                                            'period_end': ''}

            # обновляем список лимитов
            update_cat_limits(user_id, f'{user_data}')

            # меняем состояние на выбор периода
            USER_STATES[user_id] = UserState.SETTING_LIMIT_PERIOD
            # просим выбрать период
            await update.message.reply_text(
                'Теперь выберите период для этого лимита:', reply_markup=period_markup
            )
        except ValueError:
            # если неверный формат
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите категорию и сумму лимита. Например: "еда 100".'
            )
        return

    # если состояние - выбор периода лимита
    if state == UserState.SETTING_LIMIT_PERIOD:
        # приводим текст к нижнему регистру
        period = text.lower()
        # проверяем, что период допустимый
        if period in LIMIT_PERIODS:
            # получаем или создаем данные пользователя
            data = import_limits(user_id)
            if data:
                data = data.replace("'", '"')
                user_data = json.loads(data)
            else:
                user_data = {}

            # ищем категорию без периода
            for category in user_data.get('limits', {}):
                if user_data['limits'][category]['period'] == '':
                    # устанавливаем период
                    user_data['limits'][category]['period'] = LIMIT_PERIODS[period]
                    # рассчитываем дату окончания
                    user_data['limits'][category]['period_end'] = calculate_period_end(LIMIT_PERIODS[period],
                                                                                       datetime.now())

                # обновляем список лимитов
                update_cat_limits(user_id, f'{user_data}')

            # сбрасываем состояние
            USER_STATES[user_id] = UserState.NONE
            # отправляем подтверждение
            await update.message.reply_text(
                f'Период для лимита установлен: {period}.', reply_markup=markup
            )
        else:
            # если период не распознан
            await update.message.reply_text(
                '❌ Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    # если состояние - установка общего лимита
    if state == UserState.SETTING_GENERAL_LIMIT_AMOUNT:
        try:
            # преобразуем текст в число
            new_general_limit = float(text.replace(',', '.'))
            # меняем состояние на выбор периода
            USER_STATES[user_id] = UserState.SETTING_GENERAL_LIMIT_PERIOD
            # обновляем общий лимит
            update_general_limit(user_id, new_general_limit, -1)
            # просим выбрать период
            await update.message.reply_text(
                'Теперь выберите период для общего лимита:', reply_markup=period_markup
            )
        except ValueError:
            # если не число
            await update.message.reply_text(
                '❌ Неверный формат. Пожалуйста, введите сумму общего лимита. Например: "100".'
            )
        return

    # если состояние - выбор периода общего лимита
    if state == UserState.SETTING_GENERAL_LIMIT_PERIOD:
        # приводим текст к нижнему регистру
        new_period = text.lower()
        # проверяем допустимость периода
        if new_period in LIMIT_PERIODS:
            # сбрасываем состояние
            USER_STATES[user_id] = UserState.NONE
            # обновляем период общего лимита
            update_general_limit_period(user_id, new_period, datetime.now())
            # отправляем подтверждение
            await update.message.reply_text(
                f'Период для общего лимита установлен: {new_period}.', reply_markup=markup
            )
        else:
            # если период не распознан
            await update.message.reply_text(
                '❌ Неверный период. Пожалуйста, выберите день, неделю, месяц или год.'
            )
        return

    # если состояние - выбор категории для удаления
    if state == UserState.REMOVING_LIMIT:
        # приводим текст к нижнему регистру
        category = text.lower()
        # получаем или создаем данные пользователя
        data = import_limits(user_id)
        if data:
            data = data.replace("'", '"')
            user_data = json.loads(data)
        else:
            user_data = {}

        # проверяем, есть ли категория в данных пользователя
        if 'limits' in user_data and category in user_data['limits']:
            # удаляем лимит
            del user_data['limits'][category]
            # обновляем список лимитов
            update_cat_limits(user_id, json.dumps(user_data))
            await update.message.reply_text(
                f'Лимит для категории "{category}" успешно удалён.', reply_markup=markup)
        else:
            await update.message.reply_text(
                f'❌ Категория "{category}" не найдена в ваших лимитах.', reply_markup=markup)
        return

    # обработка обычных трат (не в состоянии настройки)
    try:
        # пытаемся преобразовать текст в число (трата без категории)
        spend_amount = float(text.replace(',', '.'))

        # получаем текущий баланс
        balance = import_balance(user_id)

        # проверяем, установлен ли баланс
        if balance is None:
            await update.message.reply_text(
                '❌ Баланс не задан. Сначала задайте баланс через /set_balance.'
            )
            return

        else:
            # получаем общий лимит
            general_limit = import_general_limit(user_id)
            # рассчитываем новый баланс
            new_balance = balance - spend_amount

        # проверяем, не уйдет ли баланс в минус
        if new_balance - spend_amount < 0:
            await update.message.reply_text(
                f'⚠️ Внимание! Ваш баланс меньше нуля.'
            )
        # обновляем баланс
        update_balance(user_id, balance - spend_amount)

        # если есть общий лимит
        if general_limit[0]:
            # обновляем общий лимит
            update_general_limit(user_id, general_limit[0], spend_amount)
            general_limit[1] += spend_amount

            # проверяем превышение лимита
            if general_limit[1] > general_limit[0]:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit[0]:.2f}.\n'
                    f'Потрачено: {general_limit[1]:.2f}.', reply_markup=markup
                )

        # отправляем отчет о трате
        await update.message.reply_text(
            f'Учтена трата: {spend_amount:.2f}\nНовый баланс: {balance - spend_amount:.2f}', reply_markup=markup
        )
    except ValueError:
        # если не число, пробуем разобрать как "категория сумма"
        try:
            # разделяем на категорию и сумму
            category, spend_str = text.split()
            spend_amount = float(spend_str.replace(',', '.'))

            # получаем список лимитов
            data = import_limits(user_id)
            if data:
                data = data.replace("'", '"')
                user_data = json.loads(data)
            else:
                user_data = {}

            # получаем баланс
            balance = import_balance(user_id)
            general_limit = import_general_limit(user_id)

            # проверяем, установлен ли баланс
            if balance is None:
                await update.message.reply_text(
                    '❌ Баланс не задан. Сначала задайте баланс через /set_balance.'
                )
                return

            # проверяем, есть ли категория у пользователя
            if 'limits' not in user_data or category not in user_data['limits']:
                await update.message.reply_text(
                    f'❌ Категория "{category}" не найдена. Сначала установите лимит для этой категории через /set_limit.',
                    reply_markup=markup
                )
                return

            # получаем данные по категории
            limit_data = user_data['limits'][category]
            # увеличиваем потраченную сумму
            limit_data['spent'] += spend_amount

            # проверяем превышение лимита категории
            if limit_data['spent'] > limit_data['limit']:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный лимит {limit_data['limit']:.2f} для категории "{category}".\n'
                    f'Потрачено: {limit_data['spent']:.2f}.'
                )

            # проверяем, не уйдет ли баланс в минус
            if balance - spend_amount < 0:
                await update.message.reply_text(
                    f'⚠️ Внимание! Ваш баланс меньше нуля.'
                )

            # проверяем превышение лимита
            if general_limit[1] > general_limit[0]:
                await update.message.reply_text(
                    f'⚠️ Внимание! Вы превысили установленный общий лимит {general_limit[0]:.2f}.\n'
                    f'Потрачено: {general_limit[1]:.2f}.', reply_markup=markup
                )

            # отправляем отчет о трате
            await update.message.reply_text(
                f'Учтена трата: {spend_amount:.2f}\n'
                f'Категория: {category}\n'
                f'Новый баланс: {balance - spend_amount:.2f}',
                reply_markup=markup
            )
            # обновляем баланс
            update_balance(user_id, balance - spend_amount),
            # обновляем общий лимит
            update_general_limit(user_id, general_limit[0], spend_amount)
            # обновляем список лимитов
            update_cat_limits(user_id, f'{user_data}')

        except ValueError:
            # если формат не распознан
            await update.message.reply_text(
                '❌ Для ознакомления с функционалам бота используйте команду /help.',
                reply_markup=markup
            )