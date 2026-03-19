{{ config(materialized='view') }}

with package as (
    select * from {{ ref('coreason_etl_ndc_directory_silver_ndc_package') }}
),

product as (
    select * from {{ ref('coreason_etl_ndc_directory_silver_ndc_product') }}
)

select
    package.coreason_id as package_coreason_id,
    product.coreason_id as product_coreason_id,
    package.product_id,
    package.ndc_package_code,
    package.package_description,
    product.product_ndc,
    product.proprietary_name,
    product.non_proprietary_name,
    product.labeler_name,
    product.dosage_form,
    product.route,
    product.marketing_start_date,
    CASE
        -- 4-4-2 format -> 0XXXX-XXXX-XX
        WHEN length(split_part(package.ndc_package_code, '-', 1)) = 4 THEN
            lpad(split_part(package.ndc_package_code, '-', 1), 5, '0') ||
            split_part(package.ndc_package_code, '-', 2) ||
            split_part(package.ndc_package_code, '-', 3)
        -- 5-3-2 format -> XXXXX-0XXX-XX
        WHEN length(split_part(package.ndc_package_code, '-', 2)) = 3 THEN
            split_part(package.ndc_package_code, '-', 1) ||
            lpad(split_part(package.ndc_package_code, '-', 2), 4, '0') ||
            split_part(package.ndc_package_code, '-', 3)
        -- 5-4-1 format -> XXXXX-XXXX-0X
        WHEN length(split_part(package.ndc_package_code, '-', 3)) = 1 THEN
            split_part(package.ndc_package_code, '-', 1) ||
            split_part(package.ndc_package_code, '-', 2) ||
            lpad(split_part(package.ndc_package_code, '-', 3), 2, '0')
        ELSE replace(package.ndc_package_code, '-', '')
    END as ndc_11_digit
from package
left join product on package.product_id = product.product_id
