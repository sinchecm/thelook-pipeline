{{ config(materialized='ephemeral') }}

/*
  Enriches stg_orders with item-level aggregates and shipping metrics.
  Produces one row per order with total value and status flags.
*/

with orders as (
    select * from {{ ref('stg_orders') }}
),

item_agg as (
    select
        order_id,
        count(*)                        as num_items,
        sum(sale_amount)                as order_total,
        sum(case when is_returned then 1 else 0 end) as items_returned,
        bool_or(is_returned)            as has_return

    from {{ ref('stg_order_items') }}
    group by order_id
),

enriched as (
    select
        o.order_id,
        o.customer_id,
        o.status,
        o.gender,
        o.created_at,
        o.shipped_at,
        o.returned_at,
        o.delivered_at,
        o.is_returned,
        o.days_to_ship,

        coalesce(i.num_items, o.num_of_item, 0)     as num_items,
        coalesce(i.order_total, 0)                  as order_total,
        coalesce(i.items_returned, 0)               as items_returned,
        coalesce(i.has_return, false)               as has_return,

        -- shipping tier
        case
            when o.days_to_ship <= 2  then 'Express'
            when o.days_to_ship <= 5  then 'Standard'
            when o.days_to_ship is null then 'Unknown'
            else                          'Slow'
        end                                         as shipping_tier

    from orders o
    left join item_agg i using (order_id)
)

select * from enriched
