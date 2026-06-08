{{ config(materialized='table') }}

with source as (
    select * from {{ source('raw', 'orders') }}
),

cleaned as (
    select
        order_id,
        user_id                         as customer_id,
        status,
        gender,
        created_at::timestamp           as created_at,
        returned_at::timestamp          as returned_at,
        shipped_at::timestamp           as shipped_at,
        delivered_at::timestamp         as delivered_at,
        num_of_item,

        -- derived
        case
            when returned_at is not null then true
            else false
        end                             as is_returned,

        case
            when shipped_at is not null and created_at is not null
            then extract(epoch from (shipped_at - created_at)) / 86400
            else null
        end                             as days_to_ship,

        current_timestamp               as _loaded_at

    from source
    where order_id is not null
)

select * from cleaned
