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

import pytest

from coreason_etl_ndc_directory.pipelines.bronze import (
    _transform_to_bronze_schema,
    fda_ndc_resource_generator,
    fda_ndc_source,
)


def test_transform_to_bronze_schema() -> None:
    """Test the transformation of raw dictionaries into the target Bronze schema."""
    ingestion_ts = datetime(2026, 1, 1, tzinfo=UTC)
    source_file = "test.txt"

    rows: list[dict[str, Any]] = [
        {"coreason_id": "uuid-1", "col1": "val1", "col2": "val2"},
        {"coreason_id": "uuid-2", "col1": "val3", "col2": None},
    ]

    transformed = _transform_to_bronze_schema(rows, source_file, ingestion_ts)

    assert len(transformed) == 2

    # Check first row
    row1 = transformed[0]
    assert row1["coreason_id"] == "uuid-1"
    assert row1["source_file"] == source_file
    assert row1["ingestion_ts"] == ingestion_ts
    assert row1["raw_data"] == {"col1": "val1", "col2": "val2"}

    # Check hash
    expected_json1 = json.dumps({"col1": "val1", "col2": "val2"}, sort_keys=True, default=str)
    expected_hash1 = hashlib.md5(expected_json1.encode("utf-8"), usedforsecurity=False).hexdigest()
    assert row1["content_hash"] == expected_hash1

    # Check second row
    row2 = transformed[1]
    assert row2["coreason_id"] == "uuid-2"
    assert row2["raw_data"] == {"col1": "val3", "col2": None}


@pytest.fixture
def _mock_stream_and_process_fda_zip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the Polars generator."""

    def generator_factory(*args: Any, **_kwargs: Any) -> Iterator[list[dict[str, Any]]]:
        # args[1] is target_filename
        if args[1] == "package.txt":
            yield [
                {"coreason_id": "uuid-p1", "NDCPACKAGECODE": "PKG-1"},
                {"coreason_id": "uuid-p2", "NDCPACKAGECODE": "PKG-2"},
            ]
        else:
            yield [
                {"coreason_id": "uuid-1", "PRODUCTID": "123", "NAME": "Drug A"},
                {"coreason_id": "uuid-2", "PRODUCTID": "456", "NAME": "Drug B"},
            ]

    monkeypatch.setattr(
        "coreason_etl_ndc_directory.pipelines.bronze.stream_and_process_fda_zip",
        generator_factory,
    )


@pytest.mark.usefixtures("_mock_stream_and_process_fda_zip")
def test_fda_ndc_resource_generator() -> None:
    """Test the wrapper around the Polars generator."""
    url = "https://example.com/test.zip"
    target_filename = "product.txt"
    id_column = "PRODUCTID"
    ingestion_ts = datetime(2026, 1, 1, tzinfo=UTC)

    gen = fda_ndc_resource_generator(url, target_filename, id_column, ingestion_ts)
    result = list(gen)

    assert len(result) == 1
    batch = result[0]
    assert len(batch) == 2

    assert batch[0]["coreason_id"] == "uuid-1"
    assert batch[0]["source_file"] == target_filename
    assert batch[0]["ingestion_ts"] == ingestion_ts
    assert batch[0]["raw_data"] == {"PRODUCTID": "123", "NAME": "Drug A"}


def test_fda_ndc_source() -> None:
    """Test the source initialization and explicit JSONB typing."""
    source_resources = fda_ndc_source()

    # In dlt, source_resources has resources property holding its configured resources
    resources = source_resources.resources
    assert "coreason_etl_ndc_directory_bronze_ndc_product_raw" in resources
    assert "coreason_etl_ndc_directory_bronze_ndc_package_raw" in resources

    # To test execution, we extract items from the resource
    product_resource = resources["coreason_etl_ndc_directory_bronze_ndc_product_raw"]
    package_resource = resources["coreason_etl_ndc_directory_bronze_ndc_package_raw"]

    assert product_resource.name == "coreason_etl_ndc_directory_bronze_ndc_product_raw"
    assert package_resource.name == "coreason_etl_ndc_directory_bronze_ndc_package_raw"

    # Test explicit JSON schema typing for raw_data
    # Access the partial table schema columns of the resource
    product_columns = product_resource.compute_table_schema()["columns"]
    package_columns = package_resource.compute_table_schema()["columns"]

    assert "raw_data" in product_columns
    assert product_columns["raw_data"]["data_type"] == "json"

    assert "raw_data" in package_columns
    assert package_columns["raw_data"]["data_type"] == "json"


@pytest.mark.usefixtures("_mock_stream_and_process_fda_zip")
def test_fda_ndc_source_generators() -> None:
    """Test the resource generators execution."""
    source_resources = fda_ndc_source()

    product_resource = source_resources.resources["coreason_etl_ndc_directory_bronze_ndc_product_raw"]
    package_resource = source_resources.resources["coreason_etl_ndc_directory_bronze_ndc_package_raw"]

    # Iterate over the resource wrapper, which should flatten the batches
    product_data = list(product_resource)
    # The batch has 2 items, and Dlt flatten batches
    assert len(product_data) == 2

    package_data = list(package_resource)
    assert len(package_data) == 2
