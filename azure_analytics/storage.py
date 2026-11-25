"""Storage layer.

Two interchangeable back ends with the same three methods:
    list_blobs(container, prefix) -> list of blob names
    download(container, name)     -> bytes
    upload(container, name, data) -> None

* AzureStore - real Azure Blob Storage (needs `azure-storage-blob`)
* LocalStore - a plain folder: <root>/<container>/<blob>, for testing offline
"""

import logging
from pathlib import Path

from config import Settings

log = logging.getLogger(__name__)


class LocalStore:
    """Folder-based stand-in for Azure Blob Storage."""

    def __init__(self, root: Path):
        self.root = root

    def list_blobs(self, container: str, prefix: str = "") -> list[str]:
        base = self.root / container
        if not base.exists():
            return []
        names = (p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())
        return sorted(n for n in names if n.startswith(prefix))

    def download(self, container: str, name: str) -> bytes:
        return (self.root / container / name).read_bytes()

    def upload(self, container: str, name: str, data: bytes) -> None:
        path = self.root / container / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class AzureStore:
    """Azure Blob Storage back end."""

    def __init__(self, connection_string: str):
        from azure.storage.blob import BlobServiceClient  # imported lazily

        self.client = BlobServiceClient.from_connection_string(connection_string)

    def _container(self, name: str):
        container = self.client.get_container_client(name)
        if not container.exists():
            container.create_container()
        return container

    def list_blobs(self, container: str, prefix: str = "") -> list[str]:
        blobs = self._container(container).list_blobs(name_starts_with=prefix)
        return sorted(b.name for b in blobs)

    def download(self, container: str, name: str) -> bytes:
        return self._container(container).download_blob(name).readall()

    def upload(self, container: str, name: str, data: bytes) -> None:
        self._container(container).upload_blob(name, data, overwrite=True)


def get_store(settings: Settings):
    """Pick Azure if a connection string is configured, otherwise local folder."""
    if settings.connection_string:
        log.info("Storage mode: Azure Blob Storage")
        return AzureStore(settings.connection_string)
    log.info("Storage mode: LOCAL folder (%s)", settings.local_root)
    return LocalStore(settings.local_root)
