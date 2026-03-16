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


def test_dbt_gold_models_configured() -> None:
    """
    Test that the gold models are present and configured.
    """
    model_file = DBT_PROJECT_DIR / "models" / "gold" / "gold_ndc_billing_crosswalk.sql"
    assert model_file.exists(), "gold_ndc_billing_crosswalk.sql not found."

    schema_file = DBT_PROJECT_DIR / "models" / "gold" / "schema.yml"
    assert schema_file.exists(), "Gold schema.yml not found."

    with open(schema_file) as f:
        schema_config = yaml.safe_load(f)

    assert "models" in schema_config
    models = schema_config["models"]

    crosswalk_model = next((m for m in models if m["name"] == "gold_ndc_billing_crosswalk"), None)
    assert crosswalk_model is not None, "gold_ndc_billing_crosswalk model not configured in schema.yml."

    column_names = [c["name"] for c in crosswalk_model.get("columns", [])]
    assert "package_coreason_id" in column_names
    assert "product_coreason_id" in column_names
    assert "ndc_11_digit" in column_names


def test_dbt_gold_active_ingredients_model_configured() -> None:
    """
    Test that the gold_ndc_active_ingredients model is present and configured.
    """
    model_file = DBT_PROJECT_DIR / "models" / "gold" / "gold_ndc_active_ingredients.sql"
    assert model_file.exists(), "gold_ndc_active_ingredients.sql not found."

    schema_file = DBT_PROJECT_DIR / "models" / "gold" / "schema.yml"
    assert schema_file.exists(), "Gold schema.yml not found."

    with open(schema_file) as f:
        schema_config = yaml.safe_load(f)

    assert "models" in schema_config
    models = schema_config["models"]

    ingredients_model = next((m for m in models if m["name"] == "gold_ndc_active_ingredients"), None)
    assert ingredients_model is not None, "gold_ndc_active_ingredients model not configured in schema.yml."

    column_names = [c["name"] for c in ingredients_model.get("columns", [])]
    assert "product_coreason_id" in column_names
    assert "product_id" in column_names
    assert "substance_name" in column_names
    assert "active_numerator_strength" in column_names


def test_dbt_silver_models_configured() -> None:
    """
    Test that the silver_ndc_product and silver_ndc_package models are present and configured.
    """
    model_file = DBT_PROJECT_DIR / "models" / "silver" / "silver_ndc_product.sql"
    assert model_file.exists(), "silver_ndc_product.sql not found."

    package_model_file = DBT_PROJECT_DIR / "models" / "silver" / "silver_ndc_package.sql"
    assert package_model_file.exists(), "silver_ndc_package.sql not found."

    schema_file = DBT_PROJECT_DIR / "models" / "silver" / "schema.yml"
    assert schema_file.exists(), "Silver schema.yml not found."

    with open(schema_file) as f:
        schema_config = yaml.safe_load(f)

    assert "models" in schema_config
    models = schema_config["models"]

    product_model = next((m for m in models if m["name"] == "silver_ndc_product"), None)
    assert product_model is not None, "silver_ndc_product model not configured in schema.yml."

    column_names = [c["name"] for c in product_model.get("columns", [])]
    assert "coreason_id" in column_names
    assert "product_id" in column_names

    package_model = next((m for m in models if m["name"] == "silver_ndc_package"), None)
    assert package_model is not None, "silver_ndc_package model not configured in schema.yml."

    package_column_names = [c["name"] for c in package_model.get("columns", [])]
    assert "coreason_id" in package_column_names
    assert "product_id" in package_column_names
    assert "ndc_package_code" in package_column_names


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
