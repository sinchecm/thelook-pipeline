{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'inventory_items') }}
),

cleaned as (
    select
        id                              as inventory_item_id,
        product_id,
        cost::numeric(10,2)             as cost,
        product_category                as category,
        product_name,
        product_brand                   as brand,
        product_retail_price::numeric(10,2) as retail_price,
        product_department              as department,
        product_sku                     as sku,
        created_at::timestamp           as created_at,
        sold_at::timestamp              as sold_at,

        -- derived
        case
            when sold_at is not null then true
            else false
        end                             as is_sold,

        current_timestamp               as _loaded_at

    from source
    where id is not null
)

select * from cleaned
