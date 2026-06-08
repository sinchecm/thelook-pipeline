{{ config(materialized='table') }}

with source as (
    select * from {{ source('raw', 'products') }}
),

cleaned as (
    select
        id                              as product_id,
        name                            as product_name,
        brand,
        category,
        department,
        cost::numeric(10,2)             as cost,
        retail_price::numeric(10,2)     as retail_price,
        sku,
        distribution_center_id,

        case
            when retail_price > 0
            then round(((retail_price - cost) / retail_price * 100)::numeric, 2)
            else 0::numeric
        end                             as margin_pct,

        current_timestamp               as _loaded_at

    from source
    where id           is not null
      and retail_price is not null
      and retail_price > 0
)

select * from cleaned
