{{ config(materialized='table') }}

with source as (
    select * from {{ source('raw', 'users') }}
),

cleaned as (
    select
        id                              as customer_id,
        first_name,
        last_name,
        first_name || ' ' || last_name  as full_name,
        lower(trim(email))              as email,
        age::int                        as age,
        gender,
        city,
        state,
        country,
        traffic_source,
        created_at::timestamp           as created_at,

        -- derived: age group bucket
        case
            when age between 18 and 24 then '18-24'
            when age between 25 and 34 then '25-34'
            when age between 35 and 44 then '35-44'
            when age between 45 and 54 then '45-54'
            when age >= 55             then '55+'
            else 'Unknown'
        end                             as age_group,

        current_timestamp               as _loaded_at

    from source
    where id    is not null
      and email is not null
)

select * from cleaned
