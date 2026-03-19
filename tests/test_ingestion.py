# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import os
import tempfile
import uuid
import zipfile
from typing import Any

import pytest
import requests
import responses

from coreason_etl_ndc_directory.utils.ingestion import (
    NAMESPACE_NDC,
    stream_and_process_fda_zip,
)


@pytest.fixture
def mock_fda_zip_content() -> bytes:
    """Creates an in-memory zip file with a dummy product.txt."""
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Dummy tab-separated content with unescaped quotes to test quote_char=None
        # and a PRODUCTID to test shift-left generation.
        content = 'PRODUCTID\tPROPRIETARYNAME\n12345-678_01\tTEST "DRUG"\n'
        zf.writestr("product.txt", content)

    return zip_buffer.getvalue()


@pytest.fixture
def mock_fda_zip_complex_content() -> bytes:
    """Creates an in-memory zip file with complex unescaped quotes and multiple rows."""
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # A complex scenario:
        # - Row 1: Unescaped quote inside a field.
        # - Row 2: Standard row.
        # - Row 3: A field with a quote at the very beginning but no closing quote (a common FDA issue).
        content = (
            "PRODUCTID\tPROPRIETARYNAME\tINGREDIENTS\n"
            '111-11\tTEST "DRUG"\tA; B; C\n'
            "222-22\tNORMAL DRUG\tX; Y; Z\n"
            '333-33\t"UNCLOSED QUOTE DRUG\tM; N; O\n'
        )
        zf.writestr("product.txt", content)

    return zip_buffer.getvalue()


@pytest.fixture
def mock_invalid_zip_content() -> bytes:
    """Creates a corrupted/invalid zip file payload."""
    return b"This is just some random bytes, not a zip file."


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_success(mock_fda_zip_content: bytes) -> None:
    """Test successful downloading, extraction, and shift-left ID generation."""
    url = "https://example.com/ndctext.zip"
    responses.add(responses.GET, url, body=mock_fda_zip_content, status=200)

    # Call the generator
    gen = stream_and_process_fda_zip(url, "product.txt", "PRODUCTID")
    result = list(gen)

    assert len(result) == 1
    rows = result[0]
    assert len(rows) == 1

    row = rows[0]
    assert row["PRODUCTID"] == "12345-678_01"
    assert row["PROPRIETARYNAME"] == 'TEST "DRUG"'

    # Verify deterministic UUID5 generation
    expected_uuid = str(uuid.uuid5(NAMESPACE_NDC, "12345-678_01"))
    assert row["coreason_id"] == expected_uuid


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_complex_quotes(mock_fda_zip_complex_content: bytes) -> None:
    """Test successful extraction when data contains complex unescaped and unclosed quotes."""
    url = "https://example.com/ndctext.zip"
    responses.add(responses.GET, url, body=mock_fda_zip_complex_content, status=200)

    # Call the generator
    gen = stream_and_process_fda_zip(url, "product.txt", "PRODUCTID")
    result = list(gen)

    assert len(result) == 1
    rows = result[0]
    assert len(rows) == 3

    # Row 1 (Unescaped quote inside field)
    assert rows[0]["PRODUCTID"] == "111-11"
    assert rows[0]["PROPRIETARYNAME"] == 'TEST "DRUG"'
    assert rows[0]["INGREDIENTS"] == "A; B; C"

    # Row 2 (Normal)
    assert rows[1]["PRODUCTID"] == "222-22"
    assert rows[1]["PROPRIETARYNAME"] == "NORMAL DRUG"
    assert rows[1]["INGREDIENTS"] == "X; Y; Z"

    # Row 3 (Unclosed quote at start of field)
    assert rows[2]["PRODUCTID"] == "333-33"
    assert rows[2]["PROPRIETARYNAME"] == '"UNCLOSED QUOTE DRUG'
    assert rows[2]["INGREDIENTS"] == "M; N; O"

    # Verify that UUID5 generation worked for all of them
    assert rows[0]["coreason_id"] == str(uuid.uuid5(NAMESPACE_NDC, "111-11"))
    assert rows[1]["coreason_id"] == str(uuid.uuid5(NAMESPACE_NDC, "222-22"))
    assert rows[2]["coreason_id"] == str(uuid.uuid5(NAMESPACE_NDC, "333-33"))


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_invalid_zip(mock_invalid_zip_content: bytes) -> None:
    """Test behavior when the downloaded file is not a valid zip archive."""
    url = "https://example.com/ndctext.zip"
    responses.add(responses.GET, url, body=mock_invalid_zip_content, status=200)

    gen = stream_and_process_fda_zip(url, "product.txt", "PRODUCTID")

    with pytest.raises(zipfile.BadZipFile):
        list(gen)


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_missing_id_column(mock_fda_zip_content: bytes) -> None:
    """Test behavior when the target id_column does not exist in the extracted file."""
    url = "https://example.com/ndctext.zip"
    responses.add(responses.GET, url, body=mock_fda_zip_content, status=200)

    # Call generator with an ID column that doesn't exist
    gen = stream_and_process_fda_zip(url, "product.txt", "NON_EXISTENT_ID")

    import polars as pl

    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        list(gen)


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_http_error() -> None:
    """Test behavior when HTTP request fails."""
    url = "https://example.com/ndctext.zip"
    responses.add(responses.GET, url, status=404)

    gen = stream_and_process_fda_zip(url, "product.txt", "PRODUCTID")

    with pytest.raises(requests.exceptions.HTTPError):
        list(gen)


@responses.activate  # type: ignore[misc]
def test_stream_and_process_fda_zip_cleanup_on_error() -> None:
    """Test that temporary files are cleaned up even if an error occurs."""
    url = "https://example.com/ndctext.zip"

    # We will mock requests.get to raise an error after temp files are created.
    # The temp files are created *before* the request starts in the function.
    responses.add(responses.GET, url, body=Exception("Connection Failed"))

    # Since we refactored to use mkstemp directly via _managed_temp_file,
    # we spy on tempfile.mkstemp instead.
    original_mkstemp = tempfile.mkstemp

    created_files = []

    def mock_mkstemp(*args: Any, **kwargs: Any) -> Any:
        fd, path = original_mkstemp(*args, **kwargs)
        created_files.append(path)
        return fd, path

    # Use monkeypatch pattern to inject our spy
    tempfile.mkstemp = mock_mkstemp  # type: ignore[assignment]

    gen = stream_and_process_fda_zip(url, "product.txt", "PRODUCTID")

    try:
        with pytest.raises(Exception, match="Connection Failed"):
            list(gen)

        # Ensure files were created
        assert len(created_files) == 2

        # Ensure files were deleted in finally block
        for f in created_files:
            assert not os.path.exists(f)
    finally:
        # Restore original
        tempfile.mkstemp = original_mkstemp  # type: ignore[assignment]
