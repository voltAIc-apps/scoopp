# S3/MinIO async storage service
# Stores and retrieves crawled markdown content

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import aioboto3

logger = logging.getLogger(__name__)

# module-level session (reusable, thread-safe)
_session: Optional[aioboto3.Session] = None


def _get_session() -> aioboto3.Session:
    """Lazy-init a single aioboto3 session."""
    global _session
    if _session is None:
        _session = aioboto3.Session()
    return _session


def _resolve_s3_config(config: dict) -> dict:
    """Read S3 connection params from env via config.yml indirection."""
    s3_cfg = config.get("s3", {})
    return {
        "endpoint_url": os.environ.get(s3_cfg.get("endpoint_env", ""), ""),
        "bucket": os.environ.get(s3_cfg.get("bucket_env", ""), ""),
        "aws_access_key_id": os.environ.get(s3_cfg.get("access_key_env", ""), ""),
        "aws_secret_access_key": os.environ.get(s3_cfg.get("secret_key_env", ""), ""),
        "prefix": s3_cfg.get("prefix", "md"),
        "enabled": s3_cfg.get("enabled", False),
    }


def build_s3_key(crawl_id: str, url: str, prefix: str = "md") -> str:
    """Deterministic S3 key: {prefix}/{crawl_id}/{domain}/{timestamp}.md"""
    domain = urlparse(url).netloc or "unknown"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}/{crawl_id}/{domain}/{ts}.md"


async def upload_markdown(
    crawl_id: str,
    url: str,
    markdown: str,
    config: dict,
) -> Optional[str]:
    """Upload markdown to S3. Returns the S3 key on success, None on failure.
    Never raises -- failures are logged and swallowed."""
    s3 = _resolve_s3_config(config)
    if not s3["enabled"]:
        return None

    key = build_s3_key(crawl_id, url, s3["prefix"])

    try:
        session = _get_session()
        async with session.client(
            "s3",
            endpoint_url=s3["endpoint_url"],
            aws_access_key_id=s3["aws_access_key_id"],
            aws_secret_access_key=s3["aws_secret_access_key"],
        ) as client:
            await client.put_object(
                Bucket=s3["bucket"],
                Key=key,
                Body=markdown.encode("utf-8"),
                ContentType="text/markdown; charset=utf-8",
            )
        logger.info("S3 upload OK: %s (%d bytes)", key, len(markdown))
        return key
    except Exception as exc:
        logger.error("S3 upload failed for crawl %s: %s", crawl_id, exc)
        return None


async def download_markdown(
    s3_key: str,
    config: dict,
) -> Optional[str]:
    """Download markdown from S3 by key. Returns content or None."""
    s3 = _resolve_s3_config(config)
    if not s3["enabled"]:
        return None

    try:
        session = _get_session()
        async with session.client(
            "s3",
            endpoint_url=s3["endpoint_url"],
            aws_access_key_id=s3["aws_access_key_id"],
            aws_secret_access_key=s3["aws_secret_access_key"],
        ) as client:
            resp = await client.get_object(Bucket=s3["bucket"], Key=s3_key)
            body = await resp["Body"].read()
            return body.decode("utf-8")
    except Exception as exc:
        logger.error("S3 download failed for key %s: %s", s3_key, exc)
        return None
