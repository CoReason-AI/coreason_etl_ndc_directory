# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import dlt

from coreason_etl_ndc_directory.config.settings import SystemConfigurationState
from coreason_etl_ndc_directory.utils.ingestion import stream_and_process_fda_zip
from coreason_etl_ndc_directory.utils.logger import logger


def _transform_to_bronze_schema(
    rows: list[dict[str, Any]], source_file: str, ingestion_ts: datetime
) -> list[dict[str, Any]]:
    """
    Transforms the raw dictionaries from the polars generator into the target Bronze schema.
    """
    transformed = []
    for row in rows:
        coreason_id = row.pop("coreason_id")

        row_json_str = json.dumps(row, sort_keys=True, default=str)
        content_hash = hashlib.md5(row_json_str.encode("utf-8"), usedforsecurity=False).hexdigest()

        transformed.append(
            {
                "coreason_id": coreason_id,
                "source_file": source_file,
                "ingestion_ts": ingestion_ts,
                "content_hash": content_hash,
                "raw_data": row,
            }
        )
    return transformed


def fda_ndc_resource_generator(
    url: str, target_filename: str, id_column: str, ingestion_ts: datetime
) -> Iterator[list[dict[str, Any]]]:
    """
    Wraps the stream_and_process_fda_zip generator and applies the bronze schema transformation.
    """
    for batch in stream_and_process_fda_zip(url, target_filename, id_column):
        yield _transform_to_bronze_schema(batch, target_filename, ingestion_ts)


@dlt.source(name="fda_ndc_directory")  # type: ignore[misc]
def fda_ndc_source() -> Any:
    """
    dlt Source that extracts product and package data from the FDA NDC Directory.
    """
    config = SystemConfigurationState()
    url = config.fda_ndc_target_url

    ingestion_ts = datetime.now(UTC)

    logger.info("Initializing dlt source for fda_ndc_directory")

    @dlt.resource(  # type: ignore[misc]
        name="bronze_ndc_product_raw",
        write_disposition="replace",
        primary_key="coreason_id",
    )
    def bronze_ndc_product_raw() -> Iterator[list[dict[str, Any]]]:
        yield from fda_ndc_resource_generator(url, "product.txt", "PRODUCTID", ingestion_ts)

    @dlt.resource(  # type: ignore[misc]
        name="bronze_ndc_package_raw",
        write_disposition="replace",
        primary_key="coreason_id",
    )
    def bronze_ndc_package_raw() -> Iterator[list[dict[str, Any]]]:
        yield from fda_ndc_resource_generator(url, "package.txt", "NDCPACKAGECODE", ingestion_ts)

    return [bronze_ndc_product_raw, bronze_ndc_package_raw]
