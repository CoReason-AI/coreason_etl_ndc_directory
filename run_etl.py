from coreason_etl_ndc_directory.main import run_pipeline, PipelineExecutionIntent

intent = PipelineExecutionIntent()
receipt = run_pipeline(intent)

print(f"Pipeline finished with status: {receipt.status}")
print(f"Records loaded: {receipt.records_loaded}")
