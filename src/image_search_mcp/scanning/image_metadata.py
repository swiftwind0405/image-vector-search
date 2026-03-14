import mimetypes
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    width: int
    height: int
    mime_type: str


def read_image_metadata(path: Path) -> ImageMetadata:
    with Image.open(path) as image:
        width, height = image.size
        mime_type = Image.MIME.get(image.format)

    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(path.name)

    return ImageMetadata(
        width=width,
        height=height,
        mime_type=mime_type or "application/octet-stream",
    )
