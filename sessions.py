from datetime import datetime, timedelta
from sqlalchemy import BINARY, update, delete, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, insert
import config
from crypt import hash_argon2_from_password


class Base(DeclarativeBase):
    pass


class WebSession(Base):
    __tablename__ = 'web_sessions'

    token: Mapped[bytes] = mapped_column(BINARY(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(256), nullable=False)
    org: Mapped[str] = mapped_column(String(256), nullable=False)
    created: Mapped[datetime] = mapped_column(nullable=False)
    last_used: Mapped[datetime] = mapped_column(nullable=False)
    jwt_token: Mapped[str] = mapped_column(String(1024), nullable=False)


class WebSessionsBase:
    def __init__(self):
        self.engine = create_async_engine(
            f'mariadb+asyncmy://{config.db_user}:{config.db_password}@localhost/search_sessions?charset=utf8mb4',
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )

    async def initialize(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def update_last_used(self, token: bytes):
        async with AsyncSession(self.engine) as session:
            query = update(WebSession).where(WebSession.token ==
                                             token).values(last_used=datetime.now())
            await session.execute(query)
            await session.commit()

    async def remove_deprecation(self):
        async with AsyncSession(self.engine) as session:
            query = delete(WebSession).where((WebSession.last_used < datetime.now(
            ) - timedelta(days=3)) | (WebSession.created < datetime.now() - timedelta(days=30)))
            await session.execute(query)
            await session.commit()

    async def get_session(self, token: str) -> dict[str, str] | None:
        token_bytes = hash_argon2_from_password(token)
        await self.remove_deprecation()
        async with AsyncSession(self.engine) as session:
            query = select(WebSession.username, WebSession.org,
                           WebSession.jwt_token).where(WebSession.token == token_bytes)
            result = (await session.execute(query)).first()
            if result is None:
                return None
            result = result.tuple()
            if result is not None:
                await self.update_last_used(token_bytes)
                return {'username': result[0], 'org': result[1], 'jwt_token': result[2]}

    async def get_username_and_org(self, token: str) -> tuple[str, str] | None:
        token_bytes = hash_argon2_from_password(token)
        await self.remove_deprecation()
        async with AsyncSession(self.engine) as session:
            query = select(WebSession.username, WebSession.org).where(
                WebSession.token == token_bytes)
            result = (await session.execute(query)).first()
            if result is None:
                return None
            result = result.tuple()

            if result is not None:
                await self.update_last_used(token_bytes)
                return result[0], result[1]

    async def add_session(self, token: str, jwt_token: str, username: str, org: str):
        token_bytes = hash_argon2_from_password(token)
        async with AsyncSession(self.engine) as session:
            query = insert(WebSession).values(
                token=token_bytes, created=datetime.now(), last_used=datetime.now(), jwt_token=jwt_token, username=username, org=org)
            await session.execute(query)
            await session.commit()

    async def delete_session(self, token: str) -> int | None:
        token_bytes = hash_argon2_from_password(token)
        async with AsyncSession(self.engine) as session:
            query = delete(WebSession).where(WebSession.token == token_bytes)
            await session.execute(query)
            await session.commit()

    async def close(self):
        if self.engine:
            await self.engine.dispose()
