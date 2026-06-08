{{ config(materialized='table') }}

/*
  Pre-aggregated monthly revenue report.
  Intended for direct consumption by BI tools and the Python analysis layer
  without hitting the 5M-row fact table every time.
*/

with fact as (
    select * from {{ ref('fact_sales') }}
    where is_returned = false
),

dates as (
    select * from {{ ref('dim_date') }}
),

monthly as (
    select
        d.year,
        d.month,
        d.month_name,
        d.month_abbr,
        d.fiscal_quarter_label,

        count(distinct f.sale_id)           as num_items_sold,
        count(distinct f.order_id)          as num_orders,
        count(distinct f.customer_id)       as num_customers,

        round(sum(f.sale_amount)::numeric, 2)       as total_revenue,
        round(sum(f.profit_amount)::numeric, 2)     as total_profit,
        round(avg(f.sale_amount)::numeric, 2)       as avg_order_value,
        round(avg(f.profit_margin_pct)::numeric, 2) as avg_margin_pct,

        -- new vs returning customers
        count(distinct f.customer_id)
            filter (where f.customer_id in (
                select customer_id from {{ ref('dim_customer') }}
                where is_repeat_customer = false
            ))                                      as new_customers,

        count(distinct f.customer_id)
            filter (where f.customer_id in (
                select customer_id from {{ ref('dim_customer') }}
                where is_repeat_customer = true
            ))                                      as returning_customers

    from fact f
    inner join dates d on f.date_id = d.date_id
    group by d.year, d.month, d.month_name, d.month_abbr, d.fiscal_quarter_label
),

with_growth as (
    select
        *,
        lag(total_revenue) over (order by year, month) as prev_month_revenue,
        round(
            (total_revenue - lag(total_revenue) over (order by year, month))
            / nullif(lag(total_revenue) over (order by year, month), 0) * 100,
        2)                                              as revenue_mom_pct

    from monthly
)

select * from with_growth
order by year, month
