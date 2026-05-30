"""Unit tests for app/utils/file_utility.py.
These are pure unit tests — no DB, no HTTP, no disk I/O (patched out).
They verify every validation gate in isolation:
  - File size limit
  - Extension allowlist
  - MIME type allowlist
  - Extension / MIME cross-check
  - UUID filename generation
  - Date-partitioned path building
  - Path traversal guard
  - Successful save returns correct SavedFileMetadata
  - delete_file does not raise on missing file
"""
from __future__ import annotations
import io
import os
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
import pytest
from fastapi import UploadFile
from app.utils.exceptions import BadRequestException
from app.utils.file_utility import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    SavedFileMetadata,
    _extract_extension,
    _build_date_dir,
    _safe_resolve,
    delete_file,
    validate_and_save,
    UPLOAD_BASE_DIR,
)
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_upload_file(
    filename: str = "test.png",
    content_type: str = "image/png",
    content: bytes = b"fake-image-data",
) -> UploadFile:
    """Build a minimal UploadFile mock."""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.read = AsyncMock(return_value=content)
    return mock_file
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class TestConstants:
    def test_max_file_size_is_10mb(self):
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
    def test_allowed_extensions(self):
        assert ALLOWED_EXTENSIONS == frozenset({"pdf", "jpg", "jpeg", "png"})
    def test_allowed_mime_types(self):
        assert ALLOWED_MIME_TYPES == frozenset({"application/pdf", "image/jpeg", "image/png"})
# ---------------------------------------------------------------------------
# _extract_extension
# ---------------------------------------------------------------------------
class TestExtractExtension:
    def test_returns_lowercase_extension(self):
        assert _extract_extension("report.PDF") == "pdf"
    def test_returns_jpg(self):
        assert _extract_extension("scan.JPG") == "jpg"
    def test_returns_png(self):
        assert _extract_extension("image.png") == "png"
    def test_no_extension_raises(self):
        with pytest.raises(BadRequestException, match="no extension"):
            _extract_extension("noextension")
    def test_dotfile_without_ext_raises(self):
        with pytest.raises(BadRequestException, match="no extension"):
            _extract_extension(".hiddenfile")
