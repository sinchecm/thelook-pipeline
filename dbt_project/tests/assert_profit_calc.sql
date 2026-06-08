-- Assert: profit_amount = sale_amount - cost_amount within $0.01 rounding tolerance.
-- Returns rows that violate the rule — dbt fails the test if any rows are returned.

select
    sale_id,
    sale_amount,
    cost_amount,
    profit_amount,
    (sale_amount - cost_amount)             as expected_profit,
    abs(profit_amount - (sale_amount - cost_amount)) as diff

from {{ ref('fact_sales') }}

where abs(profit_amount - (sale_amount - cost_amount)) > 0.01
