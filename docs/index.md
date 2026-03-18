# Welcome to coreason_etl_ndc_directory

This is the documentation for the `coreason_etl_ndc_directory` project.

## Project Overview
The `coreason_etl_ndc_directory` package is a foundational data pipeline designed to ingest, normalize, and serve the FDA National Drug Code (NDC) Directory. The NDC is the universal product identifier for all human drugs in the United States. This data provides the definitive commercial spine for CoReason's Knowledge Graph, linking clinical concepts (active ingredients) to specific packaged, billable, and dispensable commercial products on the market.

## Architecture

This project strictly follows the **Medallion Architecture (Bronze/Silver/Gold)**.

### Layer 1: Bronze (Ingestion)
* **Objective:** Lossless ingestion of raw text files directly from the downloaded FDA `.zip` stream, with shifted-left identity resolution.
* **Technology:** Python `requests`, `polars`, `dlt`, PostgreSQL `JSONB`.
* **Flow:** The `.zip` file is streamed via HTTP. Extracting `product.txt` and `package.txt` to temp storage to avoid OS lock issues. Parsing into a `polars` DataFrame with `quote_char=None` handles unescaped quotes.
* **Shift-Left Identity Resolution:** A deterministic UUID (`coreason_id`) is generated securely in memory using `uuid5` before reaching the database, significantly reducing database load.
* **Storage Structure:** `bronze_ndc_product_raw` and `bronze_ndc_package_raw` store data essentially as `JSONB` preserving unstructured schema shifts.

### Layer 2: Silver (Transformation)
* **Objective:** Cleaning, Deduplication, and Typing.
* **Technology:** `dbt` (SQL) on PostgreSQL.
* **Flow:** Transforming raw `JSON` from Bronze into strongly-typed structures. Window functions (`row_number() over partition`) resolve any duplicate payloads generated during the FDA data refresh.

### Layer 3: Gold (Serving/Analytics)
* **Objective:** Denormalized, analytics-ready tables for pharmacy claims cross-walking and knowledge graph ingestion.
* **Technology:** `dbt` (SQL).
* **Models:**
    * `gold_ndc_billing_crosswalk`: An optimized view combining Package -> Product data. It enforces the FDA 10-digit formats (4-4-2, 5-3-2, or 5-4-1) into the **standard 11-digit unhyphenated HIPAA format** required for precise billing and pharmacy claims linking.
    * `gold_ndc_active_ingredients`: Uses PostgreSQL's `unnest() WITH ORDINALITY` combined with string array splitting to safely unroll complex multi-ingredient products separated by `; ` maintaining specific structural alignment of an ingredient with its corresponding active strength.

## Maintenance and Deployment Requirements

* **Test Driven:** This repository adheres to a stringent 100% code coverage requirement. Changes must trigger full coverage with zero regressions.
* **Tools Used:**
   - `uv` for dependency and environment management.
   - `ruff` for code linting and formatting.
   - `mypy` for static type checking.
   - `pre-commit` for Git hook configurations ensuring clean commits.

### Running the pipeline

The project's pipeline can be executed as:

```python
from coreason_etl_ndc_directory.main import PipelineExecutionIntent, run_pipeline

intent = PipelineExecutionIntent()
receipt = run_pipeline(intent)
print(receipt.records_loaded)
```