# ---------------------------------------------------------------------------
# _build_date_dir
# ---------------------------------------------------------------------------
class TestBuildDateDir:
    def test_returns_correct_path_format(self):
        with patch("app.utils.file_utility.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(year=2026, month=5, day=30)
            result = _build_date_dir()
        assert result == os.path.join(UPLOAD_BASE_DIR, "2026", "05", "30")
    def test_zero_pads_month_and_day(self):
        with patch("app.utils.file_utility.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(year=2026, month=1, day=7)
            result = _build_date_dir()
        assert "01" in result
        assert "07" in result
# ---------------------------------------------------------------------------
# _safe_resolve
# ---------------------------------------------------------------------------
class TestSafeResolve:
    def test_valid_path_within_base_returns_path(self, tmp_path):
        base = str(tmp_path)
        target = str(tmp_path / "subdir" / "file.png")
        result = _safe_resolve(base, target)
        assert result.startswith(os.path.realpath(base))
    def test_path_traversal_raises(self, tmp_path):
        base = str(tmp_path / "uploads")
        traversal = str(tmp_path / "uploads" / ".." / ".." / "etc" / "passwd")
        with pytest.raises(BadRequestException, match="Invalid file path"):
            _safe_resolve(base, traversal)
# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------
class TestDeleteFile:
    def test_deletes_existing_file(self, tmp_path):
        f = tmp_path / "orphan.png"
        f.write_bytes(b"data")
        delete_file(str(f))
        assert not f.exists()
    def test_does_not_raise_on_missing_file(self):
        """delete_file must never raise — it is a best-effort cleanup helper."""
        delete_file("/nonexistent/path/file.png")  # must not raise
    def test_does_not_raise_on_os_error(self, tmp_path):
        with patch("os.remove", side_effect=OSError("permission denied")):
            with patch("os.path.isfile", return_value=True):
                delete_file(str(tmp_path / "locked.png"))  # must not raise
# ---------------------------------------------------------------------------
# validate_and_save
# ---------------------------------------------------------------------------
class TestValidateAndSave:
    # --- Presence ---
    @pytest.mark.asyncio
    async def test_none_file_raises(self):
        with pytest.raises(BadRequestException, match="required"):
            await validate_and_save(None)
    @pytest.mark.asyncio
    async def test_empty_filename_raises(self):
        f = _make_upload_file(filename="", content_type="image/png")
        with pytest.raises(BadRequestException, match="required"):
            await validate_and_save(f)
    # --- Extension ---
    @pytest.mark.asyncio
    async def test_invalid_extension_raises(self):
        f = _make_upload_file(filename="malware.exe", content_type="application/octet-stream")
        with pytest.raises(BadRequestException, match="Invalid file type"):
            await validate_and_save(f)
    @pytest.mark.asyncio
    async def test_txt_extension_raises(self):
        f = _make_upload_file(filename="notes.txt", content_type="text/plain")
        with pytest.raises(BadRequestException, match="Invalid file type"):
            await validate_and_save(f)
    # --- MIME type ---
    @pytest.mark.asyncio
    async def test_invalid_mime_type_raises(self):
        f = _make_upload_file(filename="image.png", content_type="application/octet-stream")
        with pytest.raises(BadRequestException, match="Invalid file content type"):
            await validate_and_save(f)
    # --- Extension / MIME mismatch ---
    @pytest.mark.asyncio
    async def test_extension_mime_mismatch_raises(self):
        # .png extension but claims to be a PDF
        f = _make_upload_file(filename="image.png", content_type="application/pdf")
        with pytest.raises(BadRequestException, match="does not match"):
            await validate_and_save(f)
    @pytest.mark.asyncio
    async def test_jpg_with_png_mime_raises(self):
        f = _make_upload_file(filename="photo.jpg", content_type="image/png")
        with pytest.raises(BadRequestException, match="does not match"):
            await validate_and_save(f)
    # --- File size ---
    @pytest.mark.asyncio
    async def test_empty_file_raises(self):
        f = _make_upload_file(content=b"")
        with pytest.raises(BadRequestException, match="empty"):
            await validate_and_save(f)
    @pytest.mark.asyncio
    async def test_oversized_file_raises(self):
        big = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        f = _make_upload_file(content=big)
        with pytest.raises(BadRequestException, match="exceeds the 10 MB limit"):
            await validate_and_save(f)
    @pytest.mark.asyncio
    async def test_exactly_max_size_is_accepted(self):
        exact = b"x" * MAX_FILE_SIZE_BYTES
        f = _make_upload_file(content=exact)
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = await validate_and_save(f)
        assert result.file_size == MAX_FILE_SIZE_BYTES
    # --- Successful save ---
    @pytest.mark.asyncio
    async def test_successful_save_returns_metadata(self):
        content = b"fake-png-bytes"
        f = _make_upload_file(
            filename="my prescription scan.png",
            content_type="image/png",
            content=content,
        )
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = await validate_and_save(f)
        assert isinstance(result, SavedFileMetadata)
        assert result.original_file_name == "my prescription scan.png"
        assert result.file_type == "png"
        assert result.file_size == len(content)
        # stored_file_name must be UUID-based, not the original name
        assert result.stored_file_name != "my prescription scan.png"
        assert result.stored_file_name.endswith(".png")
        # file_path must use forward slashes
        assert "\\" not in result.file_path
        assert result.file_path.startswith(UPLOAD_BASE_DIR)
    @pytest.mark.asyncio
    async def test_successful_save_for_pdf(self):
        f = _make_upload_file(
            filename="prescription.pdf",
            content_type="application/pdf",
            content=b"%PDF-fake",
        )
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = await validate_and_save(f)
        assert result.file_type == "pdf"
        assert result.stored_file_name.endswith(".pdf")
    @pytest.mark.asyncio
    async def test_successful_save_for_jpeg(self):
        f = _make_upload_file(
            filename="photo.jpeg",
            content_type="image/jpeg",
            content=b"fake-jpeg",
        )
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = await validate_and_save(f)
        assert result.file_type == "jpeg"
    @pytest.mark.asyncio
    async def test_stored_filename_is_uuid_based(self):
        """Stored names must be UUID4-formatted, not the original filename."""
        import re
        f = _make_upload_file(
            filename="doctor_note.png",
            content_type="image/png",
            content=b"data",
        )
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = await validate_and_save(f)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\..+$"
        assert re.match(uuid_pattern, result.stored_file_name), (
            f"Expected UUID filename, got: {result.stored_file_name}"
        )
    # --- OS error on write ---
    @pytest.mark.asyncio
    async def test_os_error_on_write_raises_bad_request(self):
        f = _make_upload_file()
        with patch("os.makedirs"), patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(BadRequestException, match="File upload failed"):
                await validate_and_save(f)

