-- Assert: every customer_id in fact_sales exists in dim_customer.
-- Returns orphaned rows — dbt fails if any are found.

select
    f.sale_id,
    f.customer_id,
    'missing from dim_customer' as reason

from {{ ref('fact_sales') }} f
left join {{ ref('dim_customer') }} d on f.customer_id = d.customer_id
where d.customer_id is null

union all

select
    f.sale_id,
    f.product_id::bigint,
    'missing from dim_product'

from {{ ref('fact_sales') }} f
left join {{ ref('dim_product') }} p on f.product_id = p.product_id
where p.product_id is null

union all

select
    f.sale_id,
    f.order_id::bigint,
    'missing from dim_order'

from {{ ref('fact_sales') }} f
left join {{ ref('dim_order') }} o on f.order_id = o.order_id
where o.order_id is null
