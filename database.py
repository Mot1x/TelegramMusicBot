import asyncio

from sqlalchemy import URL, text, create_engine, Table, MetaData, Column, Integer, String, BigInteger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from config import settings

engine = create_async_engine(url=settings.DATABASE_URL_asyncpg, echo=True)
metadata = MetaData()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


ids = Table(
    'ids', metadata,
    Column('id', Integer, primary_key=True),
    Column('track_id', BigInteger),
    Column('chat_id', BigInteger),
    Column('message_id', BigInteger)
)

Base = declarative_base()


class IDs(Base):
    __tablename__ = 'ids'

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(BigInteger, index=True)
    chat_id = Column(BigInteger, index=True)
    message_id = Column(BigInteger, index=True)


async def add_row(track_id, chat_id, message_id):
    async with async_session() as session:
        new_row = IDs(track_id=track_id, chat_id=chat_id, message_id=message_id)
        session.add(new_row)
        await session.commit()


async def create_table():
    async with engine.connect() as conn:
        await conn.run_sync(metadata.create_all)
        await conn.commit()


