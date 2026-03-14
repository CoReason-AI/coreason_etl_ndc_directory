# coreason_etl_ndc_directory

ETL pipeline for processing the FDA National Drug Code directory

[![CI/CD](https://github.com/CoReason-AI/coreason_etl_ndc_directory/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CoReason-AI/coreason_etl_ndc_directory/actions/workflows/ci-cd.yml)
[![PyPI](https://img.shields.io/pypi/v/coreason_etl_ndc_directory.svg)](https://pypi.org/project/coreason_etl_ndc_directory/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coreason_etl_ndc_directory.svg)](https://pypi.org/project/coreason_etl_ndc_directory/)
[![License](https://img.shields.io/github/license/CoReason-AI/coreason_etl_ndc_directory)](https://github.com/CoReason-AI/coreason_etl_ndc_directory/blob/main/LICENSE)
[![Codecov](https://codecov.io/gh/CoReason-AI/coreason_etl_ndc_directory/branch/main/graph/badge.svg)](https://codecov.io/gh/CoReason-AI/coreason_etl_ndc_directory)
[![Downloads](https://static.pepy.tech/badge/coreason_etl_ndc_directory)](https://pepy.tech/project/coreason_etl_ndc_directory)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Getting Started

### Prerequisites

- Python 3.14+
- uv

### Installation

1.  Clone the repository:
    ```sh
    git clone https://github.com/CoReason-AI/coreason_etl_ndc_directory.git
    cd coreason_etl_ndc_directory
    ```
2.  Install dependencies:
    ```sh
    uv sync --all-extras --dev
    ```

### Usage

-   Run the linter:
    ```sh
    uv run pre-commit run --all-files
    ```
-   Run the tests:
    ```sh
    uv run pytest
    ```
