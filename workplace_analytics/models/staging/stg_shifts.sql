with raw_shifts as (
    select * from postgres.public.shifts
)

select
    id as shift_id,
    contractor_id,
    client_company,
    km_driven,
    overnight_stay,
    total_hours,
    regular_hours,
    premium_hours,
    taxable_wages,
    tax_free_reimbursements,
    total_take_home
from raw_shifts