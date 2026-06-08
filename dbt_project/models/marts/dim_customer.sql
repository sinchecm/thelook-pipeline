{{ config(materialized='table') }}

select
    customer_id,
    first_name,
    last_name,
    full_name,
    email,
    age,
    age_group,
    gender,
    city,
    state,
    country,
    traffic_source,
    acquisition_date,
    total_orders,
    round(lifetime_value::numeric, 2)       as lifetime_value,
    round(avg_order_value::numeric, 2)      as avg_order_value,
    first_order_date,
    last_order_date,
    is_repeat_customer,
    total_returns,
    round(recency_days::numeric, 0)         as recency_days,
    clv_segment,

    -- RFM segment (used by analysis/customer_segments.py)
    case
        when recency_days <= 30  and total_orders >= 5
             and lifetime_value >= 500              then 'Champions'
        when recency_days <= 90  and total_orders >= 3 then 'Loyal'
        when recency_days <= 180 and total_orders >= 2 then 'Potential Loyalists'
        when recency_days <= 180                    then 'At Risk'
        else                                             'Lost / Churned'
    end                                             as rfm_segment

from {{ ref('int_customer_orders') }}
