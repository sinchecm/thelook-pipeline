{{ config(materialized='table') }}

select
    product_id,
    product_name,
    brand,
    category,
    department,
    sku,
    round(cost::numeric, 2)             as cost,
    round(retail_price::numeric, 2)     as retail_price,
    round(margin_pct::numeric, 2)       as margin_pct,
    units_sold,
    orders_containing,
    round(total_revenue::numeric, 2)    as total_revenue,
    round(avg_sale_price::numeric, 2)   as avg_sale_price,
    first_sold_at,
    last_sold_at,

    -- price tier for segmentation
    case
        when retail_price >= 200 then 'Premium'
        when retail_price >= 75  then 'Mid-Range'
        else                          'Budget'
    end                                 as price_tier

from {{ ref('int_product_metrics') }}
