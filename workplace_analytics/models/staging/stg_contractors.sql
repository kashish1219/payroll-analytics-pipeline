with raw_contractors as (
    select * from postgres.public.contractors
)

select
    id as contractor_id,
    name as contractor_name,
    base_rate

from raw_contractors