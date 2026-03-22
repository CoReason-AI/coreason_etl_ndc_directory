# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import contextlib
import os
import tempfile
import uuid
import zipfile
import shutil
from collections.abc import Iterator
from typing import Any

import polars as pl
import requests

from coreason_etl_ndc_directory.utils.logger import logger

__all__ = ["NAMESPACE_NDC", "stream_and_process_fda_zip"]

NAMESPACE_NDC = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@contextlib.contextmanager
def _managed_temp_file(suffix: str) -> Iterator[str]:
    """
    Context manager providing a temporary file path that is guaranteed to be deleted on exit.
    Using `delete=False` enables closing the file descriptor without deleting the file,
    preventing PermissionError locks on Windows, while still ensuring cleanup.
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError, OSError):
            os.unlink(path)


def stream_and_process_fda_zip(url: str, target_filename: str, id_column: str) -> Iterator[list[dict[str, Any]]]:
    """
    Downloads a zip file from the FDA, extracts a target file, and yields parsed
    rows with a shift-left coreason_id generation.

    AGENT INSTRUCTION: Uses a tempfile strategy that prevents OS lock bugs,
    prevents silent data loss from unescaped quotes in the FDA text files,
    and uses polars to vectorize UUID generation.

    AGENT INSTRUCTION: quote_char=None is mandatory during polars parsing to prevent silent data loss from unescaped quotes.
    """
    with _managed_temp_file(suffix=".zip") as tmp_zip_path, _managed_temp_file(suffix=".txt") as tmp_extract_path:
        try:
            logger.info(f"Downloading ZIP file from {url}")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_zip_path, "wb") as f_zip:
                    f_zip.writelines(r.iter_content(chunk_size=8192))

            logger.info(f"Extracting {target_filename} from {tmp_zip_path}")
            with (
                zipfile.ZipFile(tmp_zip_path, "r") as z,
                z.open(target_filename) as f_in,
                open(tmp_extract_path, "wb") as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)

            logger.info(f"Processing {target_filename} with polars")
            df = pl.read_csv(tmp_extract_path, separator="\t", quote_char=None, encoding="utf8-lossy", infer_schema_length=0)

            logger.info("Applying shift-left UUID generation")
            df = df.with_columns(
                pl.col(id_column)
                .map_batches(
                    lambda s: pl.Series([str(uuid.uuid5(NAMESPACE_NDC, str(x))) for x in s]),
                    return_dtype=pl.String,
                )
                .alias("coreason_id")
            )

            yield df.to_dicts()

        except Exception:
            logger.exception(f"Failed to process FDA zip file from {url}")
            raise
