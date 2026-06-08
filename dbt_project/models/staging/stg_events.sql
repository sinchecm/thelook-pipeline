{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'events') }}
),

cleaned as (
    select
        id                              as event_id,
        user_id                         as customer_id,
        sequence_number,
        session_id,
        event_type,
        uri,
        browser,
        traffic_source,
        city,
        state,
        created_at::timestamp           as created_at,

        current_timestamp               as _loaded_at

    from source
    where id is not null
)

select * from cleaned
