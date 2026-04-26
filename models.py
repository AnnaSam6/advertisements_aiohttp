from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Advertisement(Base):
    """Модель объявления"""
    __tablename__ = 'advertisements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = Column(String(100), nullable=False)

    def to_dict(self):
        """Преобразование в словарь для JSON ответа"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'owner': self.owner
        }
