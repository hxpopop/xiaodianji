from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from xiaodianji.api.evidences import read_upload_bounded
from xiaodianji.evidences.service import (
    EvidenceService,
    EvidenceTooLarge,
    EvidenceTypeUnsupported,
)
from xiaodianji.models import Evidence


class GuardedUpload:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        assert size > 0, "upload must never be read without a bound"
        self.read_sizes.append(size)
        chunk = self.data[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


async def test_upload_reader_never_reads_unbounded() -> None:
    upload = GuardedUpload(b"123456789")

    with pytest.raises(EvidenceTooLarge):
        await read_upload_bounded(upload, max_size_bytes=8, chunk_size=3)

    assert upload.read_sizes
    assert max(upload.read_sizes) <= 3


async def test_rejects_bytes_that_do_not_match_declared_media_type(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, _ = evidence_database
    service = EvidenceService(factory, fake_storage)

    with pytest.raises(EvidenceTypeUnsupported):
        await service.create_upload(
            shop_id=shop_id,
            original_filename="fake.jpg",
            mime_type="image/jpeg",
            data=b"this is not a jpeg",
        )

    assert fake_storage.objects == {}


async def test_database_failure_deletes_uploaded_object(
    evidence_database,
    fake_storage,
) -> None:
    factory, _, _ = evidence_database
    service = EvidenceService(factory, fake_storage)

    with pytest.raises(IntegrityError):
        await service.create_upload(
            shop_id=uuid4(),
            original_filename="trade.wav",
            mime_type="audio/wav",
            data=b"RIFF\x04\x00\x00\x00WAVEdata",
        )

    async with factory() as session:
        evidence_count = await session.scalar(
            select(func.count()).select_from(Evidence)
        )
    assert evidence_count == 0
    assert fake_storage.objects == {}
    assert len(fake_storage.deleted) == 1

