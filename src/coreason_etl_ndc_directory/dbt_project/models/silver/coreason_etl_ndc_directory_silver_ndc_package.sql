{{ config(materialized='table') }}

with source as (
    select * from {{ source('fda_ndc_directory', 'coreason_etl_ndc_directory_bronze_ndc_package_raw') }}
),

deduplicated as (
    select
        *,
        row_number() over (partition by coreason_id order by ingestion_ts desc) as rn
    from source
)

select
    coreason_id,
    nullif(trim(raw_data->>'PRODUCTID'), '') as product_id,
    nullif(trim(raw_data->>'NDCPACKAGECODE'), '') as ndc_package_code,
    nullif(trim(raw_data->>'PACKAGEDESCRIPTION'), '') as package_description
from deduplicated
where rn = 1
