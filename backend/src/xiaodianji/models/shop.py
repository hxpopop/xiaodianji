from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Shop(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="Asia/Shanghai",
        nullable=False,
    )

