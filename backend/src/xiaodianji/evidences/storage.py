import asyncio
from typing import Protocol

import boto3


class ObjectStorage(Protocol):
    async def put(
        self,
        object_key: str,
        data: bytes,
        mime_type: str,
    ) -> None: ...

    async def get_presigned_url(
        self,
        object_key: str,
        expires_seconds: int,
    ) -> str: ...

    async def delete(self, object_key: str) -> None: ...


class Boto3ObjectStorage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    async def put(
        self,
        object_key: str,
        data: bytes,
        mime_type: str,
    ) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=object_key,
            Body=data,
            ContentType=mime_type,
        )

    async def get_presigned_url(
        self,
        object_key: str,
        expires_seconds: int,
    ) -> str:
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires_seconds,
        )

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=object_key,
        )

