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
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from coreason_etl_ndc_directory.config import SystemConfigurationState


def test_system_configuration_default() -> None:
    """
    Ensure the SystemConfigurationState model initializes correctly with default parameters.
    """
    config = SystemConfigurationState()
    assert config.fda_ndc_target_url == "https://www.accessdata.fda.gov/cder/ndctext.zip"


def test_system_configuration_env_override() -> None:
    """
    Ensure the SystemConfigurationState model updates its parameters via environment variables.
    """
    with mock.patch.dict(os.environ, {"FDA_NDC_TARGET_URL": "https://example.com/ndc.zip"}):
        config = SystemConfigurationState()
        assert config.fda_ndc_target_url == "https://example.com/ndc.zip"


@given(st.text(alphabet=st.characters(blacklist_categories=["Cc", "Cs"])))  # type: ignore[misc]
def test_system_configuration_arbitrary_urls(url: str) -> None:
    """
    Ensure the SystemConfigurationState model accepts arbitrary strings as URL for fda_ndc_target_url.
    Since it is typed as a str in the implementation, any string without control characters is valid.
    """
    with mock.patch.dict(os.environ, {"FDA_NDC_TARGET_URL": url}):
        config = SystemConfigurationState()
        assert config.fda_ndc_target_url == url


def test_system_configuration_invalid_type() -> None:
    """
    Ensure the SystemConfigurationState model raises ValidationError on invalid types.
    Wait, Pydantic tries to coerce. Let's test providing an invalid value via instantiation.
    """
    with pytest.raises(ValidationError):
        SystemConfigurationState(fda_ndc_target_url=object())
