import logging
from telegram import ReplyKeyboardMarkup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# команды
COMMAND_START = '/start'
COMMAND_PROFILE = '/profile'
COMMAND_STATS = '/stats'
COMMAND_SET_BALANCE = '/set_balance'
COMMAND_ADD_TO_BALANCE = '/add_to_balance'
COMMAND_SET_LIMIT = '/set_limit'
COMMAND_SET_GENERAL_LIMIT = '/set_general_limit'
COMMAND_REMOVE_LIMIT = '/remove_limit'
COMMAND_REMOVE_GENERAL_LIMIT = '/remove_general_limit'
COMMAND_CANCEL = '/cancel'
COMMAND_HELP = '/help'

# периоды
PERIOD_DAY = 'день'
PERIOD_WEEK = 'неделя'
PERIOD_MONTH = 'месяц'
PERIOD_YEAR = 'год'


# состояние программы
class UserState:
    NONE = 'none'
    SETTING_BALANCE = 'setting_balance'
    ADDING_TO_BALANCE = 'adding_to_balance'
    SETTING_LIMIT_AMOUNT = 'setting_limit_amount'
    SETTING_LIMIT_PERIOD = 'setting_limit_period'
    SETTING_GENERAL_LIMIT_AMOUNT = 'setting_general_limit_amount'
    SETTING_GENERAL_LIMIT_PERIOD = 'setting_general_limit_period'
    REMOVING_LIMIT = 'removing_limit'


LIMIT_PERIODS = {
    'день': 'день',
    'неделя': 'неделя',
    'месяц': 'месяц',
    'год': 'год'
}

USER_STATES = {}

reply_keyboard = [
    [COMMAND_START],
    [COMMAND_PROFILE, COMMAND_STATS],
    [COMMAND_SET_BALANCE, COMMAND_ADD_TO_BALANCE],
    [COMMAND_SET_LIMIT, COMMAND_SET_GENERAL_LIMIT],
    [COMMAND_REMOVE_LIMIT, COMMAND_REMOVE_GENERAL_LIMIT],
    [COMMAND_CANCEL, COMMAND_HELP]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)

period_keyboard = [
    [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH, PERIOD_YEAR],
    [COMMAND_CANCEL]
]
period_markup = ReplyKeyboardMarkup(period_keyboard, one_time_keyboard=False, resize_keyboard=True)