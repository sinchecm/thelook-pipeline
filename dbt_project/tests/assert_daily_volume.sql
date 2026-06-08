{{ config(severity='warn') }}

with daily as (
    select
        date_id,
        count(*) as daily_orders
    from {{ ref('fact_sales') }}
    group by date_id
),

with_rolling as (
    select
        date_id,
        daily_orders,
        avg(daily_orders) over (
            order by date_id
            rows between 7 preceding and 1 preceding
        ) as rolling_7d_avg
    from daily
)

select
    date_id,
    daily_orders,
    round(rolling_7d_avg, 0) as rolling_7d_avg,
    case
        when daily_orders > rolling_7d_avg * 3   then 'spike'
        when daily_orders < rolling_7d_avg * 0.3 then 'drop'
    end as anomaly_type

from with_rolling
where rolling_7d_avg is not null
  and (
      daily_orders > rolling_7d_avg * 3
   or daily_orders < rolling_7d_avg * 0.3
  )
