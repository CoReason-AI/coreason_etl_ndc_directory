# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemConfigurationState(BaseSettings):
    """
    State payload containing configuration values for the coreason_etl_ndc environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fda_ndc_target_url: str = Field(
        default="https://www.accessdata.fda.gov/cder/ndctext.zip",
        description="The source URL from which the National Drug Code (NDC) Directory zip file is fetched.",
    )
