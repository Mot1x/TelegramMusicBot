from sqlalchemy import Table, MetaData, Column, Integer, BigInteger, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from settings import Settings

engine = create_async_engine(url=Settings().database_url_asyncpg, echo=True)
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


async def add_row(track_id: int, chat_id: int, message_id: int) -> None:
    async with async_session() as session:
        new_row = IDs(track_id=track_id, chat_id=chat_id, message_id=message_id)
        session.add(new_row)
        await session.commit()


async def create_table() -> None:
    async with engine.connect() as conn:
        await conn.run_sync(metadata.create_all)
        await conn.commit()


async def get_ids_by_track_id(track_id: int) -> IDs | None:
    async with async_session() as session:
        async with session.begin():
            stmt = select(IDs).where(IDs.track_id == track_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

