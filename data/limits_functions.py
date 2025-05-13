from data.ORM.services import *
from data.constants_and_etc import USER_DATA
from datetime import datetime, timedelta


# ф-ия для читаемости даты окончания лимита
def convert_time_format(period_end):
    dt = datetime.strptime(period_end, '%Y-%m-%d %H:%M:%S.%f')
    return dt.strftime('%d.%m.%Y %H:%M')


# ф-ия для даты окончания лимита
def calculate_period_end(period_key, from_date):
    if period_key == 'день':
        return from_date + timedelta(days=1)
    elif period_key == 'неделя':
        return from_date + timedelta(days=7)
    elif period_key == 'месяц':
        return from_date + timedelta(days=30)
    elif period_key == 'год':
        return from_date + timedelta(days=365)
    else:
        return from_date


# автоматическое обновление лимитов
def update_limits():
    for user_id, user_data in USER_DATA.items():
        if 'limits' in user_data:
            for category, limit_data in user_data['limits'].items():
                if limit_data['period_end'] and datetime.now() >= limit_data['period_end']:
                    limit_data['spent'] = 0.0
                    limit_data['period_end'] = calculate_period_end(limit_data['period'], datetime.now())

        general_limit = import_general_limit(user_id)
        if general_limit[3] and datetime.now() >= general_limit[3]:
            general_limit[1] = 0.0
            general_limit[3] = calculate_period_end(general_limit[2], datetime.now())