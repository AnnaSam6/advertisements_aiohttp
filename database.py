from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from models import Base, User, Advertisement
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: str = "sqlite+aiosqlite:///advertisements.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    async def close(self):
        await self.engine.dispose()

    # ========== USER METHODS ==========
    
    async def create_user(self, username: str, email: str, password_hash: str) -> User:
        """Создание пользователя"""
        async with self.async_session() as session:
            async with session.begin():
                user = User(
                    username=username.strip(),
                    email=email.strip().lower(),
                    password_hash=password_hash
                )
                session.add(user)  # Исправлено: было "user", не "user"
                await session.flush()
                return user

    async def get_user_by_username(self, username: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()

    # ========== ADVERTISEMENT METHODS ==========

    async def create_advertisement(self, title: str, description: str, user_id: int) -> Advertisement:
        """Создание объявления - ИСПРАВЛЕНО: session.add(advertisement)"""
        async with self.async_session() as session:
            async with session.begin():
                advertisement = Advertisement(
                    title=title.strip(),
                    description=description.strip(),
                    user_id=user_id
                )
                session.add(advertisement)  # ✅ ИСПРАВЛЕНО: было "vertisement"
                await session.flush()
                return advertisement

    async def get_advertisement(self, ad_id: int):
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).where(Advertisement.id == ad_id)
            )
            return result.scalar_one_or_none()

    async def get_advertisement_with_user(self, ad_id: int):
        """Получение объявления с подгрузкой пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).where(Advertisement.id == ad_id)
            )
            return result.scalar_one_or_none()

    async def update_advertisement(self, ad_id: int, user_id: int, data: dict):
        """Обновление объявления (только владелец)"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Advertisement).where(Advertisement.id == ad_id)
                )
                advertisement = result.scalar_one_or_none()
                
                if not advertisement:
                    return None, "not_found"
                
                # Проверка прав: только владелец может редактировать
                if advertisement.user_id != user_id:
                    return None, "forbidden"
                
                if 'title' in data and data['title']:
                    advertisement.title = data['title'].strip()
                if 'description' in data and data['description']:
                    advertisement.description = data['description'].strip()
                
                await session.flush()
                return advertisement, "success"

    async def delete_advertisement(self, ad_id: int, user_id: int):
        """Удаление объявления (только владелец)"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Advertisement).where(Advertisement.id == ad_id)
                )
                advertisement = result.scalar_one_or_none()
                
                if not advertisement:
                    return False, "not_found"
                
                if advertisement.user_id != user_id:
                    return False, "forbidden"
                
                await session.delete(advertisement)
                return True, "success"

    async def get_all_advertisements(self):
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).order_by(Advertisement.created_at.desc())
            )
            return result.scalars().all()

    async def get_user_advertisements(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(
                select(Advertisement).where(Advertisement.user_id == user_id)
                .order_by(Advertisement.created_at.desc())
            )
            return result.scalars().all()
