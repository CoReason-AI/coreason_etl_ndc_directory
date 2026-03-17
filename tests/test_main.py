# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

from coreason_etl_ndc_directory.main import PipelineExecutionIntent, run_pipeline


def test_run_pipeline_resolves_configuration() -> None:
    """Test that the run_pipeline resolves SystemConfigurationState successfully."""
    intent = PipelineExecutionIntent()
    receipt = run_pipeline(intent)

    assert receipt.status == "resolved"
    assert receipt.target_url == "https://www.accessdata.fda.gov/cder/ndctext.zip"
