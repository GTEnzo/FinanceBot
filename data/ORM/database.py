from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.ORM.models import Base

engine = create_engine('sqlite:///database/database.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
