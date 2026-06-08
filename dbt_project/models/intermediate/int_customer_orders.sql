{{ config(materialized='ephemeral') }}

/*
  Joins stg_users with aggregated order metrics to produce
  customer-level KPIs: lifetime value, order count, recency,
  repeat-purchase flag, and CLV segment.
*/

with customers as (
    select * from {{ ref('stg_users') }}
),

order_agg as (
    select
        customer_id,
        count(distinct order_id)                    as total_orders,
        sum(sale_amount)                            as lifetime_value,
        avg(sale_amount)                            as avg_order_value,
        min(ordered_at)                             as first_order_date,
        max(ordered_at)                             as last_order_date,
        count(distinct order_id) > 1                as is_repeat_customer,
        sum(case when is_returned then 1 else 0 end) as total_returns,
        count(*) filter (where is_returned = false)  as items_kept

    from {{ ref('stg_order_items') }}
    group by customer_id
),

joined as (
    select
        c.customer_id,
        c.first_name,
        c.last_name,
        c.full_name,
        c.email,
        c.age,
        c.age_group,
        c.gender,
        c.city,
        c.state,
        c.country,
        c.traffic_source,
        c.created_at                                as acquisition_date,

        coalesce(o.total_orders, 0)                 as total_orders,
        coalesce(o.lifetime_value, 0)               as lifetime_value,
        coalesce(o.avg_order_value, 0)              as avg_order_value,
        o.first_order_date,
        o.last_order_date,
        coalesce(o.is_repeat_customer, false)       as is_repeat_customer,
        coalesce(o.total_returns, 0)                as total_returns,

        -- days since last purchase (recency)
        case
            when o.last_order_date is not null
            then extract(epoch from (current_timestamp - o.last_order_date)) / 86400
            else null
        end                                         as recency_days,

        -- CLV segment
        case
            when coalesce(o.lifetime_value, 0) >= 500  then 'High'
            when coalesce(o.lifetime_value, 0) >= 150  then 'Medium'
            else                                             'Low'
        end                                         as clv_segment

    from customers c
    left join order_agg o using (customer_id)
)

select * from joined
