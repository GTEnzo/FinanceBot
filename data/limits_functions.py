from data.constants_and_etc import USER_DATA
from datetime import datetime, timedelta


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


def update_limits():
    for user_id, user_data in USER_DATA.items():
        if 'limits' in user_data:
            for category, limit_data in user_data['limits'].items():
                if limit_data['period_end'] and datetime.now() >= limit_data['period_end']:
                    limit_data['spent'] = 0.0
                    limit_data['period_end'] = calculate_period_end(limit_data['period'], datetime.now())

        if 'general_limit' in user_data:
            general_limit_data = user_data['general_limit']
            if general_limit_data['period_end'] and datetime.now() >= general_limit_data['period_end']:
                general_limit_data['spent'] = 0.0
                general_limit_data['period_end'] = calculate_period_end(general_limit_data['period'], datetime.now())
