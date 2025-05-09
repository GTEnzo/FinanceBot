import logging
from telegram import ReplyKeyboardMarkup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

COMMAND_START = '/start'
COMMAND_PROFILE = '/profile'
COMMAND_SET_BALANCE = '/set_balance'
COMMAND_SET_LIMIT = '/set_limit'
COMMAND_SET_GENERAL_LIMIT = '/set_general_limit'
COMMAND_STATS = '/stats'
COMMAND_CANCEL = '/cancel'

PERIOD_DAY = 'день'
PERIOD_WEEK = 'неделя'
PERIOD_MONTH = 'месяц'
PERIOD_YEAR = 'год'


class UserState:
    NONE = 'none'
    SETTING_BALANCE = 'setting_balance'
    SETTING_LIMIT_AMOUNT = 'setting_limit_amount'
    SETTING_LIMIT_PERIOD = 'setting_limit_period'
    SETTING_GENERAL_LIMIT_AMOUNT = 'setting_general_limit_amount'
    SETTING_GENERAL_LIMIT_PERIOD = 'setting_general_limit_period'


LIMIT_PERIODS = {
    "день": "день",
    "неделя": "неделя",
    "месяц": "месяц",
    "год": "год"
}

USER_STATES = {}
USER_DATA = {}

reply_keyboard = [
    [COMMAND_START],
    [COMMAND_PROFILE, COMMAND_STATS],
    [COMMAND_SET_BALANCE],
    [COMMAND_SET_LIMIT, COMMAND_SET_GENERAL_LIMIT],
    [COMMAND_CANCEL]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)

period_keyboard = [
    [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH, PERIOD_YEAR],
    [COMMAND_CANCEL]
]
period_markup = ReplyKeyboardMarkup(period_keyboard, one_time_keyboard=False, resize_keyboard=True)
