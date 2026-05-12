from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from rent_pulse.config import DatasetSource, RentPulseConfig


@dataclass(frozen=True)
class DownloadedDataset:
    source: DatasetSource
    url: str
    content: bytes
    content_type: str


def _resolve_file_url(url: str, config: RentPulseConfig) -> Path:
    parsed = urlparse(url)
    raw_path = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return config.project_root / path


def fetch_source(source: DatasetSource, config: RentPulseConfig, timeout_seconds: int = 120) -> DownloadedDataset:
    url = source.resolved_url()
    if url.startswith("file://"):
        path = _resolve_file_url(url, config)
        return DownloadedDataset(
            source=source,
            url=url,
            content=path.read_bytes(),
            content_type=f"text/{source.file_format}",
        )

    import requests

    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return DownloadedDataset(
        source=source,
        url=url,
        content=response.content,
        content_type=response.headers.get("content-type", ""),
    )
