{{ config(materialized='table') }}

select
    order_id,
    customer_id,
    status,
    num_items,
    round(order_total::numeric, 2)      as order_total,
    is_returned                         as has_any_return,
    items_returned,
    round(days_to_ship::numeric, 1)     as days_to_ship,
    shipping_tier,
    created_at,
    shipped_at,
    delivered_at,
    returned_at

from {{ ref('int_orders_enriched') }}
