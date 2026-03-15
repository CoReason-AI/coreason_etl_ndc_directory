{{ config(materialized='table') }}

with source as (
    select * from {{ source('fda_ndc_directory', 'bronze_ndc_package_raw') }}
)

select
    coreason_id,
    nullif(trim(raw_data->>'PRODUCTID'), '') as product_id,
    nullif(trim(raw_data->>'NDCPACKAGECODE'), '') as ndc_package_code,
    nullif(trim(raw_data->>'PACKAGEDESCRIPTION'), '') as package_description
from source
