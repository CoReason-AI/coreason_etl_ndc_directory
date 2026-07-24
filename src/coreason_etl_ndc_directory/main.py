# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import dlt
from pydantic import BaseModel, Field

from coreason_etl_ndc_directory.config.settings import SystemConfigurationState
from coreason_etl_ndc_directory.pipelines.bronze import fda_ndc_source
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
    records_loaded: int = Field(description="The total number of records successfully loaded by dlt.", default=0)
    dataset_name: str = Field(description="The destination dataset name in Postgres.", default="")


def run_pipeline(_intent: PipelineExecutionIntent) -> PipelineExecutionReceipt:
    """
    Executes the pipeline resolution logic and runs the dlt pipeline.

    AGENT INSTRUCTION: Strictly resolve SystemConfigurationState here, execute the dlt
    pipeline targeting Postgres with dataset_name='bronze', and return a receipt.
    """
    logger.info("Resolving system configuration state")
    config = SystemConfigurationState()

    logger.info(f"Target URL resolved: {config.fda_ndc_target_url}")

    pipeline = dlt.pipeline(
        pipeline_name="coreason_etl_ndc",
        destination="postgres",
        dataset_name="bronze",
    )

    logger.info("Executing dlt pipeline for fda_ndc_source")
    source = fda_ndc_source()
    load_info = pipeline.run(source)

    logger.info(f"Pipeline executed successfully. Load info: {load_info}")

    records_loaded = 0
    if pipeline.last_trace:
        records_loaded = 0
    if pipeline.last_trace and pipeline.last_trace.last_normalize_info:
        # row_counts is a native dictionary mapping table names to normalized row counts
        records_loaded = sum(pipeline.last_trace.last_normalize_info.row_counts.values())

    return PipelineExecutionReceipt(
        status="success",
        target_url=config.fda_ndc_target_url,
        records_loaded=records_loaded,
        dataset_name=pipeline.dataset_name,
    )

    return PipelineExecutionReceipt(
        status="success",
        target_url=config.fda_ndc_target_url,
        records_loaded=records_loaded,
        dataset_name=pipeline.dataset_name,
    )
