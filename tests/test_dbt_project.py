# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

DBT_PROJECT_DIR = Path(__file__).parent.parent / "src" / "coreason_etl_ndc_directory" / "dbt_project"


def test_dbt_project_configuration_exists() -> None:
    """
    Test that the dbt_project.yml exists and has the correct basic structure.
    """
    project_file = DBT_PROJECT_DIR / "dbt_project.yml"
    assert project_file.exists(), "dbt_project.yml not found."

    with open(project_file) as f:
        config = yaml.safe_load(f)

    assert config.get("name") == "coreason_etl_ndc_directory"
    assert "models" in config


def test_dbt_sources_configured() -> None:
    """
    Test that the sources.yml file is present and properly configures the Bronze tables.
    """
    sources_file = DBT_PROJECT_DIR / "models" / "sources.yml"
    assert sources_file.exists(), "sources.yml not found."

    with open(sources_file) as f:
        sources_config = yaml.safe_load(f)

    assert "sources" in sources_config
    sources = sources_config["sources"]
    assert len(sources) > 0

    fda_source = next((s for s in sources if s["name"] == "fda_ndc_directory"), None)
    assert fda_source is not None, "fda_ndc_directory source not configured."

    table_names = [t["name"] for t in fda_source.get("tables", [])]
    assert "bronze_ndc_product_raw" in table_names
    assert "bronze_ndc_package_raw" in table_names


@pytest.mark.skipif(not DBT_PROJECT_DIR.exists(), reason="DBT project not scaffolded yet")
@pytest.mark.skipif(sys.version_info >= (3, 14), reason="dbt-core mashumaro serialization fails on Python 3.14")
def test_dbt_parse() -> None:
    """
    Test that dbt can parse the project successfully.
    This creates a dummy profiles.yml in memory/temp to allow `dbt parse` to run
    without needing a real postgres connection just to validate the syntax.
    """
    # Create a dummy profiles.yml
    profile_content = """
coreason_etl_ndc_directory:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: dummy
      password: dummy
      port: 5432
      dbname: dummy
      schema: public
      threads: 1
    """

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "profiles.yml"
        profile_path.write_text(profile_content)

        # Run dbt parse
        result = subprocess.run(  # noqa: S603
            ["dbt", "parse", "--project-dir", str(DBT_PROJECT_DIR), "--profiles-dir", str(tmpdir)],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"dbt parse failed: {result.stderr}"
