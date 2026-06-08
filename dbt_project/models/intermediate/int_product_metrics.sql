{{ config(materialized='ephemeral') }}

/*
  Aggregates item-level sales data to the product grain.
  Used to enrich dim_product with revenue and volume metrics.
*/

with items as (
    select * from {{ ref('stg_order_items') }}
    where is_returned = false
),

products as (
    select * from {{ ref('stg_products') }}
),

agg as (
    select
        i.product_id,
        count(*)                        as units_sold,
        count(distinct i.order_id)      as orders_containing,
        sum(i.sale_amount)              as total_revenue,
        avg(i.sale_amount)              as avg_sale_price,
        min(i.ordered_at)               as first_sold_at,
        max(i.ordered_at)               as last_sold_at

    from items i
    group by i.product_id
),

joined as (
    select
        p.product_id,
        p.product_name,
        p.brand,
        p.category,
        p.department,
        p.cost,
        p.retail_price,
        p.margin_pct,
        p.sku,

        coalesce(a.units_sold, 0)           as units_sold,
        coalesce(a.orders_containing, 0)    as orders_containing,
        coalesce(a.total_revenue, 0)        as total_revenue,
        a.avg_sale_price,
        a.first_sold_at,
        a.last_sold_at

    from products p
    left join agg a using (product_id)
)

select * from joined
