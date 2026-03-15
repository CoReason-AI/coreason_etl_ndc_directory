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

    # We need to spy on tempfile.NamedTemporaryFile to capture the created filenames
    # before they are deleted.
    original_named_temporary_file = tempfile.NamedTemporaryFile

    created_files = []

    def mock_named_temporary_file(*args: Any, **kwargs: Any) -> Any:
        f = original_named_temporary_file(*args, **kwargs)
        created_files.append(f.name)
        return f

    # Use monkeypatch pattern to inject our spy
    tempfile.NamedTemporaryFile = mock_named_temporary_file

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
        tempfile.NamedTemporaryFile = original_named_temporary_file
