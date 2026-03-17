# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

from pydantic import BaseModel, Field

from coreason_etl_ndc_directory.config.settings import SystemConfigurationState
from coreason_etl_ndc_directory.utils.logger import logger


class PipelineExecutionIntent(BaseModel):
    """
    State mutation intent that triggers the ETL pipeline execution.
    """


class PipelineExecutionReceipt(BaseModel):
    """
    Immutable historical fact representing the completion state of a pipeline execution.
    """

    status: str = Field(description="The final status of the execution intent.")
    target_url: str = Field(description="The FDA NDC target URL resolved from configuration.")


def run_pipeline(_intent: PipelineExecutionIntent) -> PipelineExecutionReceipt:
    """
    Executes the pipeline resolution logic.

    AGENT INSTRUCTION: Strictly resolve SystemConfigurationState here and return a receipt.
    """
    logger.info("Resolving system configuration state")
    config = SystemConfigurationState()

    logger.info(f"Target URL resolved: {config.fda_ndc_target_url}")

    return PipelineExecutionReceipt(
        status="resolved",
        target_url=config.fda_ndc_target_url,
    )
