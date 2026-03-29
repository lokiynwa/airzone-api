from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class LocationSearchCache(TimestampMixin, Base):
    __tablename__ = "location_search_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    results_json: Mapped[str] = mapped_column(Text)

