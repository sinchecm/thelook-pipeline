{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'order_items') }}
),

cleaned as (
    select
        id                              as sale_id,
        order_id,
        user_id                         as customer_id,
        product_id,
        inventory_item_id,
        status,
        sale_price::numeric(10,2)       as sale_amount,
        created_at::timestamp           as ordered_at,
        shipped_at::timestamp           as shipped_at,
        delivered_at::timestamp         as delivered_at,
        returned_at::timestamp          as returned_at,

        -- derived
        case
            when returned_at is not null then true
            else false
        end                             as is_returned,

        to_char(created_at, 'YYYYMMDD')::int as date_id,

        current_timestamp               as _loaded_at

    from source
    where id is not null
      and sale_price is not null
      and sale_price >= 0
)

select * from cleaned
