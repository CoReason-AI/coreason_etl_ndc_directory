# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

from unittest.mock import MagicMock, patch

from coreason_etl_ndc_directory.main import PipelineExecutionIntent, run_pipeline


@patch("coreason_etl_ndc_directory.main.dlt")
@patch("coreason_etl_ndc_directory.main.fda_ndc_source")
def test_run_pipeline_orchestrates_dlt(mock_source: MagicMock, mock_dlt: MagicMock) -> None:
    """Test that run_pipeline orchestrates dlt correctly."""
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.dataset_name = "bronze"

    # Setup mock trace info
    mock_trace = MagicMock()
    mock_extract_info = MagicMock()
    mock_extract_info.asdict.return_value = {
        "metrics": {
            "pkg1": [{"row_count": 10}, {"row_count": 5}],
            "pkg2": [{"row_count": 2}],
        }
    }
    mock_trace.last_extract_info = mock_extract_info
    mock_pipeline_instance.last_trace = mock_trace

    mock_dlt.pipeline.return_value = mock_pipeline_instance

    mock_source_instance = MagicMock()
    mock_source.return_value = mock_source_instance

    intent = PipelineExecutionIntent()
    receipt = run_pipeline(intent)

    # Verify dlt.pipeline was called correctly
    mock_dlt.pipeline.assert_called_once_with(
        pipeline_name="coreason_etl_ndc",
        destination="postgres",
        dataset_name="bronze",
    )

    # Verify pipeline.run was called with the fda_ndc_source
    mock_pipeline_instance.run.assert_called_once_with(mock_source_instance)

    # Verify receipt fields
    assert receipt.status == "success"
    assert receipt.target_url == "https://www.accessdata.fda.gov/cder/ndctext.zip"
    assert receipt.dataset_name == "bronze"
    assert receipt.records_loaded == 17  # 10 + 5 + 2


@patch("coreason_etl_ndc_directory.main.dlt")
@patch("coreason_etl_ndc_directory.main.fda_ndc_source")
def test_run_pipeline_no_last_trace(mock_source: MagicMock, mock_dlt: MagicMock) -> None:
    """Test that run_pipeline handles missing last_trace."""
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.dataset_name = "bronze"
    mock_pipeline_instance.last_trace = None

    mock_dlt.pipeline.return_value = mock_pipeline_instance
    mock_source.return_value = MagicMock()

    intent = PipelineExecutionIntent()
    receipt = run_pipeline(intent)

    assert receipt.status == "success"
    assert receipt.records_loaded == 0
