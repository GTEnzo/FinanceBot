from data.ORM.database import Session
from data.ORM.models import User


def create_or_import_user(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        return user
    else:
        new_user = User(username=username)
        session.add(new_user)
        session.commit()
        session.close()
        return new_user


def import_balance(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        session.commit()
        return user.balance
    session.close()


def import_general_limit(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        session.commit()
        return [user.general_limit, user.spent, user.period, user.period_end]
    session.close()


def import_limits(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        session.commit()
        return user.limits
    session.close()


def update_balance(username, new_balance):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.balance = new_balance
        session.commit()
    session.close()


def update_general_limit(username, new_general_limit, new_spent):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.general_limit = new_general_limit
        if new_spent == -1:
            user.spent = 0
        else:
            user.spent += new_spent
        session.commit()
    session.close()


def update_general_limit_period(username, new_period, new_period_end):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.period = new_period
        user.period_end = new_period_end
        session.commit()
    session.close()


def update_cat_limits(username, new_limits):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.limits = new_limits
        session.commit()
    session.close()


def to_balance(username, adding):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.balance += adding
        session.commit()
    session.close()


def remove_gen_limit(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if user:
        user.general_limit = None
        user.spent = None
        user.period = None
        user.period_end = None
        session.commit()
    session.close()