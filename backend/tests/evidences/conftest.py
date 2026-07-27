import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.models import Base, Shop


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    (
        "postgresql+psycopg://xiaodianji:xiaodianji_test"
        "@127.0.0.1:55432/xiaodianji_test"
    ),
)


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.presign_calls: list[tuple[str, int]] = []
        self.deleted: list[str] = []

    async def put(self, object_key: str, data: bytes, mime_type: str) -> None:
        self.objects[object_key] = (data, mime_type)

    async def get_presigned_url(
        self,
        object_key: str,
        expires_seconds: int,
    ) -> str:
        self.presign_calls.append((object_key, expires_seconds))
        return f"https://storage.test/{object_key}?expires={expires_seconds}"

    async def delete(self, object_key: str) -> None:
        self.deleted.append(object_key)
        self.objects.pop(object_key, None)


@pytest.fixture
async def evidence_database():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    other_shop_id = uuid4()
    async with factory.begin() as session:
        session.add_all(
            [
                Shop(id=shop_id, name="凭证测试店"),
                Shop(id=other_shop_id, name="其他门店"),
            ]
        )
    yield factory, shop_id, other_shop_id
    await engine.dispose()


@pytest.fixture
def fake_storage() -> FakeObjectStorage:
    return FakeObjectStorage()

