"""Raw artifact storage: S3 when ``CARETHREAD_S3_BUCKET`` is set, local disk otherwise."""
import logging
from functools import lru_cache
from pathlib import Path

from app.config import settings, aws_credential_kwargs

log = logging.getLogger("carethread.storage")


@lru_cache(maxsize=1)
def _s3():
    import boto3
    return boto3.client("s3", region_name=settings.aws_region, **aws_credential_kwargs())


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def store_raw_local(patient_id: str, artifact_type: str, title: str, text: str) -> str:
    subdir = Path(settings.storage_dir) / patient_id / artifact_type.lower()
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / f"{_safe(title)}.txt"
    path.write_text(text, encoding="utf-8")
    return f"local://{path.relative_to(Path(settings.storage_dir).parent)}"


def store_raw_s3(patient_id: str, artifact_type: str, title: str, text: str) -> str:
    key = f"{settings.s3_prefix}/{patient_id}/{artifact_type.lower()}/{_safe(title)}.txt"
    _s3().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=text.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
        ServerSideEncryption="AES256",
    )
    return f"s3://{settings.s3_bucket}/{key}"


def store_raw(patient_id: str, artifact_type: str, title: str, text: str) -> str:
    if settings.s3_bucket:
        try:
            return store_raw_s3(patient_id, artifact_type, title, text)
        except Exception as e:  # noqa: BLE001 — never lose an ingest over storage
            log.warning("S3 upload failed (%s); storing locally instead", e)
    return store_raw_local(patient_id, artifact_type, title, text)
