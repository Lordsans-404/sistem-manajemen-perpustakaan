# apps/catalog/services/storage_service.py
import logging
import uuid
from decouple import config
from supabase import create_client

logger = logging.getLogger(__name__)

BUCKET_NAME = "library-storage"


def _get_supabase_client():
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_SERVICE_ROLE_KEY"),  # pakai service role untuk upload
    )


def upload_cover_image(file, filename: str = None) -> str:
    """
    Upload cover image ke Supabase Storage.
    Returns public URL of the uploaded file.
    """
    client = _get_supabase_client()

    # Generate unique filename biar tidak collision
    ext = filename.rsplit(".", 1)[-1] if filename else "jpg"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    path = f"covers/{unique_name}"

    file_bytes = file.read()

    client.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": file.content_type},
    )

    # Build public URL
    public_url = (
        f"{config('SUPABASE_URL')}/storage/v1/object/public/{BUCKET_NAME}/{path}"
    )

    logger.info("cover.uploaded path=%s", path)
    return public_url


def delete_cover_image(url: str) -> None:
    """
    Hapus cover image lama dari Supabase Storage.
    Dipanggil saat cover diganti atau buku dihapus.
    """
    if not url:
        return

    try:
        # Extract path dari URL
        # URL format: .../storage/v1/object/public/book-covers/covers/xxx.jpg
        path = url.split(f"{BUCKET_NAME}/")[-1]
        client = _get_supabase_client()
        client.storage.from_(BUCKET_NAME).remove([path])
        logger.info("cover.deleted path=%s", path)
    except Exception as exc:
        logger.warning("cover.delete_failed url=%s error=%s", url, exc)