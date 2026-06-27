with contractors as (
    select * from {{ ref('stg_contractors') }}
),

shifts as (
    select * from {{ ref('stg_shifts') }}
),

performance_aggregations as (
    select
        c.contractor_id,
        c.contractor_name,
        c.base_rate,
        
        -- Operational Metrics
        count(s.shift_id) as total_shifts_completed,
        sum(s.total_hours) as total_hours_worked,
        sum(s.premium_hours) as total_premium_hours_worked,
        sum(s.km_driven) as total_distance_driven_km,
        
        -- Financial Metrics
        sum(s.taxable_wages) as total_taxable_wages_earned,
        sum(s.tax_free_reimbursements) as total_reimbursements_received,
        sum(s.total_take_home) as total_net_payout
        
    from contractors c
    left join shifts s on c.contractor_id = s.contractor_id
    group by c.contractor_id, c.contractor_name, c.base_rate
)

select * from performance_aggregations