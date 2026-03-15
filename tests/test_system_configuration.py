# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import pytest

from coreason_etl_ndc_directory.config.settings import SystemConfigurationState


def test_system_configuration_default() -> None:
    """Test the default configuration values."""
    config = SystemConfigurationState()
    assert config.fda_ndc_target_url == "https://www.accessdata.fda.gov/cder/ndctext.zip"


def test_system_configuration_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test overriding configuration values using environment variables."""
    test_url = "https://example.com/custom_ndctext.zip"
    monkeypatch.setenv("FDA_NDC_TARGET_URL", test_url)

    config = SystemConfigurationState()
    assert config.fda_ndc_target_url == test_url


def test_system_configuration_ignore_extra_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that extra environment variables do not cause validation errors."""
    monkeypatch.setenv("EXTRA_CONFIG_VAR", "some_value")
    config = SystemConfigurationState()

    # Should still use default, and extra var should be ignored
    assert config.fda_ndc_target_url == "https://www.accessdata.fda.gov/cder/ndctext.zip"
    assert not hasattr(config, "EXTRA_CONFIG_VAR")


@pytest.mark.parametrize(
    "url",
    [
        "http://insecure.example.com/data.zip",
        "ftp://example.com/data.zip",
        "file:///local/path/data.zip",
    ],
)
def test_system_configuration_arbitrary_urls(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that it accepts arbitrary strings as URLs for flexibility, as per current strictness."""
    monkeypatch.setenv("FDA_NDC_TARGET_URL", url)
    config = SystemConfigurationState()
    assert config.fda_ndc_target_url == url
