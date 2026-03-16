{{ config(materialized='table') }}

with source as (
    select * from {{ source('fda_ndc_directory', 'bronze_ndc_product_raw') }}
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
    nullif(trim(raw_data->>'PRODUCTNDC'), '') as product_ndc,
    nullif(trim(raw_data->>'PROPRIETARYNAME'), '') as proprietary_name,
    nullif(trim(raw_data->>'NONPROPRIETARYNAME'), '') as non_proprietary_name,
    nullif(trim(raw_data->>'LABELERNAME'), '') as labeler_name,
    nullif(trim(raw_data->>'DOSAGEFORMNAME'), '') as dosage_form,
    nullif(trim(raw_data->>'ROUTENAME'), '') as route,
    case
        when trim(raw_data->>'STARTMARKETINGDATE') is not null and length(trim(raw_data->>'STARTMARKETINGDATE')) = 8 then
            to_date(trim(raw_data->>'STARTMARKETINGDATE'), 'YYYYMMDD')
        else null
    end as marketing_start_date
from deduplicated
where rn = 1
