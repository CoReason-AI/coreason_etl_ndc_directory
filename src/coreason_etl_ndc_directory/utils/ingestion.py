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
from collections.abc import Iterator
from typing import Any

import polars as pl
import requests

from coreason_etl_ndc_directory.utils.logger import logger

__all__ = ["NAMESPACE_NDC", "stream_and_process_fda_zip"]

NAMESPACE_NDC = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def stream_and_process_fda_zip(url: str, target_filename: str, id_column: str) -> Iterator[list[dict[str, Any]]]:
    """
    Downloads a zip file from the FDA, extracts a target file, and yields parsed
    rows with a shift-left coreason_id generation.

    AGENT INSTRUCTION: Uses a tempfile strategy that prevents OS lock bugs,
    prevents silent data loss from unescaped quotes in the FDA text files,
    and uses polars to vectorize UUID generation.
    """
    # Use delete=False to prevent Windows OS lock bugs
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")  # noqa: SIM115
    tmp_extract = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")  # noqa: SIM115

    try:
        logger.info(f"Downloading ZIP file from {url}")
        # 1. Stream download to avoid memory exhaustion
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                tmp_zip.write(chunk)
        tmp_zip.close()  # Close to release the OS lock

        logger.info(f"Extracting {target_filename} from {tmp_zip.name}")
        # 2. Extract the target file
        with (
            zipfile.ZipFile(tmp_zip.name, "r") as z,
            z.open(target_filename) as f_in,
            open(tmp_extract.name, "wb") as f_out,
        ):
            f_out.write(f_in.read())
        tmp_extract.close()

        logger.info(f"Processing {target_filename} with polars")
        # 3. Read with Polars
        # CRITICAL: FDA text files contain unescaped quotes.
        # quote_char=None is mandatory to prevent silent data loss and row misalignment.
        df = pl.read_csv(tmp_extract.name, separator="\t", quote_char=None, encoding="utf8-lossy")

        logger.info("Applying shift-left UUID generation")
        # 4. Shift-Left UUID5 Generation
        df = df.with_columns(
            pl.col(id_column)
            .map_batches(
                lambda s: pl.Series([str(uuid.uuid5(NAMESPACE_NDC, str(x))) for x in s]),
                return_dtype=pl.String,
            )
            .alias("coreason_id")
        )

        # Yield dictionary rows to dlt
        yield df.to_dicts()

    except Exception:
        logger.exception(f"Failed to process FDA zip file from {url}")
        raise

    finally:
        # Ensure cross-platform cleanup
        if os.path.exists(tmp_zip.name):
            os.unlink(tmp_zip.name)
        if os.path.exists(tmp_extract.name):
            os.unlink(tmp_extract.name)
