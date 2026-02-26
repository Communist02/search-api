from datetime import datetime
from sqlalchemy import DATETIME, VARCHAR, Column, BINARY, INT, ForeignKey, TEXT, Index, delete, desc, event, update, func
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy import create_engine, select, insert
from config import config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(INT, primary_key=True, autoincrement=True)
    login = Column(VARCHAR(25), nullable=False)
    encrypted_private_key = Column(BINARY(48), nullable=False)
    public_key = Column(BINARY(32), nullable=False)


class Service(Base):
    __tablename__ = 'services'

    # id = Column(INT, primary_key=True, autoincrement=True)
    id = Column(VARCHAR(25), primary_key=True, nullable=False)


class BucketItem(Base):
    __tablename__ = 'bucket_items'

    id = Column(INT, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey(User.id), nullable=False)
    document_id = Column(TEXT, nullable=False)
    service_id = Column(ForeignKey(Service.id), nullable=False)


# class Log(Base):
#     __tablename__ = 'logs'

#     id = Column(INT, primary_key=True, autoincrement=True)
#     date_time = Column(DATETIME, nullable=False)
#     action = Column(VARCHAR(255), nullable=False)
#     message = Column(TEXT, nullable=True)
#     result = Column(INT, nullable=False)
#     user_id = Column(ForeignKey(User.id), nullable=True)
#     group_id = Column(ForeignKey(Group.id), nullable=True)
#     collection_id = Column(ForeignKey(Collection.id), nullable=True)


@event.listens_for(Service.__table__, 'after_create')
def insert_initial_user_roles(target, connection, **kw):
    connection.execute(target.insert(), [
        {'id': 'storage-api'}
    ])


class MainDatabase:
    def __init__(self):
        self.engine = create_engine(
            f'mariadb+pymysql://{config.db_user}:{config.db_password}@localhost/main?charset=utf8mb4',
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        self.connection = self.engine.connect()
        Base.metadata.create_all(self.engine)

    def get_user_id(self, login: str) -> int | None:
        with Session(self.engine) as session:
            query = select(User.id).where(User.login == login)
            user_id = session.execute(query).scalar()
            return user_id

    def get_username(self, user_id: int) -> str | None:
        with Session(self.engine) as session:
            query = select(User.login).where(User.id == user_id)
            username = session.execute(query).scalar()
            return username

    def add_to_bucket(self, user_id: int, document_id: str, service_id: str) -> int:
        with Session(self.engine) as session:
            query = insert(BucketItem).values(
                user_id=user_id, document_id=document_id, service_id=service_id).returning(BucketItem.id)
            item_id = session.execute(query).scalar_one()
            session.commit()
            return item_id

    def get_bucket(self, user_id: int) -> list:
        with Session(self.engine) as session:
            query = select(BucketItem.id, BucketItem.document_id,
                           BucketItem.service_id).where(BucketItem.user_id == user_id)
            bucket_items = session.execute(query).all()

            result = []
            for item in bucket_items:
                result.append(
                    {'id': item[0], 'document_id': item[1], 'service_id': item[2]})
            return result

    def delete_from_bucket(self, user_id: int, item_id: int):
        with Session(self.engine) as session:
            query = delete(BucketItem).where((BucketItem.user_id == user_id) & (BucketItem.id == item_id))
            session.execute(query)
            session.commit()

    def clear_bucket(self, user_id: int):
        with Session(self.engine) as session:
            query = delete(BucketItem).where(BucketItem.user_id == user_id)
            session.execute(query)
            session.commit()
