import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.evidences.storage import ObjectStorage
from xiaodianji.models import Evidence, EvidenceStatus, EvidenceType


logger = logging.getLogger(__name__)


class EvidenceTypeUnsupported(ValueError):
    pass


class EvidenceTooLarge(ValueError):
    pass


class EvidenceNotFound(LookupError):
    pass


class TranscriptInvalid(ValueError):
    pass


MIME_TYPES: dict[str, tuple[EvidenceType, str]] = {
    "audio/mpeg": (EvidenceType.AUDIO, ".mp3"),
    "audio/mp4": (EvidenceType.AUDIO, ".m4a"),
    "audio/ogg": (EvidenceType.AUDIO, ".ogg"),
    "audio/wav": (EvidenceType.AUDIO, ".wav"),
    "audio/webm": (EvidenceType.AUDIO, ".webm"),
    "audio/x-m4a": (EvidenceType.AUDIO, ".m4a"),
    "image/jpeg": (EvidenceType.IMAGE, ".jpg"),
    "image/png": (EvidenceType.IMAGE, ".png"),
}


def normalize_mime_type(mime_type: str) -> str:
    return mime_type.split(";", 1)[0].strip().lower()


def has_valid_signature(mime_type: str, data: bytes) -> bool:
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "audio/wav":
        return (
            len(data) >= 12
            and data.startswith(b"RIFF")
            and data[8:12] == b"WAVE"
        )
    if mime_type == "audio/ogg":
        return data.startswith(b"OggS")
    if mime_type == "audio/webm":
        return data.startswith(b"\x1a\x45\xdf\xa3")
    if mime_type in {"audio/mp4", "audio/x-m4a"}:
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if mime_type == "audio/mpeg":
        return data.startswith(b"ID3") or (
            len(data) >= 2
            and data[0] == 0xFF
            and data[1] & 0xE0 == 0xE0
        )
    return False


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: UUID
    shop_id: UUID
    type: EvidenceType
    status: EvidenceStatus
    object_key: str
    original_filename: str | None
    mime_type: str
    size_bytes: int
    asr_text: str | None
    access_url: str | None = None


class EvidenceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: ObjectStorage,
        *,
        max_size_bytes: int = 20 * 1024 * 1024,
        access_url_ttl_seconds: int = 300,
        max_transcript_characters: int = 50_000,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.max_size_bytes = max_size_bytes
        self.access_url_ttl_seconds = access_url_ttl_seconds
        self.max_transcript_characters = max_transcript_characters

    def validate_mime_type(self, mime_type: str) -> str:
        normalized = normalize_mime_type(mime_type)
        if normalized not in MIME_TYPES:
            raise EvidenceTypeUnsupported(mime_type)
        return normalized

    async def create_upload(
        self,
        *,
        shop_id: UUID,
        original_filename: str | None,
        mime_type: str,
        data: bytes,
    ) -> EvidenceRecord:
        normalized_mime = self.validate_mime_type(mime_type)
        evidence_type, extension = MIME_TYPES[normalized_mime]
        if len(data) > self.max_size_bytes:
            raise EvidenceTooLarge(
                f"evidence exceeds {self.max_size_bytes} byte limit"
            )
        if not has_valid_signature(normalized_mime, data):
            raise EvidenceTypeUnsupported(
                f"content does not match {normalized_mime}"
            )

        now = datetime.now(timezone.utc)
        object_key = f"{shop_id}/{now:%Y/%m}/{uuid4().hex}{extension}"
        safe_filename = self._safe_filename(original_filename)
        await self.storage.put(object_key, data, normalized_mime)
        try:
            async with self.session_factory.begin() as session:
                evidence = Evidence(
                    shop_id=shop_id,
                    type=evidence_type,
                    status=EvidenceStatus.READY,
                    object_key=object_key,
                    original_filename=safe_filename,
                    mime_type=normalized_mime,
                    size_bytes=len(data),
                )
                session.add(evidence)
                await session.flush()
                result = self._to_record(evidence)
        except Exception:
            try:
                await self.storage.delete(object_key)
            except Exception:
                logger.exception(
                    "failed to delete orphaned evidence object %s",
                    object_key,
                )
            raise
        return result

    async def get_access(
        self,
        shop_id: UUID,
        evidence_id: UUID,
    ) -> EvidenceRecord:
        async with self.session_factory() as session:
            evidence = await session.scalar(
                select(Evidence).where(
                    Evidence.id == evidence_id,
                    Evidence.shop_id == shop_id,
                )
            )
        if evidence is None:
            raise EvidenceNotFound(str(evidence_id))
        access_url = await self.storage.get_presigned_url(
            evidence.object_key,
            self.access_url_ttl_seconds,
        )
        return self._to_record(evidence, access_url=access_url)

    async def attach_transcript(
        self,
        shop_id: UUID,
        evidence_id: UUID,
        transcript: str,
    ) -> EvidenceRecord:
        normalized_transcript = transcript.strip()
        if (
            not normalized_transcript
            or len(normalized_transcript) > self.max_transcript_characters
        ):
            raise TranscriptInvalid("transcript is blank or too long")
        async with self.session_factory.begin() as session:
            evidence = await session.scalar(
                select(Evidence)
                .where(
                    Evidence.id == evidence_id,
                    Evidence.shop_id == shop_id,
                )
                .with_for_update()
            )
            if evidence is None:
                raise EvidenceNotFound(str(evidence_id))
            if evidence.type is not EvidenceType.AUDIO:
                raise TranscriptInvalid(
                    "transcripts can only be attached to audio evidence"
                )
            evidence.asr_text = normalized_transcript
            await session.flush()
            result = self._to_record(evidence)
        return result

    @staticmethod
    def _safe_filename(filename: str | None) -> str | None:
        if not filename:
            return None
        normalized = filename.replace("\\", "/")
        return PurePosixPath(normalized).name[:255] or None

    @staticmethod
    def _to_record(
        evidence: Evidence,
        *,
        access_url: str | None = None,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            id=evidence.id,
            shop_id=evidence.shop_id,
            type=evidence.type,
            status=evidence.status,
            object_key=evidence.object_key,
            original_filename=evidence.original_filename,
            mime_type=evidence.mime_type,
            size_bytes=evidence.size_bytes,
            asr_text=evidence.asr_text,
            access_url=access_url,
        )

