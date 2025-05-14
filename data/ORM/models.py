from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    balance = Column(Float)
    general_limit = Column(Float)
    spent = Column(Float)
    period = Column(String)
    period_end = Column(String)
    limits = Column(String)

    def __repr__(self):
        return f'<User  (id={self.id}, username={self.username}, balance={self.balance}, general_limit={self.general_limit}, spent={self.spent}, period={self.period}, period_end={self.period_end}, limits={self.limits})>'