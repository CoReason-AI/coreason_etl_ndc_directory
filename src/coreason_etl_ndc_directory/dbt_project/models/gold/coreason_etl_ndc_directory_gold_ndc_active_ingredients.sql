{{ config(materialized='view') }}

with source as (
    select * from {{ source('fda_ndc_directory', 'coreason_etl_ndc_directory_bronze_ndc_product_raw') }}
),

unnested as (
    select
        coreason_id,
        nullif(trim(raw_data->>'PRODUCTID'), '') as product_id,
        s.substance_name,
        s.idx as substance_idx,
        n.numerator_strength,
        n.idx as strength_idx
    from source,
         unnest(string_to_array(raw_data->>'SUBSTANCENAME', '; ')) with ordinality as s(substance_name, idx),
         unnest(string_to_array(raw_data->>'ACTIVE_NUMERATOR_STRENGTH', '; ')) with ordinality as n(numerator_strength, idx)
    where s.idx = n.idx
)

select
    coreason_id as product_coreason_id,
    product_id,
    nullif(trim(substance_name), '') as substance_name,
    nullif(trim(numerator_strength), '') as active_numerator_strength
from unnested
