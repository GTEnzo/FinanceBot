import json
from datetime import datetime, timedelta

from data.ORM.services import *


# ф-ия для читаемости даты окончания лимита
def convert_time_format(period_end):
    dt = datetime.strptime(period_end, '%Y-%m-%d %H:%M:%S.%f')
    return dt.strftime('%d.%m.%Y %H:%M')


# ф-ия для даты окончания лимита
def calculate_period_end(period_key, from_date):
    if period_key == 'день':
        return convert_time_format(f'{from_date + timedelta(days=1)}')
    elif period_key == 'неделя':
        return convert_time_format(f'{from_date + timedelta(days=7)}')
    elif period_key == 'месяц':
        return convert_time_format(f'{from_date + timedelta(days=30)}')
    elif period_key == 'год':
        return convert_time_format(f'{from_date + timedelta(days=365)}')
    else:
        return from_date


# автоматическое обновление лимитов
def update_limits(username):
    data = import_limits(username)
    if data:
        data = data.replace("'", '"')
        user_data = json.loads(data)

        for category, limits in user_data['limits'].items():
            datetime1 = datetime.strptime(f'{datetime.now()}', "%Y-%m-%d %H:%M:%S.%f")
            datetime2 = datetime.strptime(f'{limits["period_end"]}', "%d.%m.%Y %H:%M")
            if datetime1 >= datetime2:
                limits['spent'] = 0.0
                limits['period_end'] = calculate_period_end(limits['period'], datetime.now())
    else:
        pass

    general_limit = import_general_limit(username)
    if general_limit[3] is not None:
        datetime1 = datetime.strptime(f'{datetime.now()}', "%Y-%m-%d %H:%M:%S.%f")
        datetime2 = datetime.strptime(f'{general_limit[3]}', "%Y-%m-%d %H:%M:%S.%f")
        if datetime1 >= datetime2:
            general_limit[1] = 0.0
            general_limit[3] = calculate_period_end(general_limit[2], datetime.now())