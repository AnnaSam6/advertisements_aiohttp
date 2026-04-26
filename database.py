from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from models import Base, Advertisement
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Асинхронный класс для работы с БД"""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///advertisements.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Инициализация БД - создание таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    async def close(self):
        """Закрытие соединения"""
        await self.engine.dispose()

    async def create_advertisement(self, title: str, description: str, owner: str) -> Advertisement:
        """Создание объявления"""
        async with self.async_session() as session:
            async with session.begin():
                advertisement = Advertisement(
                    title=title.strip(),
                    description=description.strip(),
                    owner=owner.strip()
                )
                session.add(vertisement)
                await session.flush()
                # Возвращаем копию данных (сессия закроется)
                return advertisement

    async def get_advertisement(self, ad_id: int):
        """Получение объявления по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).where(Advertisement.id == ad_id)
            )
            return result.scalar_one_or_none()

    async def update_advertisement(self, ad_id: int, data: dict):
        """Обновление объявления"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Advertisement).where(Advertisement.id == ad_id)
                )
                advertisement = result.scalar_one_or_none()
                
                if not advertisement:
                    return None
                
                if 'title' in data and data['title']:
                    advertisement.title = data['title'].strip()
                if 'description' in data and data['description']:
                    advertisement.description = data['description'].strip()
                if 'owner' in data and data['owner']:
                    advertisement.owner = data['owner'].strip()
                
                await session.flush()
                return advertisement

    async def delete_advertisement(self, ad_id: int) -> bool:
        """Удаление объявления"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Advertisement).where(Advertisement.id == ad_id)
                )
                advertisement = result.scalar_one_or_none()
                
                if not advertisement:
                    return False
                
                await session.delete(advertisement)
                return True

    async def get_all_advertisements(self):
        """Получение всех объявлений"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).order_by(Advertisement.created_at.desc())
            )
            return result.scalars().all()
