# Local End-to-End Testing

This guide details the procedures for executing and verifying the `coreason_etl_ndc_directory` ingestion and transformation pipelines entirely on a local machine without Docker. The environment relies strictly on Python 3.14+, `uv`, and a local PostgreSQL instance.

## Source Data Context

* **Source Directory:** FDA National Drug Code (NDC) Directory
* **Origin URL:** [https://www.accessdata.fda.gov/cder/ndctext.zip](https://www.accessdata.fda.gov/cder/ndctext.zip)
* **Payload Size:** The compressed archive is roughly **3 to 5 MB**. Upon streaming and extraction, the underlying tab-delimited text payloads (`product.txt` and `package.txt`) expand to approximately **30 to 50 MB**.

## 1. System Configuration

The pipeline requires a standard local PostgreSQL database. Ensure the database service is running and accessible.

Create a `.env` file in the repository root to configure the `dlt` pipeline destination and downstream credentials:

```env
# Define the PostgreSQL destination for the Python dlt ingestion pipeline
DESTINATION__POSTGRES__CREDENTIALS=postgresql://your_user:your_password@localhost:5432/your_db_name

# Standard credentials (can be referenced by dbt profiles or tests)
PGHOST=localhost
PGPORT=5432
PGUSER=your_user
PGPASSWORD=your_password
PGDATABASE=your_db_name
```

## 2. Environment Initialization

Bootstrap the virtual environment and install all requisite dependencies (including `dlt`, `polars`, and `dbt-postgres`) using `uv`:

```bash
uv sync --all-extras --dev
```

## 3. Bronze Layer Execution (Ingestion)

The initial phase streams the ZIP file, enforces the shift-left UUID determinism via `polars`, and lands the JSONB payload into the `bronze` PostgreSQL schema.

Create a temporary execution script (e.g., `run_ingestion.py`) in the root directory:

```python
from coreason_etl_ndc_directory.main import PipelineExecutionIntent, run_pipeline

if __name__ == "__main__":
    print("Initiating FDA NDC Ingestion Pipeline...")
    intent = PipelineExecutionIntent()
    receipt = run_pipeline(intent)

    print(f"Execution Receipt Status: {receipt.status}")
    print(f"Records Landed: {receipt.records_loaded}")
    print(f"Destination Dataset: {receipt.dataset_name}")
```

Execute the pipeline within the managed environment:

```bash
uv run python run_ingestion.py
```

## 4. Silver and Gold Layer Execution (Transformation)

Following successful ingestion, execute the `dbt` transformations to clean, deduplicate, and structurally format the data into the analytical layers (Silver and Gold schemas).

First, ensure your `profiles.yml` (typically located in `~/.dbt/profiles.yml` or the project root) is configured to target your local PostgreSQL instance:

```yaml
coreason_etl_ndc_directory:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: your_user
      password: your_password
      port: 5432
      dbname: your_db_name
      schema: public
      threads: 4
```

Execute the SQL manifold sequence:

```bash
uv run dbt run --project-dir src/coreason_etl_ndc_directory/dbt_project
```

## 5. Verification Queries

Connect to your local PostgreSQL instance (via `psql`, pgAdmin, or DBeaver) and issue the following queries to verify the integrity and structure of the Medallion progression:

**Verify Bronze (Raw JSONB Landing):**
```sql
SELECT coreason_id, ingestion_ts, source_file, raw_data
FROM bronze.coreason_etl_ndc_directory_bronze_ndc_product_raw
LIMIT 5;
```

**Verify Silver (Strongly Typed Schema):**
```sql
SELECT coreason_id, product_id, proprietary_name, non_proprietary_name
FROM silver.coreason_etl_ndc_directory_silver_ndc_product
LIMIT 5;
```

**Verify Gold (Analytical Crosswalk - 11-Digit Standard):**
```sql
SELECT ndc_11_digit, ndc_package_code, proprietary_name, package_description
FROM gold.coreason_etl_ndc_directory_gold_ndc_billing_crosswalk
LIMIT 5;
```

**Verify Gold (Unnested Array Topology):**
```sql
SELECT product_id, substance_name, active_numerator_strength
FROM gold.coreason_etl_ndc_directory_gold_ndc_active_ingredients
LIMIT 5;
```
