{{ config(materialized='table') }}

with date_spine as (
    select generate_series(
        '2019-01-01'::date,
        '2026-12-31'::date,
        '1 day'::interval
    )::date as full_date
)

select
    to_char(full_date, 'YYYYMMDD')::int         as date_id,
    full_date,
    extract(year    from full_date)::int         as year,
    extract(quarter from full_date)::int         as quarter,
    extract(month   from full_date)::int         as month,
    trim(to_char(full_date, 'Month'))            as month_name,
    to_char(full_date, 'Mon')                    as month_abbr,
    extract(week    from full_date)::int         as week_of_year,
    extract(isodow  from full_date)::int         as day_of_week,
    trim(to_char(full_date, 'Day'))              as day_name,
    to_char(full_date, 'Dy')                     as day_abbr,
    extract(day     from full_date)::int         as day_of_month,
    extract(doy     from full_date)::int         as day_of_year,

    -- flags
    case when extract(isodow from full_date) in (6, 7)
         then true else false end                as is_weekend,

    case when extract(isodow from full_date) not in (6, 7)
         then true else false end                as is_weekday,

    -- holiday season: Black Friday week through New Year
    case
        when extract(month from full_date) = 11
             and extract(day from full_date) >= 22 then true
        when extract(month from full_date) = 12   then true
        else false
    end                                          as is_holiday_season,

    -- fiscal quarter label
    'Q' || extract(quarter from full_date)::text
        || ' ' || extract(year from full_date)::text  as fiscal_quarter_label

from date_spine
order by full_date
