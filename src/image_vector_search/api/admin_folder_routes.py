from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse

from image_vector_search.scanning.files import is_supported_image, scan_disk_folders, to_container_path
from image_vector_search.scanning.files import iter_image_files
from image_vector_search.scanning.image_metadata import read_image_metadata


def create_admin_folder_router(
    *,
    repository,
    status_service,
    images_root: str,
    auth_enabled: bool = False,
) -> APIRouter:
    router = APIRouter()
    root_path = Path(images_root).resolve()

    def _require_authentication(request: Request) -> None:
        if auth_enabled and not request.session.get("authenticated", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

    def _known_folders() -> list[str]:
        return scan_disk_folders(root_path)

    def _normalize_path(raw_path: str, known_folders: list[str]) -> str:
        if "\x00" in raw_path or "\\" in raw_path:
            raise HTTPException(status_code=400, detail="invalid path")
        normalized = raw_path.strip("/")
        if any(segment == ".." for segment in normalized.split("/") if segment):
            raise HTTPException(status_code=400, detail="invalid path")
        if raw_path.startswith("/") and raw_path != "/" and normalized not in known_folders:
            raise HTTPException(status_code=400, detail="invalid path")
        return normalized

    def _resolve_directory(normalized_path: str) -> Path | None:
        target = (root_path / normalized_path).resolve()
        try:
            target.relative_to(root_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid path") from exc
        if not target.exists():
            return None
        if not target.is_dir():
            return None
        return target

    def _resolve_file(raw_path: str) -> Path:
        if "\x00" in raw_path or "\\" in raw_path:
            raise HTTPException(status_code=400, detail="invalid path")
        file_path = Path(raw_path)
        if any(segment == ".." for segment in file_path.parts):
            raise HTTPException(status_code=400, detail="invalid path")
        if not file_path.is_absolute():
            file_path = root_path / raw_path.strip("/")
        file_path = file_path.resolve()
        try:
            file_path.relative_to(root_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid path") from exc
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="not found")
        return file_path

    def _serialize_image(file_path: Path) -> dict[str, object]:
        container_path = to_container_path(file_path, root_path)
        stat = file_path.stat()
        metadata = read_image_metadata(file_path)
        indexed_image = repository.get_active_image_by_canonical_path(container_path)
        observed_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        file_url = f"/api/folders/file?{urlencode({'path': container_path})}"

        if indexed_image is not None:
            payload = indexed_image.model_dump(mode="json")
            payload["indexed"] = True
            payload["indexed_content_hash"] = indexed_image.content_hash
            payload["file_url"] = file_url
            return payload

        synthetic_hash = f"fs:{container_path}"
        return {
            "content_hash": synthetic_hash,
            "canonical_path": container_path,
            "file_size": stat.st_size,
            "mtime": stat.st_mtime,
            "mime_type": metadata.mime_type,
            "width": metadata.width,
            "height": metadata.height,
            "is_active": False,
            "last_seen_at": observed_at.isoformat(),
            "embedding_provider": "",
            "embedding_model": "",
            "embedding_version": "",
            "embedding_status": "pending",
            "created_at": observed_at.isoformat(),
            "updated_at": observed_at.isoformat(),
            "indexed": False,
            "indexed_content_hash": None,
            "file_url": file_url,
        }

    @router.get("/api/folders/browse")
    async def browse_folders(
        request: Request,
        path: str = "",
        limit: int | None = None,
        cursor: str | None = None,
    ):
        _require_authentication(request)
        known_folders = _known_folders()
        normalized_path = _normalize_path(path, known_folders)
        target_dir = _resolve_directory(normalized_path)

        folders: list[str] = []
        images: list[dict[str, object]] = []
        if target_dir is not None:
            for entry in sorted(target_dir.iterdir(), key=lambda item: item.name):
                if entry.is_dir():
                    relative = entry.relative_to(root_path).as_posix()
                    folders.append(relative)
                elif entry.is_file() and is_supported_image(entry):
                    images.append(_serialize_image(entry))

        if cursor is not None:
            images = [image for image in images if str(image["canonical_path"]) > cursor]
        if limit is not None:
            images = images[:limit]

        parent = (
            None
            if normalized_path == ""
            else normalized_path.rsplit("/", 1)[0] if "/" in normalized_path else ""
        )
        next_cursor = (
            str(images[-1]["canonical_path"])
            if limit is not None and len(images) == limit and images
            else None
        )
        return JSONResponse(
            content=jsonable_encoder(
                {
                    "path": normalized_path,
                    "parent": parent,
                    "folders": folders,
                    "images": images,
                    "next_cursor": next_cursor,
                }
            )
        )

    @router.get("/api/images/filesystem")
    async def list_filesystem_images(
        request: Request,
        limit: int | None = None,
        cursor: str | None = None,
    ):
        _require_authentication(request)
        images = [
            _serialize_image(file_path)
            for file_path in iter_image_files(root_path)
        ]
        if cursor is not None:
            images = [image for image in images if str(image["canonical_path"]) > cursor]
        if limit is not None:
            images = images[:limit]
        next_cursor = (
            str(images[-1]["canonical_path"])
            if limit is not None and len(images) == limit and images
            else None
        )
        return JSONResponse(
            content=jsonable_encoder(
                {
                    "items": images,
                    "next_cursor": next_cursor,
                }
            )
        )

    @router.get("/api/folders/file")
    async def get_folder_file(request: Request, path: str):
        _require_authentication(request)
        file_path = _resolve_file(path)
        metadata = read_image_metadata(file_path)
        return FileResponse(
            path=str(file_path),
            media_type=metadata.mime_type or "application/octet-stream",
            headers={"Cache-Control": "max-age=86400"},
        )

    return router
