from typing import Annotated, Protocol
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from xiaodianji.evidences.service import (
    EvidenceNotFound,
    EvidenceRecord,
    EvidenceTooLarge,
    EvidenceTypeUnsupported,
)
from xiaodianji.schemas.evidence import EvidenceRead


DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


class EvidenceActions(Protocol):
    max_size_bytes: int

    def validate_mime_type(self, mime_type: str) -> str: ...

    async def create_upload(
        self,
        *,
        shop_id: UUID,
        original_filename: str | None,
        mime_type: str,
        data: bytes,
    ) -> EvidenceRecord: ...

    async def get_access(
        self,
        shop_id: UUID,
        evidence_id: UUID,
    ) -> EvidenceRecord: ...


router = APIRouter(prefix="/api/v1/evidences", tags=["evidences"])


def get_evidence_service(request: Request) -> EvidenceActions:
    service = request.app.state.evidence_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="evidence service is not configured",
        )
    return service


async def read_upload_bounded(
    upload,
    *,
    max_size_bytes: int,
    chunk_size: int = UPLOAD_CHUNK_BYTES,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining_probe = max_size_bytes - total + 1
        if remaining_probe <= 0:
            raise EvidenceTooLarge(
                f"evidence exceeds {max_size_bytes} byte limit"
            )
        chunk = await upload.read(min(chunk_size, remaining_probe))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > max_size_bytes:
            raise EvidenceTooLarge(
                f"evidence exceeds {max_size_bytes} byte limit"
            )
        chunks.append(chunk)


def map_evidence_error(error: Exception) -> HTTPException:
    if isinstance(error, EvidenceTypeUnsupported):
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported or mismatched evidence media type",
        )
    if isinstance(error, EvidenceTooLarge):
        return HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        )
    if isinstance(error, EvidenceNotFound):
        return HTTPException(status_code=404, detail="evidence not found")
    raise error


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    file: Annotated[UploadFile, File()],
    x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")],
) -> EvidenceRead:
    service = get_evidence_service(request)
    try:
        mime_type = service.validate_mime_type(file.content_type or "")
        data = await read_upload_bounded(
            file,
            max_size_bytes=getattr(
                service,
                "max_size_bytes",
                DEFAULT_MAX_UPLOAD_BYTES,
            ),
        )
        record = await service.create_upload(
            shop_id=x_shop_id,
            original_filename=file.filename,
            mime_type=mime_type,
            data=data,
        )
    except (
        EvidenceTypeUnsupported,
        EvidenceTooLarge,
        EvidenceNotFound,
    ) as error:
        raise map_evidence_error(error) from error
    finally:
        await file.close()
    return EvidenceRead.from_record(record)


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(
    request: Request,
    evidence_id: UUID,
    x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")],
) -> EvidenceRead:
    try:
        record = await get_evidence_service(request).get_access(
            x_shop_id,
            evidence_id,
        )
    except EvidenceNotFound as error:
        raise map_evidence_error(error) from error
    return EvidenceRead.from_record(record)

