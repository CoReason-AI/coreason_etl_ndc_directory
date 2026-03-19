# Ingestion Protocol

## Architecture Overview

The ingestion pipeline (`coreason_etl_ndc_directory`) operates fundamentally as a state mutation workflow, bridging the external FDA National Drug Code (NDC) domain with the internal CoReason ecosystem. The primary architecture leverages a Python-native, "clean room" extraction strategy. The extraction orchestrates chunked HTTP streaming, in-memory structured deserialization via `polars`, and variant-tolerant data landing into PostgreSQL via `dlt`. This guarantees lossless persistence and determinism.

## Memory & File Safety

The extraction protocol implements aggressive memory constraints and cross-platform safety measures to handle large zip archives.

1. **Chunked HTTP Streaming:** Memory exhaustion is preempted by streaming the payload in an 8192-byte iterative loop directly to a temporary file.
2. **OS Lock Mitigation:** The `tempfile.NamedTemporaryFile` configuration strictly mandates `delete=False`. This explicit configuration circumvents pervasive Windows OS-level file lock contentions, allowing the Python process to safely close the file pointer before executing zip extraction logic. Clean-up is manually enforced within a guaranteed `finally` block.
3. **Escaped Quote Abrogation:** The FDA NDC text format introduces parsing instability through unescaped quotes within raw string fields. The ingestion protocol enforces a strict `quote_char=None` argument during the `polars` CSV parsing event. This configuration prevents silent data loss and row misalignment, ensuring complete data integrity.

```python
# Extraction logic snippet enforcing safe memory and file constraints
tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
tmp_extract = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")

try:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            tmp_zip.write(chunk)
    tmp_zip.close() # OS Lock Mitigation

    with zipfile.ZipFile(tmp_zip.name, "r") as z, z.open(target_filename) as f_in, open(tmp_extract.name, "wb") as f_out:
        f_out.write(f_in.read())
    tmp_extract.close()

    # Escaped Quote Abrogation Protocol
    df = pl.read_csv(tmp_extract.name, separator="\t", quote_char=None, encoding="utf8-lossy")
```

## Shift-Left Identity Resolution

The architecture enforces absolute identity determinism entirely within the Python computational boundary. Database-level sequence generation or extensions are explicitly forbidden.

The primary object identifier, `coreason_id`, is synthesized via a `UUID5` operation anchored to the `NAMESPACE_NDC` namespace. This calculation is vectorized across the data frame using `polars.Series.map_batches`. This pre-computed deterministic identity guarantees absolute idempotency during the ingestion pipeline and eliminates dependencies on downstream database engine features.

```python
# Shift-Left Identity generation logic
NAMESPACE_NDC = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

df = df.with_columns(
    pl.col(id_column)
    .map_batches(
        lambda s: pl.Series([str(uuid.uuid5(NAMESPACE_NDC, str(x))) for x in s]),
        return_dtype=pl.String,
    )
    .alias("coreason_id")
)
```

## Bronze Schema Definition

The ingestion protocol targets a "Variant-First" Medallion Architecture. The objective of the Bronze layer is to provide an immutable, idempotent, and resilient staging manifold that decouples upstream schema volatility from downstream transformations.

Data is yielded to the `dlt` pipeline and persisted into PostgreSQL. The schema is defined by a wrapper object that encapsulates the raw data into a strictly typed `JSONB` column.

The properties injected into the Bronze schema wrapper are:
* `coreason_id`: The deterministic, pre-computed UUID.
* `source_file`: Metadata reflecting the source filename origin.
* `ingestion_ts`: An immutable timestamp denoting the pipeline execution state.
* `content_hash`: An MD5 hash of the raw row payload to verify data integrity.
* `raw_data`: The target `JSONB` column containing the unabridged tab-delimited payload fields as keys and values. This explicit `data_type="json"` classification within the `dlt.resource` prevents the pipeline from recursively unnesting flat JSON objects into explicit table columns, enabling upstream field flexibility.
