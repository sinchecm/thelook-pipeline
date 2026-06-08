{{ config(materialized='table') }}

/*
  Grain: one row per order_item (sale_id).
  All foreign keys are validated by schema.yml tests.
*/

with items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select
        product_id,
        cost,
        retail_price,
        margin_pct,
        category,
        department
    from {{ ref('stg_products') }}
),

inventory as (
    -- use inventory cost when available (more accurate than product list cost)
    select
        inventory_item_id,
        cost as inventory_cost
    from {{ ref('stg_inventory_items') }}
),

enriched as (
    select
        i.sale_id,
        i.order_id,
        i.customer_id,
        i.product_id,
        i.date_id,

        -- measures
        i.sale_amount,
        1                                               as quantity,

        -- prefer inventory cost; fall back to product list cost
        coalesce(
            inv.inventory_cost,
            p.cost,
            0
        )                                               as cost_amount,

        i.sale_amount
            - coalesce(inv.inventory_cost, p.cost, 0)  as profit_amount,

        case
            when i.sale_amount > 0
            then round(
                (i.sale_amount - coalesce(inv.inventory_cost, p.cost, 0))
                / i.sale_amount * 100,
            2)
            else 0
        end                                             as profit_margin_pct,

        i.is_returned,
        i.ordered_at,
        i.shipped_at,
        i.returned_at

    from items i
    left join products p    using (product_id)
    left join inventory inv using (inventory_item_id)

    -- exclude rows where date_id cannot be computed
    where i.date_id is not null
)

select * from enriched
